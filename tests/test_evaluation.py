import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

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
    assert metrics["closeness"] == pytest.approx(0.98)  # 1 - MAE(0.01, 0.03)
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
