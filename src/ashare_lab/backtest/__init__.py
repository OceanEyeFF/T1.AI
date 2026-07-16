"""Shim: ``ashare_lab.backtest`` → ``ashare_infra.sim`` (merged)."""

from __future__ import annotations

from ashare_infra.sim.book import Lot, PositionBook
from ashare_infra.sim.engine import BacktestConfig, BacktestEngine, BacktestResult

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "Lot",
    "PositionBook",
]
