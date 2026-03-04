import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.audit_ic_reports import main


def test_audit_reports_outputs_files_and_summary(tmp_path) -> None:
    oos = tmp_path / "oos.parquet"
    pd.DataFrame(
        [
            {
                "date": "2025-01-02",
                "symbol": "A",
                "label_5d": 0.1,
                "label_10d": 0.2,
                "pred_5d": 0.11,
                "pred_10d": 0.21,
                "pred_5d_cal": 0.10,
                "pred_10d_cal": 0.20,
            },
            {
                "date": "2025-01-02",
                "symbol": "B",
                "label_5d": -0.1,
                "label_10d": -0.2,
                "pred_5d": -0.09,
                "pred_10d": -0.19,
                "pred_5d_cal": -0.08,
                "pred_10d_cal": -0.18,
            },
        ]
    ).to_parquet(oos, index=False)

    report = {
        "oos_predictions_path": str(oos),
        "raw_oos_metrics_h2": {"ic_5d": 0.01, "ic_10d": 0.02},
    }
    report_path = tmp_path / "r.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    out_dir = tmp_path / "out"
    code = main(["--reports", str(report_path), "--output-dir", str(out_dir), "--tag", "audit"])
    assert code == 0

    json_path = out_dir / "ic_report_oos_coverage_audit.json"
    md_path = out_dir / "ic_report_oos_coverage_audit.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["total_reports"] == 1
    assert payload["summary"]["strict_daily_cs_raw_ready"] == 1
    assert payload["summary"]["strict_daily_cs_calibrated_ready"] == 1
    assert payload["results"][0]["issues"] == []


def test_audit_reports_marks_missing_oos_path(tmp_path) -> None:
    report = {"raw_oos_metrics_h2": {"ic_5d": 0.01, "ic_10d": 0.02}}
    report_path = tmp_path / "r.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    out_dir = tmp_path / "out"
    code = main(["--reports", str(report_path), "--output-dir", str(out_dir), "--tag", "missing"])
    assert code == 0

    payload = json.loads((out_dir / "ic_report_oos_coverage_missing.json").read_text(encoding="utf-8"))
    assert payload["summary"]["oos_path_ready"] == 0
    assert payload["results"][0]["issues"] == ["missing_oos_path"]
