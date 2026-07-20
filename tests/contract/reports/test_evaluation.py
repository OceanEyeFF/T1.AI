import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


from scripts.evaluate_recommendation import evaluate_top_k, generate_report  # noqa: E402


def test_hit_rate_and_closeness_score():
    date = pd.Timestamp("2026-01-12")
    pred_df = pd.DataFrame(
        {
            "date": [date] * 3,
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "predicted_return": [0.02, 0.01, -0.03],
        }
    )
    actual_df = pd.DataFrame(
        {
            "date": [date] * 3,
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "actual_return": [0.03, -0.02, -0.04],
        }
    )

    metrics, daily = evaluate_top_k(pred_df, actual_df, top_n=2)

    assert metrics["hit_rate"] == 0.5
    assert metrics["closeness"] == pytest.approx(0.98)  # 1 - 平均绝对误差（0.01, 0.03）
    assert metrics["cumulative_return"] == pytest.approx((1.03 * 0.98) - 1)
    assert not daily.empty


def test_generate_report_outputs(tmp_path):
    date = pd.Timestamp("2026-01-11")
    metrics = {"hit_rate": 0.6, "closeness": 0.9, "cumulative_return": 0.12}
    daily = pd.DataFrame({"date": [date], "hit_rate": [0.6], "closeness": [0.9], "avg_return": [0.02]})

    paths = generate_report(metrics, daily, tmp_path, date)

    assert paths["summary"].exists()
    assert paths["trend"].exists()
    assert paths["html"].exists()
    html_text = paths["html"].read_text(encoding="utf-8")
    assert "Hit Rate" in html_text


def test_load_table_supports_json_and_csv(tmp_path):
    json_path = tmp_path / "pred.json"
    json_path.write_text('[{"date": "2026-01-12", "symbol": "000001.SZ", "predicted_return": 0.1}]', encoding="utf-8")
    csv_path = tmp_path / "actual.csv"
    csv_path.write_text("date,symbol,actual_return\n2026-01-12,000001.SZ,0.05\n", encoding="utf-8")

    from scripts.evaluate_recommendation import _load_table

    pred_df = _load_table(json_path)
    actual_df = _load_table(csv_path)

    assert pred_df.iloc[0]["predicted_return"] == 0.1
    assert actual_df.iloc[0]["actual_return"] == 0.05


def test_evaluate_top_k_raises_on_empty():
    with pytest.raises(ValueError):
        evaluate_top_k(pd.DataFrame(), pd.DataFrame(), top_n=1)


def test_cli_main_runs(tmp_path, capsys):
    date = pd.Timestamp("2026-01-12")
    pred_path = tmp_path / "pred.json"
    actual_path = tmp_path / "actual.csv"
    pred_path.write_text(
        '[{"date": "2026-01-12", "symbol": "000001.SZ", "predicted_return": 0.02}]',
        encoding="utf-8",
    )
    actual_path.write_text("date,symbol,actual_return\n2026-01-12,000001.SZ,0.03\n", encoding="utf-8")

    from scripts.evaluate_recommendation import main

    main(
        [
            "--pred-file",
            str(pred_path),
            "--actual-file",
            str(actual_path),
            "--output-dir",
            str(tmp_path / "reports"),
            "--top-n",
            "1",
        ]
    )

    captured = capsys.readouterr().out
    assert "metrics" in captured
    assert (tmp_path / "reports" / f"summary_{date:%Y%m%d}.json").exists()


