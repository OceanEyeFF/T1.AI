from __future__ import annotations

import math


def round_price(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def floor_to_lot(shares: float, lot: int = 100) -> int:
    if shares <= 0:
        return 0
    return int(math.floor(shares / lot) * lot)
