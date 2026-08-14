"""compare_trade_like_panels CLI 合同（3.2 可对比面板报告）。"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.compare_trade_like_panels import main


def _write_report(path: Path, name: str, monthly: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "experiment_metadata": {"experiment_id": name},
                "comparison_panel": {
                    "raw": {
                        "available": True,
                        "day_count": 2,
                        "month_count": len(monthly),
                        "mean_excess_return": 0.01,
                        "daily_win_rate": 0.5,
                        "monthly_win_rate": 0.5,
                        "worst_day_excess_return": -0.02,
                        "max_consecutive_negative_days": 2,
                        "worst_month": -0.01,
                        "max_consecutive_negative_months": 1,
                        "pass_gate": True,
                        "monthly": monthly,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_panel_compare_md_has_summary_and_monthly(tmp_path: Path) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_report(a, "model_a", [{"month": "2026-01", "avg_excess_return": 0.01}])
    _write_report(b, "model_b", [{"month": "2026-01", "avg_excess_return": -0.02}])

    rc = main(["--reports", str(a), str(b), "--output-dir", str(tmp_path), "--tag", "t"])
    assert rc == 0
    md = (tmp_path / "ic_trade_panel_t.md").read_text(encoding="utf-8")
    assert "model_a" in md and "model_b" in md
    assert "2026-01" in md
    assert "pass" in md  # pass_gate 渲染
    assert "0.0100" in md and "-0.0200" in md


def test_panel_compare_handles_missing_panel(tmp_path: Path) -> None:
    a = tmp_path / "a.json"
    a.write_text(
        json.dumps({"experiment_metadata": {"experiment_id": "no_panel"}}),
        encoding="utf-8",
    )
    b = tmp_path / "b.json"
    _write_report(b, "with_panel", [{"month": "2026-01", "avg_excess_return": 0.0}])
    rc = main(["--reports", str(a), str(b), "--output-dir", str(tmp_path), "--tag", "t2"])
    assert rc == 0
    md = (tmp_path / "ic_trade_panel_t2.md").read_text(encoding="utf-8")
    assert "panel 不可用" in md
