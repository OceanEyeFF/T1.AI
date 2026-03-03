import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import json
import pytest

from scripts.compare_ic_reports import (
    GateThresholds,
    _common_months,
    compute_ic_5_10,
    compute_rank_ic_5_10,
    extract_monthly_series,
    main,
    passes_gate,
    summarize_monthly,
)


def test_metric_5_10_helpers() -> None:
    metrics = {"ic_5d": 0.1, "ic_10d": 0.2, "rank_ic_5d": 0.05, "rank_ic_10d": 0.15}
    assert compute_ic_5_10(metrics) == pytest.approx(0.15)
    assert compute_rank_ic_5_10(metrics) == pytest.approx(0.1)


def test_extract_monthly_series_prefers_5_10() -> None:
    report = {
        "monthly_logs": [
            {"month": "2025-01", "month_avg_ic_5_10": 0.03},
            {"month": "2025-02", "month_ic_5d": 0.02, "month_ic_10d": 0.04},
            {"month": "2025-03", "raw_avg_ic": 0.01},
        ]
    }
    out = extract_monthly_series(report, monthly_source="raw")
    assert out == {"2025-01": 0.03, "2025-02": 0.03, "2025-03": 0.01}


def test_extract_monthly_series_falls_back_to_monthly_decisions() -> None:
    report = {
        "monthly_decisions": [
            {"month": "2025-01", "month_raw_avg_ic": 0.02, "month_cal_avg_ic": 0.04},
            {"month": "2025-02", "month_raw_avg_ic": -0.01, "month_cal_avg_ic": 0.01},
        ]
    }
    assert extract_monthly_series(report, monthly_source="raw") == {
        "2025-01": 0.02,
        "2025-02": -0.01,
    }
    assert extract_monthly_series(report, monthly_source="calibrated") == {
        "2025-01": 0.04,
        "2025-02": 0.01,
    }


def test_extract_monthly_series_accepts_walkforward_field_names() -> None:
    report = {
        "monthly_logs": [
            {"month": "2025-01", "month_raw_avg_ic": 0.03, "month_cal_avg_ic": 0.05},
            {"month": "2025-02", "month_raw_avg_ic": 0.00, "month_cal_avg_ic": 0.01},
        ]
    }
    assert extract_monthly_series(report, monthly_source="raw") == {"2025-01": 0.03, "2025-02": 0.0}
    assert extract_monthly_series(report, monthly_source="calibrated") == {
        "2025-01": 0.05,
        "2025-02": 0.01,
    }


def test_monthly_summary_and_gate() -> None:
    summary = summarize_monthly([0.1, -0.2, -0.05, 0.03])
    assert summary.month_count == 4
    assert summary.worst == -0.2
    assert summary.max_consecutive_negative_months == 2

    gate = GateThresholds()
    assert not passes_gate(0.06, 0.09, summary, gate)


def test_common_months_helper() -> None:
    common = _common_months(
        [
            ("r1", {"2025-01": 0.1, "2025-02": 0.2}),
            ("r2", {"2025-02": 0.3, "2025-03": 0.4}),
        ]
    )
    assert common == ["2025-02"]


def test_cli_outputs_files(tmp_path) -> None:
    report1 = {
        "raw_oos_metrics": {"ic_5d": 0.06, "ic_10d": 0.08, "rank_ic_5d": 0.09, "rank_ic_10d": 0.10},
        "monthly_logs": [
            {"month": "2025-01", "month_avg_ic_5_10": 0.01},
            {"month": "2025-02", "month_avg_ic_5_10": 0.02},
        ],
    }
    report2 = {
        "raw_oos_metrics": {"ic_5d": 0.03, "ic_10d": 0.05, "rank_ic_5d": 0.02, "rank_ic_10d": 0.04},
        "monthly_logs": [
            {"month": "2025-01", "month_avg_ic_5_10": -0.01},
            {"month": "2025-03", "month_avg_ic_5_10": 0.03},
        ],
    }

    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    p1.write_text(json.dumps(report1), encoding="utf-8")
    p2.write_text(json.dumps(report2), encoding="utf-8")

    out_dir = tmp_path / "out"
    code = main(["--reports", str(p1), str(p2), "--output-dir", str(out_dir), "--tag", "test"])
    assert code == 0

    json_path = out_dir / "ic_monthly_comparison_test.json"
    md_path = out_dir / "ic_monthly_comparison_test.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["common_months"] == ["2025-01"]
    assert len(payload["results"]) == 2


def test_cli_raises_when_common_months_empty(tmp_path) -> None:
    r1 = {
        "raw_oos_metrics": {"ic_5d": 0.01, "ic_10d": 0.01, "rank_ic_5d": 0.01, "rank_ic_10d": 0.01},
        "monthly_logs": [{"month": "2025-01", "month_avg_ic_5_10": 0.01}],
    }
    r2 = {
        "raw_oos_metrics": {"ic_5d": 0.01, "ic_10d": 0.01, "rank_ic_5d": 0.01, "rank_ic_10d": 0.01},
        "monthly_logs": [{"month": "2025-02", "month_avg_ic_5_10": 0.01}],
    }
    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    p1.write_text(json.dumps(r1), encoding="utf-8")
    p2.write_text(json.dumps(r2), encoding="utf-8")

    with pytest.raises(ValueError):
        main(["--reports", str(p1), str(p2), "--output-dir", str(tmp_path / "out")])

    code = main(
        [
            "--reports",
            str(p1),
            str(p2),
            "--allow-empty-common-months",
            "--output-dir",
            str(tmp_path / "out2"),
            "--tag",
            "empty-ok",
        ]
    )
    assert code == 0
