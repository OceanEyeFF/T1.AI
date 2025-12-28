from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Lot:
    acquired: date
    shares: int


class PositionBook:
    def __init__(self) -> None:
        self._lots: dict[str, list[Lot]] = {}

    def total_shares(self, symbol: str) -> int:
        return sum(lot.shares for lot in self._lots.get(symbol, []))

    def sellable_shares(self, symbol: str, today: date) -> int:
        return sum(lot.shares for lot in self._lots.get(symbol, []) if lot.acquired < today)

    def apply_buy(self, symbol: str, shares: int, today: date) -> None:
        if shares <= 0:
            return
        self._lots.setdefault(symbol, []).append(Lot(acquired=today, shares=shares))

    def apply_sell(self, symbol: str, shares: int, today: date) -> int:
        if shares <= 0:
            return 0

        lots = self._lots.get(symbol, [])
        remaining = shares
        for lot in lots:
            if remaining <= 0:
                break
            if lot.acquired >= today:
                continue
            sell_now = min(lot.shares, remaining)
            lot.shares -= sell_now
            remaining -= sell_now

        if lots:
            self._lots[symbol] = [lot for lot in lots if lot.shares > 0]
        return shares - remaining

    def symbols(self) -> list[str]:
        return sorted(self._lots.keys())
