from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


from scripts.compare_ic_reports import check_protocol_consistency
from scripts.run_xgboost_rolling_retrain_regime import (
    _build_comparison_panel,
    _build_evaluation_protocol,
)


def test_build_evaluation_protocol_matches_shared_checker_keys() -> None:
    proto = _build_evaluation_protocol("close_to_close")

    assert proto == {
        "signal_time_mode": "close",
        "execution_time_mode": "next_open",
        "label_mode": "close_to_close",
        "return_mode": "close_to_close",
        "cost_model": "none",
        "daily_cs_mode": "required",
    }
    ok, msg = check_protocol_consistency([{"evaluation_protocol": proto, "_report_name": "xgb"}])
    assert ok is True
    assert "协议字段完整" in msg


def test_build_comparison_panel_uses_primary_trade_like_contract() -> None:
    oos = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-03",
                    "2025-01-03",
                    "2025-01-03",
                    "2025-01-10",
                    "2025-01-10",
                    "2025-01-10",
                ]
            ),
            "symbol": ["A", "B", "C", "A", "B", "C"],
            "label_3d": [0.05, 0.01, -0.02, 0.04, 0.00, -0.03],
            "label_5d": [0.08, 0.00, -0.03, 0.06, -0.01, -0.04],
            "label_10d": [0.10, -0.02, -0.05, 0.09, 0.00, -0.06],
            "pred_3d": [0.9, 0.1, -0.5, 0.8, 0.0, -0.4],
            "pred_5d": [1.0, 0.2, -0.6, 0.9, 0.1, -0.5],
            "pred_10d": [1.1, 0.0, -0.7, 1.0, 0.1, -0.6],
            "pred_3d_cal": [1.0, 0.0, -0.6, 0.9, -0.1, -0.5],
            "pred_5d_cal": [1.1, 0.1, -0.7, 1.0, 0.0, -0.6],
            "pred_10d_cal": [1.2, -0.1, -0.8, 1.1, 0.0, -0.7],
        }
    )

    panel = _build_comparison_panel(oos, top_n=1)

    assert panel["score_target"] == "alpha_score"
    assert panel["evaluation_method"] == "topn_equal_weight_excess"
    assert panel["top_n"] == 1
    assert panel["raw"]["available"] is True
    assert panel["calibrated"]["available"] is True
    assert panel["raw"]["day_count"] == 2
