from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np

from scripts.run_lstm_rolling_retrain_dim19_regime import (
    _build_mainline_model_profile,
    _build_comparison_panel,
    _build_config_status_policy,
    _compute_hlc_1d_consistency,
    _infer_label_cols,
    _resolve_loss_weights,
)


def test_infer_label_cols_keeps_legacy_heads_first() -> None:
    df = pd.DataFrame(
        {
            "label_1d_high": [0.0],
            "label_3d": [0.0],
            "label_10d": [0.0],
            "label_5d": [0.0],
            "label_1d_close": [0.0],
        }
    )
    cols = _infer_label_cols(df)
    assert cols[:3] == ["label_3d", "label_5d", "label_10d"]
    assert "label_1d_high" in cols and "label_1d_close" in cols


def test_resolve_loss_weights_supports_overrides() -> None:
    label_cols = ["label_3d", "label_5d", "label_10d", "label_1d_high", "label_1d_low", "label_1d_close"]
    weights = _resolve_loss_weights(
        label_cols=label_cols,
        w3=1.0,
        w5=2.0,
        w10=3.0,
        extra_head_weight=0.5,
        head_loss_weights="label_1d_close:1.2",
    )
    assert weights == (1.0, 2.0, 3.0, 0.5, 0.5, 1.2)


def test_compute_hlc_1d_consistency_metrics() -> None:
    label_cols = ["label_3d", "label_1d_high", "label_1d_low", "label_1d_close"]
    pred = np.array(
        [
            [0.0, 0.04, -0.02, 0.01],  # order valid, inside true
            [0.0, 0.01, -0.01, 0.05],  # order violation (close > high), inside false
        ],
        dtype=float,
    )
    y = np.array(
        [
            [0.0, 0.05, -0.03, 0.02],
            [0.0, 0.04, -0.02, 0.01],
        ],
        dtype=float,
    )
    m = _compute_hlc_1d_consistency(pred, y, label_cols)
    assert m["hlc_1d_valid_count"] == 2.0
    assert np.isclose(m["order_violation_rate_1d_hlc"], 0.5)
    # sample1: |0.06-0.08|=0.02, sample2: |0.02-0.06|=0.04 => mean=0.03
    assert np.isclose(m["range_mae_1d_hlc"], 0.03)
    assert np.isclose(m["inside_rate_1d_hlc"], 0.5)


def test_build_mainline_model_profile_marks_primary_aggregation_ready() -> None:
    profile = _build_mainline_model_profile(
        model_track="mainline_3510d",
        config_profile="lstm_rolling_baseline",
        config_status="baseline",
        label_cols=["label_3d", "label_5d", "label_10d"],
        pred_cols=["pred_3d", "pred_5d", "pred_10d"],
    )
    assert profile["config_status"] == "baseline"
    assert profile["aggregation_ready"] is True
    assert profile["aggregation_target"] == "alpha_score"


def test_build_comparison_panel_contains_monthly_gate_metrics() -> None:
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
    assert panel["raw"]["available"] is True
    assert panel["raw"]["day_count"] == 2
    assert panel["raw"]["mean_excess_return"] > 0
    assert panel["raw"]["monthly_win_rate"] == 1.0
    assert panel["calibrated"]["mean_rank_ic"] >= panel["raw"]["mean_rank_ic"]


def test_build_config_status_policy_defines_promotion_rules() -> None:
    policy = _build_config_status_policy("baseline")
    assert policy["current_status"] == "baseline"
    assert "baseline_to_candidate" in policy["promotion_rules"]
    assert "candidate_to_frozen" in policy["promotion_rules"]
    assert "trade_like comparison_panel" in policy["promotion_rules"]["baseline_to_candidate"][1]