def test_cli_year_month_generates_markdown(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from ashare_lab.recommendation import RecommendationHistory

    db_path = tmp_path / "recommendations.db"
    year_month = "2026-01"

    with RecommendationHistory(db_path) as history:
        history.save_recommendations(
            [
                {"symbol": "600519", "score": 0.85, "rank": 1},
                {"symbol": "000001", "score": 0.80, "rank": 2},
            ],
            rec_date="2026-01-02",
        )
        history.save_validation_results(
            rec_date="2026-01-02",
            validation_result={
                "validation_date": "2026-01-09",
                "hit_rate": 0.7,
                "ic": 0.15,
                "rank_ic": 0.18,
                "excess_return": 0.021,
                "valid_count": 10,
            },
            horizon=5,
        )

    from scripts.evaluate_recommendation import main

    main(["--year-month", year_month, "--db-path", str(db_path)])

    report_path = tmp_path / "output" / "reports" / f"{year_month}_report.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert f"# {year_month} 推荐系统月度报告" in content
    assert "## 整体指标" in content
    assert "## 每日验证结果" in content
    assert "## 推荐详情" in content
    assert "600519" in content


def test_cli_year_month_mutually_exclusive_with_files(tmp_path):
    from scripts.evaluate_recommendation import main

    pred_path = tmp_path / "pred.json"
    pred_path.write_text(
        '[{"date": "2026-01-12", "symbol": "000001.SZ", "predicted_return": 0.02}]',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        main(["--year-month", "2026-01", "--pred-file", str(pred_path), "--actual-file", str(pred_path)])


def test_cli_year_month_invalid_format_raises(tmp_path):
    from scripts.evaluate_recommendation import main

    with pytest.raises(SystemExit):
        main(["--year-month", "2026-13", "--db-path", str(tmp_path / "db.sqlite")])


def test_cli_year_month_no_data_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from ashare_lab.recommendation import RecommendationHistory
    from scripts.evaluate_recommendation import main

    db_path = tmp_path / "recommendations.db"
    with RecommendationHistory(db_path):
        pass

    with pytest.raises(SystemExit) as exc:
        main(["--year-month", "2026-01", "--db-path", str(db_path)])

    assert "无验证数据" in str(exc.value)


def test_metrics_branches_cover_nan_and_empty() -> None:
    from ashare_lab.evaluation import metrics as m

    assert m.information_coefficient(np.array([]), np.array([])) == 0.0
    assert m.rank_information_coefficient(np.array([]), np.array([])) == 0.0
    assert m.mean_squared_error(np.array([]), np.array([])) == float("inf")
    assert m.mean_absolute_error(np.array([]), np.array([])) == float("inf")
    assert m.sharpe_ratio(np.array([])) == 0.0

    preds = np.array([1.0, np.nan, 3.0])
    labels = np.array([1.0, 2.0, np.nan])
    assert m.information_coefficient(preds, labels) == 0.0
    assert m.rank_information_coefficient(preds, labels) == 0.0
    assert m.mean_squared_error(preds, labels) == 0.0
    assert m.mean_absolute_error(preds, labels) == 0.0

    const = np.array([1.0, 1.0, 1.0])
    assert m.information_coefficient(const, np.array([1.0, 2.0, 3.0])) == 0.0


def test_calculate_daily_ic_and_evaluate_model() -> None:
    from ashare_lab.evaluation import metrics as m

    df_pred = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"],
            "symbol": ["A", "B", "A", "B"],
            "label": [0.1, 0.2, 0.3, 0.4],
        }
    )
    df_true = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"],
            "symbol": ["A", "B", "A", "B"],
            "label": [0.1, 0.0, 0.4, 0.2],
        }
    )
    daily = m.calculate_daily_ic(df_pred, df_true)
    assert set(daily.columns) >= {"date", "ic", "rank_ic", "n_samples"}
    assert len(daily) == 2

    out = m.evaluate_model(np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0]))
    assert set(out.keys()) == {"mse", "mae", "ic", "rank_ic"}
    assert out["mse"] == 0.0
    assert out["mae"] == 0.0
    assert out["ic"] == 1.0


def test_reporting_align_and_summarize_excess() -> None:
    from ashare_lab import reporting

    idx = pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])
    equity = pd.DataFrame({"equity": [1.0, 1.1, 1.0]}, index=idx)
    bench = pd.Series([100.0, 110.0, 110.0], index=idx)
    ex = reporting.align_equity_and_benchmark(equity, bench)
    assert set(ex.columns) >= {"equity_ret", "benchmark_ret", "excess_ret", "excess_curve"}

    summary = reporting.summarize_excess(ex)
    assert set(summary.keys()) == {"excess_ann", "excess_vol", "excess_sharpe"}

    assert reporting.summarize_excess(pd.DataFrame()) == {}
    assert reporting.summarize_excess(pd.DataFrame({"excess_ret": [np.nan]})) == {}


