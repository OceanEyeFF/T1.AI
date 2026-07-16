from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from ashare_lab.types import Fill, Side

RejectReason = Literal[
    "missing_bar",
    "invalid_bar",
    "not_touched",
    "buy_blocked_limit_up",
    "sell_blocked_limit_down",
    "sell_blocked_tplus1",
    "insufficient_cash",
    "insufficient_volume",
    "zero_lot",
]


@dataclass(frozen=True)
class DailyBar:
    """One symbol-day OHLCV bar used by the daily fill model."""

    open: float
    high: float
    low: float
    close: float
    volume: float
    prev_close: float


@dataclass(frozen=True)
class LimitOrder:
    """Day limit order: price and size fixed before the session; no revise."""

    symbol: str
    side: Side
    shares: int
    limit_price: float
    order_id: str = ""


@dataclass(frozen=True)
class Reject:
    order: LimitOrder
    reason: RejectReason


@dataclass
class DayMatchResult:
    date: date
    fills: list[Fill] = field(default_factory=list)
    rejects: list[Reject] = field(default_factory=list)
    cash_end: float = 0.0
