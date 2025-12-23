from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class Order:
    symbol: str
    side: Side
    shares: int


@dataclass(frozen=True)
class Fill:
    date: date
    symbol: str
    side: Side
    shares: int
    price: float
    turnover: float
    cost: float

