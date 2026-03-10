from __future__ import annotations

import pandas as pd

from ashare_lab.evaluation.trade_like_panel import (
    TradeLikeGateThresholds,
    build_primary_trade_like_comparison_panel,
)


def test_trade_like_panel_builds_topn_excess_summary() -> None:
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
            "label_3d": [0.05, 0.01, -0.02, 0.04, 0.01, -0.03],
            "label_5d": [0.08, 0.00, -0.03, 0.06, 0.01, -0.04],
            "label_10d": [0.10, -0.01, -0.05, 0.09, 0.00, -0.06],
            "pred_3d": [0.9, 0.2, -0.5, 0.8, 0.1, -0.4],
            "pred_5d": [1.0, 0.2, -0.6, 0.9, 0.1, -0.5],
            "pred_10d": [1.1, 0.1, -0.7, 1.0, 0.1, -0.6],
            "pred_3d_cal": [1.0, 0.1, -0.6, 0.9, 0.0, -0.5],
            "pred_5d_cal": [1.1, 0.1, -0.7, 1.0, 0.0, -0.6],
            "pred_10d_cal": [1.2, 0.0, -0.8, 1.1, 0.0, -0.7],
        }
    )

    panel = build_primary_trade_like_comparison_panel(oos, top_n=1)

    assert panel["top_n"] == 1
    assert panel["benchmark_definition"] == "same-day universe equal-weight realized alpha proxy"
    assert panel["raw"]["mean_excess_return"] > 0
    assert panel["raw"]["daily_win_rate"] == 1.0
    assert panel["raw"]["max_consecutive_negative_days"] == 0
    assert panel["raw"]["monthly"][0]["month"] == "2025-01"


def test_trade_like_panel_gate_fails_on_negative_excess() -> None:
    oos = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-03", "2025-01-03", "2025-01-10", "2025-01-10"]),
            "symbol": ["A", "B", "A", "B"],
            "label_3d": [-0.04, 0.05, -0.03, 0.04],
            "label_5d": [-0.05, 0.06, -0.04, 0.05],
            "label_10d": [-0.06, 0.07, -0.05, 0.06],
            "pred_3d": [1.0, 0.0, 1.0, 0.0],
            "pred_5d": [1.0, 0.0, 1.0, 0.0],
            "pred_10d": [1.0, 0.0, 1.0, 0.0],
            "pred_3d_cal": [1.0, 0.0, 1.0, 0.0],
            "pred_5d_cal": [1.0, 0.0, 1.0, 0.0],
            "pred_10d_cal": [1.0, 0.0, 1.0, 0.0],
        }
    )

    panel = build_primary_trade_like_comparison_panel(
        oos,
        top_n=1,
        gate=TradeLikeGateThresholds(mean_excess_return=0.0, daily_win_rate=0.5, monthly_win_rate=0.5),
    )

    assert panel["raw"]["mean_excess_return"] < 0
    assert panel["raw"]["pass_gate"] is False
