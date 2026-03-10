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
    raw_metrics = {
        "ic_3d": 0.01,
        "ic_5d": 0.05,
        "ic_10d": 0.09,
        "rank_ic_3d": 0.01,
        "rank_ic_5d": 0.08,
        "rank_ic_10d": 0.12,
        "avg_ic": 0.05,
        "avg_rank_ic": 0.07,
    }
    cal_metrics = {
        "ic_3d": 0.02,
        "ic_5d": 0.06,
        "ic_10d": 0.10,
        "rank_ic_3d": 0.02,
        "rank_ic_5d": 0.09,
        "rank_ic_10d": 0.13,
        "avg_ic": 0.06,
        "avg_rank_ic": 0.08,
    }
    weekly_logs = [
        {"week_start": "2025-01-03", "raw_avg_ic": 0.04, "cal_avg_ic": 0.05},
        {"week_start": "2025-01-10", "raw_avg_ic": 0.06, "cal_avg_ic": 0.07},
        {"week_start": "2025-02-07", "raw_avg_ic": -0.02, "cal_avg_ic": 0.01},
        {"week_start": "2025-02-14", "raw_avg_ic": 0.03, "cal_avg_ic": 0.04},
    ]
    panel = _build_comparison_panel(raw_metrics, cal_metrics, weekly_logs)
    assert panel["focus_targets"] == ["5d", "10d"]
    assert panel["raw"]["mean_ic_5_10"] == 0.07
    assert panel["calibrated"]["mean_rank_ic_5_10"] == 0.11
    assert panel["raw"]["month_count"] == 2
    assert panel["delta_cal_minus_raw"]["mean_ic_5_10"] > 0


def test_build_config_status_policy_defines_promotion_rules() -> None:
    policy = _build_config_status_policy("baseline")
    assert policy["current_status"] == "baseline"
    assert "baseline_to_candidate-best" in policy["promotion_rules"]
    assert "candidate-best_to_frozen-best" in policy["promotion_rules"]
