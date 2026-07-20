"""B0 white-box: MomentumTopNStrategy target_weights + BacktestEngine drive."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_exec import MomentumTopNStrategy
from ashare_infra.sim.engine import BacktestConfig, BacktestEngine


def _hist(close: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": [1_000_000.0] * len(close),
        },
        index=pd.date_range(start, periods=len(close), freq="B"),
    )


def test_import_ashare_exec_package() -> None:
    import ashare_exec as pkg

    assert hasattr(pkg, "MomentumTopNStrategy")
    assert pkg.MomentumTopNStrategy is MomentumTopNStrategy


def test_momentum_top_n_filters_and_equal_weights() -> None:
    today = pd.Timestamp("2024-03-15")
    strat = MomentumTopNStrategy(top_n=2, lookback=2, min_history=4)
    history = {
        "A": _hist([10, 10, 11, 12]),
        "B": _hist([10, 10, 10, 10]),
        "C": pd.DataFrame({"open": [1, 2, 3, 4]}),
        "D": _hist([10, 11, 12]),  # too short for min_history=4 with lookback=2? 3 bars
    }
    # D has 3 closes; need max(4, 3)=4 → excluded
    w = strat.target_weights(today=today, history=history)
    assert set(w.keys()) == {"A", "B"}
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["A"] == pytest.approx(0.5)

    w2 = strat.target_weights(today=today, history={"C": history["C"], "D": history["D"]})
    assert w2 == {}


def test_momentum_ranks_higher_return_first() -> None:
    strat = MomentumTopNStrategy(top_n=1, lookback=5, min_history=10)
    dates = pd.date_range("2024-01-01", periods=20, freq="B")
    history = {
        "up": pd.DataFrame(
            {"close": [100.0 + i for i in range(20)]},
            index=dates,
        ),
        "down": pd.DataFrame(
            {"close": [100.0 - i * 0.5 for i in range(20)]},
            index=dates,
        ),
    }
    w = strat.target_weights(today=dates[-1], history=history)
    assert list(w.keys()) == ["up"]
    assert w["up"] == pytest.approx(1.0)


def test_backtest_engine_runs_with_momentum_strategy() -> None:
    """B0 gate: mechanical strategy drives BacktestEngine.run (no network)."""
    n = 80
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    data = {
        "600000": pd.DataFrame(
            {
                "open": np.linspace(10.0, 12.0, n),
                "high": np.linspace(10.2, 12.2, n),
                "low": np.linspace(9.8, 11.8, n),
                "close": np.linspace(10.0, 12.0, n),
                "volume": np.full(n, 1_000_000.0),
            },
            index=idx,
        ),
        "000001": pd.DataFrame(
            {
                "open": np.linspace(20.0, 18.0, n),
                "high": np.linspace(20.2, 18.2, n),
                "low": np.linspace(19.8, 17.8, n),
                "close": np.linspace(20.0, 18.0, n),
                "volume": np.full(n, 1_000_000.0),
            },
            index=idx,
        ),
    }
    engine = BacktestEngine(BacktestConfig(initial_cash=100_000.0, lot_size=100))
    strategy = MomentumTopNStrategy(top_n=1, lookback=5, min_history=20)
    result = engine.run(data, strategy=strategy)

    assert not result.equity_curve.empty
    assert "equity" in result.equity_curve.columns
    assert result.stats["final_equity"] > 0
    assert isinstance(result.diagnostics, dict)
