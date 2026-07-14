import sys
from pathlib import Path


import json
import pytest
import pandas as pd

from scripts.compare_ic_reports import (
    DailyCsSummary,
    GateThresholds,
    _common_months,
    check_icir_threshold,
    check_protocol_consistency,
    compute_ic_5_10,
    compute_rank_ic_5_10,
    extract_monthly_series,
    main,
    passes_gate,
    summarize_monthly,
)


def _write_oos_parquet(path: Path, rows: list[dict[str, object]]) -> Path:
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)
    return path


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
    oos1 = _write_oos_parquet(
        tmp_path / "r1_oos.parquet",
        [
            {"date": "2025-01-02", "symbol": "A", "label_5d": 0.1, "label_10d": 0.2, "pred_5d": 0.12, "pred_10d": 0.18},
            {"date": "2025-01-02", "symbol": "B", "label_5d": -0.1, "label_10d": -0.2, "pred_5d": -0.11, "pred_10d": -0.19},
            {"date": "2025-02-03", "symbol": "A", "label_5d": 0.2, "label_10d": 0.1, "pred_5d": 0.19, "pred_10d": 0.09},
            {"date": "2025-02-03", "symbol": "B", "label_5d": -0.2, "label_10d": -0.1, "pred_5d": -0.21, "pred_10d": -0.12},
        ],
    )
    oos2 = _write_oos_parquet(
        tmp_path / "r2_oos.parquet",
        [
            {"date": "2025-01-02", "symbol": "A", "label_5d": 0.1, "label_10d": 0.1, "pred_5d": 0.08, "pred_10d": 0.07},
            {"date": "2025-01-02", "symbol": "B", "label_5d": -0.1, "label_10d": -0.1, "pred_5d": -0.06, "pred_10d": -0.07},
            {"date": "2025-03-03", "symbol": "A", "label_5d": 0.2, "label_10d": 0.1, "pred_5d": 0.21, "pred_10d": 0.11},
            {"date": "2025-03-03", "symbol": "B", "label_5d": -0.2, "label_10d": -0.1, "pred_5d": -0.18, "pred_10d": -0.09},
        ],
    )

    report1 = {
        "raw_oos_metrics": {"ic_5d": 0.06, "ic_10d": 0.08, "rank_ic_5d": 0.09, "rank_ic_10d": 0.10},
        "oos_predictions_path": str(oos1),
        "monthly_logs": [
            {"month": "2025-01", "month_avg_ic_5_10": 0.01},
            {"month": "2025-02", "month_avg_ic_5_10": 0.02},
        ],
    }
    report2 = {
        "raw_oos_metrics": {"ic_5d": 0.03, "ic_10d": 0.05, "rank_ic_5d": 0.02, "rank_ic_10d": 0.04},
        "oos_predictions_path": str(oos2),
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
    assert payload["daily_cs_mode"] == "required"
    assert payload["daily_cs_reports"] == 2
    assert payload["results"][0]["metric_mode"] == "daily_cs"


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
        main(
            [
                "--reports",
                str(p1),
                str(p2),
                "--daily-cs-mode",
                "off",
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )

    code = main(
        [
            "--reports",
            str(p1),
            str(p2),
            "--daily-cs-mode",
            "off",
            "--allow-empty-common-months",
            "--output-dir",
            str(tmp_path / "out2"),
            "--tag",
            "empty-ok",
        ]
    )
    assert code == 0


def test_cli_required_mode_raises_without_oos_path(tmp_path) -> None:
    report = {
        "raw_oos_metrics": {"ic_5d": 0.06, "ic_10d": 0.08, "rank_ic_5d": 0.09, "rank_ic_10d": 0.10},
        "monthly_logs": [{"month": "2025-01", "month_avg_ic_5_10": 0.01}],
    }
    p = tmp_path / "r.json"
    p.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="oos parquet"):
        main(["--reports", str(p), "--output-dir", str(tmp_path / "out"), "--tag", "required-missing"])


def test_check_protocol_consistency_all_match() -> None:
    """协议一致的报告应该通过"""
    proto = {
        "signal_time_mode": "close",
        "execution_time_mode": "next_open",
        "label_mode": "next_open_to_open",
        "return_mode": "next_open_to_open",
    }
    reports = [
        {"evaluation_protocol": proto, "_report_name": "r1"},
        {"evaluation_protocol": proto, "_report_name": "r2"},
    ]
    ok, msg = check_protocol_consistency(reports)
    assert ok is True


def test_check_protocol_consistency_mismatch() -> None:
    """协议不一致应该失败"""
    close_proto = {
        "signal_time_mode": "close",
        "execution_time_mode": "close",
        "label_mode": "close_to_close",
        "return_mode": "close_to_close",
    }
    next_open_proto = {
        "signal_time_mode": "close",
        "execution_time_mode": "next_open",
        "label_mode": "next_open_to_open",
        "return_mode": "next_open_to_open",
    }
    reports = [
        {"evaluation_protocol": close_proto, "_report_name": "r1"},
        {"evaluation_protocol": next_open_proto, "_report_name": "r2"},
    ]
    ok, msg = check_protocol_consistency(reports)
    assert ok is False
    assert "execution_time_mode" in msg


def test_check_protocol_consistency_missing_protocol() -> None:
    """缺少 evaluation_protocol 的报告应该阻断 strict 协议门禁"""
    reports = [
        {
            "evaluation_protocol": {
                "signal_time_mode": "close",
                "execution_time_mode": "next_open",
                "label_mode": "next_open_to_open",
                "return_mode": "next_open_to_open",
            },
            "_report_name": "r1",
        },
        {"_report_name": "r2"},  # 无 evaluation_protocol
    ]
    ok, msg = check_protocol_consistency(reports)
    assert ok is False
    assert "缺少 evaluation_protocol" in msg


def test_check_protocol_consistency_missing_protocol_keys() -> None:
    """evaluation_protocol 缺少关键字段也应该阻断 strict 协议门禁"""
    reports = [
        {"evaluation_protocol": {"label_mode": "close_to_close"}, "_report_name": "r1"},
    ]
    ok, msg = check_protocol_consistency(reports)
    assert ok is False
    assert "缺少关键字段" in msg


def test_check_icir_threshold() -> None:
    """ICIR 门禁测试"""
    summary_high = DailyCsSummary(
        source_path="test", day_count=100, month_count=5,
        mean_ic_5_10=0.08, mean_rank_ic_5_10=0.10, icir_5_10=0.8,
        monthly_ic_5_10={},
    )
    summary_low = DailyCsSummary(
        source_path="test", day_count=100, month_count=5,
        mean_ic_5_10=0.03, mean_rank_ic_5_10=0.04, icir_5_10=0.3,
        monthly_ic_5_10={},
    )

    assert check_icir_threshold(summary_high, threshold=0.5) is True
    assert check_icir_threshold(summary_low, threshold=0.5) is False
    assert check_icir_threshold(None, threshold=0.5) is False
    assert check_icir_threshold(summary_low, threshold=0.0) is True  # 0 = 不检查


def test_passes_gate_with_icir() -> None:
    """passes_gate 应该同时检查 ICIR"""
    monthly = summarize_monthly([0.06, 0.08, 0.05, 0.07])
    summary = DailyCsSummary(
        source_path="test", day_count=100, month_count=4,
        mean_ic_5_10=0.08, mean_rank_ic_5_10=0.10, icir_5_10=0.8,
        monthly_ic_5_10={},
    )

    # 无 ICIR 门禁（默认）-> 通过
    gate_no_icir = GateThresholds(mean_ic_5_10=0.05, mean_rank_ic_5_10=0.08)
    assert passes_gate(0.08, 0.10, monthly, gate_no_icir) is True

    # 有 ICIR 门禁 + 高 ICIR -> 通过
    gate_with_icir = GateThresholds(mean_ic_5_10=0.05, mean_rank_ic_5_10=0.08, icir_5_10=0.5)
    assert passes_gate(0.08, 0.10, monthly, gate_with_icir, daily_summary=summary) is True

    # 有 ICIR 门禁 + 无 daily_summary -> 失败
    assert passes_gate(0.08, 0.10, monthly, gate_with_icir, daily_summary=None) is False

    # 有 ICIR 门禁 + 低 ICIR -> 失败
    summary_low = DailyCsSummary(
        source_path="test", day_count=100, month_count=4,
        mean_ic_5_10=0.08, mean_rank_ic_5_10=0.10, icir_5_10=0.3,
        monthly_ic_5_10={},
    )
    assert passes_gate(0.08, 0.10, monthly, gate_with_icir, daily_summary=summary_low) is False


def test_cli_protocol_check_raises_on_mismatch(tmp_path) -> None:
    """--check-protocol 应在协议不一致时报错"""
    r1 = {
        "raw_oos_metrics": {"ic_5d": 0.06, "ic_10d": 0.08, "rank_ic_5d": 0.09, "rank_ic_10d": 0.10},
        "evaluation_protocol": {
            "signal_time_mode": "close",
            "execution_time_mode": "close",
            "label_mode": "close_to_close",
            "return_mode": "close_to_close",
        },
        "monthly_logs": [{"month": "2025-01", "month_avg_ic_5_10": 0.05}],
    }
    r2 = {
        "raw_oos_metrics": {"ic_5d": 0.06, "ic_10d": 0.08, "rank_ic_5d": 0.09, "rank_ic_10d": 0.10},
        "evaluation_protocol": {
            "signal_time_mode": "close",
            "execution_time_mode": "next_open",
            "label_mode": "next_open_to_open",
            "return_mode": "next_open_to_open",
        },
        "monthly_logs": [{"month": "2025-01", "month_avg_ic_5_10": 0.03}],
    }
    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    p1.write_text(json.dumps(r1), encoding="utf-8")
    p2.write_text(json.dumps(r2), encoding="utf-8")

    with pytest.raises(ValueError, match="协议一致性检查失败"):
        main([
            "--reports", str(p1), str(p2),
            "--daily-cs-mode", "off",
            "--check-protocol",
            "--output-dir", str(tmp_path / "out"),
            "--tag", "proto-test",
        ])


def test_cli_protocol_check_raises_on_missing_protocol(tmp_path) -> None:
    """--check-protocol 应在协议字段缺失时报错"""
    report = {
        "raw_oos_metrics": {"ic_5d": 0.06, "ic_10d": 0.08, "rank_ic_5d": 0.09, "rank_ic_10d": 0.10},
        "monthly_logs": [{"month": "2025-01", "month_avg_ic_5_10": 0.05}],
    }
    p = tmp_path / "r.json"
    p.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="协议一致性检查失败"):
        main([
            "--reports", str(p),
            "--daily-cs-mode", "off",
            "--check-protocol",
            "--output-dir", str(tmp_path / "out"),
            "--tag", "missing-proto",
        ])
