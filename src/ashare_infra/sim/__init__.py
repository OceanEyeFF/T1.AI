"""Sim + backtest surface (merged under ashare_infra.sim)."""

from __future__ import annotations

from ashare_infra.sim.book import Lot, PositionBook
from ashare_infra.sim.broker import PaperBroker, SimConfig
from ashare_infra.sim.engine import BacktestConfig, BacktestEngine, BacktestResult
from ashare_infra.sim.fill_model import match_limit_daily_ohlc
from ashare_infra.sim.replay import (
    ReplayConfig,
    ReplayEngine,
    ReplayResult,
    ScriptedPlanner,
    build_calendar,
)
from ashare_infra.sim.session import TestSession
from ashare_infra.sim.types import DailyBar, DayMatchResult, LimitOrder, Reject

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "DailyBar",
    "DayMatchResult",
    "LimitOrder",
    "Lot",
    "PaperBroker",
    "PositionBook",
    "Reject",
    "ReplayConfig",
    "ReplayEngine",
    "ReplayResult",
    "ScriptedPlanner",
    "SimConfig",
    "TestSession",
    "build_calendar",
    "match_limit_daily_ohlc",
]
