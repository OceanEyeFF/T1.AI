from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.auto_tune_xgb import ScoreWeights, _monthly_values_from_weekly_logs, score_report


def test_monthly_values_from_weekly_logs_groups_by_month() -> None:
    logs = [
        {"week_start": "2026-01-03", "raw_avg_ic": 0.10, "cal_avg_ic": 0.20},
        {"week_start": "2026-01-10", "raw_avg_ic": 0.30, "cal_avg_ic": 0.40},
        {"week_start": "2026-02-07", "raw_avg_ic": -0.20, "cal_avg_ic": -0.10},
    ]
    raw_vals = _monthly_values_from_weekly_logs(logs, metric_source="raw")
    cal_vals = _monthly_values_from_weekly_logs(logs, metric_source="calibrated")
    assert raw_vals == [0.20, -0.20]
    assert abs(cal_vals[0] - 0.30) < 1e-12
    assert abs(cal_vals[1] + 0.10) < 1e-12


def test_score_report_penalizes_negative_streak() -> None:
    report = {
        "raw_oos_metrics": {
            "ic_5d": 0.02,
            "ic_10d": 0.00,
            "rank_ic_5d": 0.01,
            "rank_ic_10d": -0.01,
        },
        "weekly_logs": [
            {"week_start": "2026-01-03", "raw_avg_ic": -0.2, "cal_avg_ic": -0.1},
            {"week_start": "2026-01-10", "raw_avg_ic": -0.1, "cal_avg_ic": -0.1},
            {"week_start": "2026-02-07", "raw_avg_ic": -0.3, "cal_avg_ic": -0.2},
            {"week_start": "2026-03-07", "raw_avg_ic": 0.1, "cal_avg_ic": 0.1},
        ],
    }
    weights = ScoreWeights(
        w_ic=1.0,
        w_rank_ic=0.3,
        w_win_rate=0.1,
        p_worst_month=0.6,
        p_neg_streak=0.08,
    )
    s = score_report(report, metric_source="raw", weights=weights)
    assert s.max_consecutive_negative_months == 2
    assert s.worst_month < 0
    assert s.total < 0.0
