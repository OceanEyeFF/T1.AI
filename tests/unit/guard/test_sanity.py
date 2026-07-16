"""U-G6: direct unit tests for ashare_infra.guard.sanity (no ashare_lab imports)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ashare_infra.guard.sanity import (
    compute_baseline_ic,
    lag1_test,
    shuffle_test,
    time_reverse_test,
)
from tests.support import infra_a as fx


def _make_strong_signal(n_dates: int = 20, n_symbols: int = 10, seed: int = 42):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-02", periods=n_dates)
    symbols = [f"S{i:03d}" for i in range(n_symbols)]
    index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    true_signal = rng.randn(len(index))
    predictions = pd.Series(true_signal + rng.randn(len(index)) * 0.1, index=index)
    labels = pd.Series(true_signal + rng.randn(len(index)) * 0.3, index=index)
    return predictions, labels


def test_shuffle_destroys_strong_signal_ic() -> None:
    preds, labels = _make_strong_signal()
    baseline = compute_baseline_ic(preds, labels)
    assert baseline["mean_ic"] > 0.5
    result = shuffle_test(preds, labels, n_trials=5, threshold=0.15, seed=42)
    assert abs(result["mean_ic"]) < 0.15
    assert result["pass"] is True


def test_time_reverse_destroys_ic() -> None:
    preds, labels = _make_strong_signal()
    result = time_reverse_test(preds, labels, threshold=0.15)
    assert abs(result["mean_ic"]) < 0.15
    assert result["pass"] is True


def test_lag1_reduces_ic() -> None:
    preds, labels = _make_strong_signal(n_dates=30)
    baseline = compute_baseline_ic(preds, labels)
    # lag1_test requires baseline_mean_ic (API contract)
    result = lag1_test(preds, labels, baseline_mean_ic=baseline["mean_ic"])
    assert result["baseline_mean_ic"] == pytest.approx(baseline["mean_ic"], rel=1e-9)
    assert result["lag1_mean_ic"] < baseline["mean_ic"]


def test_infra_a_panel_baseline_positive() -> None:
    preds, labels = fx.load_ic_panel()
    stats = compute_baseline_ic(preds, labels)
    assert stats["mean_ic"] > 0.5
    assert stats["n_days"] == int(fx.expected("ic_panel_n_days"))


def test_sanity_module_does_not_import_ashare_lab() -> None:
    import ashare_infra.guard.sanity as sanity_mod

    text = Path(sanity_mod.__file__).read_text(encoding="utf-8")
    assert "ashare_lab" not in text