def test_momentum_strategy_filters_and_weights() -> None:
    from ashare_exec.strategies.momentum import MomentumTopNStrategy

    today = pd.Timestamp("2026-01-10")
    strat = MomentumTopNStrategy(top_n=2, lookback=2, min_history=4)

    def _hist(close: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": close}, index=pd.date_range("2026-01-01", periods=len(close), freq="D"))

    history = {
        "A": _hist([10, 10, 11, 12]),
        "B": _hist([10, 10, 10, 10]),
        "C": pd.DataFrame({"open": [1, 2, 3, 4]}),
        "D": _hist([10, 11, 12]),
    }
    w = strat.target_weights(today=today, history=history)
    assert set(w.keys()) == {"A", "B"}
    assert sum(w.values()) == pytest.approx(1.0)

    w2 = strat.target_weights(today=today, history={"C": history["C"], "D": history["D"]})
    assert w2 == {}


def test_sequence_builder_py_file_is_exercised() -> None:
    from ashare_lab.dataset.sequence_builder import SequenceDatasetBuilder

    builder = SequenceDatasetBuilder(seq_len=3, stride=1)
    dates = pd.date_range("2026-01-01", periods=6, freq="D")
    features = pd.DataFrame({"f0": np.arange(6, dtype=np.float32)}, index=dates)
    labels = pd.DataFrame({"y0": np.arange(6, dtype=np.float32)}, index=dates)
    X, y = builder.build_sequences(features, labels)
    assert X.shape == (3, 3, 1)
    assert y.shape == (3, 1)

    splits = builder.split_walk_forward(X, y, train_ratio=0.6, valid_ratio=0.2)
    assert set(splits.keys()) == {"train", "valid", "test"}


def test_trainer_smoke_epoch_validate_and_checkpoint(tmp_path: Path, monkeypatch) -> None:
    import torch
    import torch.nn as nn

    from ashare_lab.training.trainer import Trainer, TrainerConfig, EarlyStopping

    class _Model(nn.Module):
        def __init__(self, n_features: int) -> None:
            super().__init__()
            self.linear = nn.Linear(n_features, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x2 = x.squeeze(1)
            return self.linear(x2).squeeze(-1)

    train_df = pd.DataFrame(
        {
            "f0": [0.0, 1.0, 2.0, 3.0],
            "f1": [1.0, 2.0, 3.0, 4.0],
            "label": [0.0, 1.0, 2.0, 3.0],
        }
    )
    valid_df = pd.DataFrame(
        {
            "f0": [0.5, 1.5, 2.5, 3.5],
            "f1": [1.5, 2.5, 3.5, 4.5],
            "label": [0.5, 1.5, 2.5, 3.5],
        }
    )

    config = TrainerConfig(
        batch_size=2,
        learning_rate=1e-2,
        weight_decay=0.0,
        max_epochs=1,
        patience=2,
        lr_scheduler="reduce_on_plateau",
        device="cpu",
        save_dir=tmp_path / "ckpt",
    )
    trainer = Trainer(_Model(n_features=2), config, train_df, valid_df, feature_cols=["f0", "f1"])

    loss = trainer.train_epoch()
    assert loss >= 0.0

    metrics = trainer.validate()
    assert set(metrics.keys()) >= {"mse", "mae", "ic", "rank_ic", "loss"}

    trainer.save_checkpoint("best_model.pt")
    monkeypatch.setattr(
        torch,
        "load",
        lambda _path, map_location=None, weights_only=True: {
            "model_state_dict": trainer.model.state_dict(),
            "optimizer_state_dict": trainer.optimizer.state_dict(),
            "history": trainer.history,
            "best_valid_loss": trainer.best_valid_loss,
            "best_epoch": trainer.best_epoch,
        },
    )
    trainer.load_checkpoint("best_model.pt")

    es = EarlyStopping(patience=1, min_delta=0.0)
    assert es(1.0) is False
    assert es(1.1) is True


def test_trainer_train_cosine_scheduler_triggers_early_stop(tmp_path: Path, monkeypatch) -> None:
    import torch
    import torch.nn as nn

    from ashare_lab.training.trainer import Trainer, TrainerConfig

    class _Model(nn.Module):
        def __init__(self, n_features: int) -> None:
            super().__init__()
            self.linear = nn.Linear(n_features, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x2 = x.squeeze(1)
            return self.linear(x2).squeeze(-1)

    df = pd.DataFrame({"f0": [0.0, 1.0, 2.0, 3.0], "label": [0.0, 1.0, 2.0, 3.0]})
    config = TrainerConfig(
        batch_size=2,
        learning_rate=1e-2,
        weight_decay=0.0,
        max_epochs=3,
        patience=1,
        lr_scheduler="cosine",
        device="cpu",
        save_dir=tmp_path / "ckpt",
    )
    trainer = Trainer(_Model(n_features=1), config, df, df, feature_cols=["f0"])

    monkeypatch.setattr(
        trainer,
        "validate",
        lambda: {"mse": 0.0, "mae": 0.0, "ic": 0.0, "rank_ic": 0.0, "loss": 1.0},
    )
    history = trainer.train()
    assert len(history["valid_loss"]) >= 1
