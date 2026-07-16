"""Shim: ``ashare_lab.backtest.engine`` → ``ashare_infra.sim.engine``."""

from ashare_infra.sim.engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    Strategy,
    _calc_stats,
    _reconstruct_gross_equity,
)

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "Strategy",
    "_calc_stats",
    "_reconstruct_gross_equity",
]
