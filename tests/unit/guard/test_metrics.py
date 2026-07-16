"""Guard metrics: IC implementation uniqueness + parity with lab shim."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_infra.guard import metrics as guard_metrics
from ashare_lab.evaluation import metrics as lab_metrics


def _multi_index_series() -> tuple[pd.Series, pd.Series]:
    idx = pd.MultiIndex.from_tuples(
        [
            ("2024-01-01", "A"),
            ("2024-01-01", "B"),
            ("2024-01-01", "C"),
            ("2024-01-02", "A"),
            ("2024-01-02", "B"),
            ("2024-01-02", "C"),
        ],
        names=["date", "symbol"],
    )
    predictions = pd.Series([0.1, 0.2, -0.1, 0.3, 0.1, -0.2], index=idx)
    labels = pd.Series([0.15, 0.18, -0.08, 0.25, 0.12, -0.15], index=idx)
    return predictions, labels


def test_calculate_daily_cs_ic_guard() -> None:
    predictions, labels = _multi_index_series()
    daily = guard_metrics.calculate_daily_cs_ic(predictions, labels, method="pearson")
    assert len(daily) == 2
    assert daily.notna().all()
    stats = guard_metrics.summarize_daily_cs(daily)
    assert "mean_ic" in stats and "icir" in stats
    assert stats["n_days"] == 2


def test_lab_shim_identical_to_guard() -> None:
    predictions, labels = _multi_index_series()
    g = guard_metrics.calculate_daily_cs_ic(predictions, labels)
    l = lab_metrics.calculate_daily_cs_ic(predictions, labels)
    pd.testing.assert_series_equal(g, l)

    assert guard_metrics.information_coefficient is lab_metrics.information_coefficient
    assert guard_metrics.calculate_daily_cs_ic is lab_metrics.calculate_daily_cs_ic
    assert guard_metrics.summarize_daily_cs is lab_metrics.summarize_daily_cs


def test_session_score_ic_delegates_guard() -> None:
    from datetime import date

    from ashare_infra.sim.session import TestSession

    predictions, labels = _multi_index_series()
    session = TestSession.for_ic(
        {"A", "B", "C"},
        date(2024, 1, 1),
        date(2024, 1, 31),
    )
    stats = session.score_ic(predictions, labels)
    expected = guard_metrics.summarize_daily_cs(
        guard_metrics.calculate_daily_cs_ic(predictions, labels)
    )
    assert stats == expected


def test_information_coefficient_empty() -> None:
    assert guard_metrics.information_coefficient(np.array([]), np.array([])) == 0.0
