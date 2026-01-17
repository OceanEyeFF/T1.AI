import sys
from pathlib import Path

import pandas as pd
import pytest
import torch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.daily_pipeline import (  # noqa: E402
    generate_recommendations,
    incremental_update,
    main as pipeline_main,
    recompute_features_labels,
    evaluate_previous_day,
    run_pipeline,
    warm_start_incremental_train,
)
from ashare_lab.models.transformer import create_mtl_model  # noqa: E402


def test_incremental_update_only_latest_date(tmp_path):
    calls = []

    def fake_fetch(req, cache_dir):
        calls.append((req.start_date, req.end_date, req.symbol))
        df = pd.DataFrame(
            {
                "open": [1.0],
                "high": [1.1],
                "low": [0.9],
                "close": [1.0],
                "volume": [10],
                "amount": [100],
            },
            index=[pd.to_datetime(req.start_date)],
        )
        df.index.name = "date"
        return df

    date = "20260113"
    result = incremental_update(["000001.SZ"], date, tmp_path, fetch_fn=fake_fetch)

    assert calls == [(date, date, "000001.SZ")]
    df = result["000001.SZ"]
    assert list(df.index) == [pd.to_datetime(date)]
    assert df.iloc[0]["close"] == 1.0


def test_recompute_features_labels_window_respects_tail():
    dates = pd.date_range("2025-12-01", periods=40, freq="B")
    close = pd.Series(range(40), index=dates, dtype=float) + 10
    df = pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1,
            "amount": 1,
        }
    )

    features = recompute_features_labels({"000001.SZ": df}, window=30)

    assert features["date"].min() == dates[-30]
    expected_momentum = close.iloc[-1] / close.iloc[-31] - 1
    assert features.iloc[-1]["feature_momentum"] == expected_momentum

    expected_label = close.iloc[-1] / close.iloc[-2] - 1
    assert features.iloc[-2]["label_next"] == expected_label


def test_incremental_update_empty_raises(tmp_path):
    def empty_fetch(req, cache_dir):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"]).set_index(
            pd.Index([], name="date")
        )

    with pytest.raises(ValueError):
        incremental_update(["000001.SZ"], "20260113", tmp_path, fetch_fn=empty_fetch)


def test_recompute_features_labels_empty_map():
    empty = recompute_features_labels({}, window=30)
    assert empty.empty
    assert list(empty.columns) == ["date", "symbol", "feature_momentum", "label_next", "close"]


def test_warm_start_incremental_train_uses_checkpoint_and_freeze(tmp_path):
    ckpt_dir = tmp_path / "runs"
    ckpt_dir.mkdir()
    base_model = create_mtl_model(input_dim=6, min_seq_len=30)
    torch.save({"model_state_dict": base_model.state_dict()}, ckpt_dir / "base.pt")

    model, meta = warm_start_incremental_train(
        checkpoint_dir=ckpt_dir,
        freeze_layers=1,
        epochs=1,
        dry_run=True,
    )

    assert meta["warm_start"] == ckpt_dir / "base.pt"
    assert meta["checkpoint"].exists()
    first_layer_param = next(model.transformer_encoder.layers[0].parameters())
    assert first_layer_param.requires_grad is False


def test_warm_start_incremental_train_runs_training_loop(tmp_path):
    ckpt_dir = tmp_path / "runs_train"
    ckpt_dir.mkdir()
    model, meta = warm_start_incremental_train(ckpt_dir, freeze_layers=0, epochs=1, dry_run=False)
    assert meta["checkpoint"].exists()
    # 训练路径会创建至少一个参数更新（无法直接验证数值，确保函数可运行）
    assert isinstance(model, torch.nn.Module)


def test_generate_recommendations_filters_st_and_star(tmp_path):
    date = pd.Timestamp("2026-01-13")
    feature_df = pd.DataFrame(
        {
            "date": [date] * 4,
            "symbol": ["000001.SZ", "ST1234", "688001.SH", "000002.SZ"],
            "feature_momentum": [0.3, 0.5, 0.4, 0.2],
            "label_next": [0, 0, 0, 0],
            "close": [1, 1, 1, 1],
        }
    )

    recs = generate_recommendations(feature_df, date, top_n=3, output_dir=tmp_path)

    assert list(recs["symbol"]) == ["000001.SZ", "000002.SZ"]
    assert (tmp_path / "20260113.csv").exists()
    assert (tmp_path / "20260113.json").exists()


def test_generate_recommendations_error_branches():
    date = pd.Timestamp("2026-01-13")
    with pytest.raises(ValueError):
        generate_recommendations(pd.DataFrame(), date, top_n=3, output_dir=None)

    feature_df = pd.DataFrame(
        {
            "date": [date - pd.Timedelta(days=1)],
            "symbol": ["000001.SZ"],
            "feature_momentum": [0.1],
            "label_next": [0.0],
            "close": [1.0],
        }
    )
    with pytest.raises(ValueError):
        generate_recommendations(feature_df, date, top_n=1, output_dir=None)


def test_evaluate_previous_day_with_existing_file(tmp_path):
    today = pd.Timestamp("2026-01-13")
    prev = today - pd.Timedelta(days=1)
    rec_dir = tmp_path / "recs"
    rec_dir.mkdir()
    prev_rec = pd.DataFrame(
        {"symbol": ["000001.SZ"], "predicted_return": [0.02], "rank": [1], "date": [prev]}
    )
    prev_rec.to_csv(rec_dir / f"{prev:%Y%m%d}.csv", index=False)

    feature_df = pd.DataFrame(
        {
            "date": [prev, today],
            "symbol": ["000001.SZ", "000001.SZ"],
            "feature_momentum": [0.1, 0.2],
            "label_next": [0.03, 0.04],
            "close": [10, 10.2],
        }
    )

    metrics = evaluate_previous_day(today, rec_dir, feature_df, top_n=1, report_dir=tmp_path / "reports")
    assert metrics is not None
    assert metrics["hit_rate"] == 1.0
    assert (tmp_path / "reports" / f"summary_{prev:%Y%m%d}.json").exists()


def test_pipeline_cli_dry_run(tmp_path, monkeypatch):
    args = [
        "--date",
        "20260113",
        "--dry-run",
        "--skip-training",
        "--recommendations-dir",
        str(tmp_path / "recs"),
        "--report-dir",
        str(tmp_path / "reports"),
    ]
    pipeline_main(args)

    assert (tmp_path / "recs" / "20260113.csv").exists()
    # 没有上一日推荐文件时，评估可为空，但主流程应顺利结束


def test_run_pipeline_with_training_branch(tmp_path, monkeypatch):
    summary = run_pipeline(
        date=pd.Timestamp("2026-01-13"),
        symbols=["000001.SZ"],
        cache_dir=tmp_path / "cache",
        recommendations_dir=tmp_path / "recs",
        report_dir=tmp_path / "reports",
        window=30,
        skip_training=False,
        dry_run=True,
        freeze_layers=0,
    )
    assert "recommendations" in summary
