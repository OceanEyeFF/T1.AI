"""Infra A unit: IC panel from fixture → guard.metrics."""

from __future__ import annotations

from ashare_infra.guard import metrics as guard_metrics
from ashare_lab.evaluation import metrics as lab_metrics
from tests.support import infra_a as fx


def test_ic_panel_shape_and_positive_mean() -> None:
    preds, labels = fx.load_ic_panel()
    daily = guard_metrics.calculate_daily_cs_ic(preds, labels, method="pearson")
    assert len(daily) == int(fx.expected("ic_panel_n_days"))
    stats = guard_metrics.summarize_daily_cs(daily)
    assert stats["n_days"] == int(fx.expected("ic_panel_n_days"))
    assert stats["mean_ic"] > 0.5  # synthetic panel is strongly ranked


def test_ic_unique_impl_via_lab_shim() -> None:
    preds, labels = fx.load_ic_panel()
    assert guard_metrics.calculate_daily_cs_ic is lab_metrics.calculate_daily_cs_ic
    g = guard_metrics.calculate_daily_cs_ic(preds, labels)
    l = lab_metrics.calculate_daily_cs_ic(preds, labels)
    assert list(g.values) == list(l.values)
