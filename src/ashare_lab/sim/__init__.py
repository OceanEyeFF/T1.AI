"""Compatibility shim — re-exports ``ashare_infra.sim`` (paper + backtest)."""

from __future__ import annotations

from ashare_infra.sim import (
    DailyBar,
    DayMatchResult,
    LimitOrder,
    PaperBroker,
    Reject,
    ReplayConfig,
    ReplayEngine,
    ReplayResult,
    ScriptedPlanner,
    SimConfig,
    match_limit_daily_ohlc,
)

__all__ = [
    "DailyBar",
    "DayMatchResult",
    "LimitOrder",
    "PaperBroker",
    "Reject",
    "ReplayConfig",
    "ReplayEngine",
    "ReplayResult",
    "ScriptedPlanner",
    "SimConfig",
    "match_limit_daily_ohlc",
]
