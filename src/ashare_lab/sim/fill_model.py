from __future__ import annotations

from dataclasses import dataclass

from ashare_lab.sim.types import DailyBar, LimitOrder, RejectReason
from ashare_lab.utils import floor_to_lot, round_price


@dataclass(frozen=True)
class TouchFill:
    """Pure matching result before cash / T+1 ledger constraints."""

    shares: int
    price: float
    reason_if_zero: RejectReason | None = None


def limit_band(prev_close: float, board_limit_pct: float = 0.10) -> tuple[float, float]:
    up = round_price(prev_close * (1.0 + board_limit_pct))
    down = round_price(prev_close * (1.0 - board_limit_pct))
    return up, down


def is_buy_blocked_limit_up(open_px: float, prev_close: float, board_limit_pct: float = 0.10) -> bool:
    limit_up, _ = limit_band(prev_close, board_limit_pct)
    return open_px >= limit_up - 1e-9


def is_sell_blocked_limit_down(
    open_px: float, prev_close: float, board_limit_pct: float = 0.10
) -> bool:
    _, limit_down = limit_band(prev_close, board_limit_pct)
    return open_px <= limit_down + 1e-9


def _bar_ok(bar: DailyBar) -> bool:
    vals = (bar.open, bar.high, bar.low, bar.close, bar.prev_close, bar.volume)
    if any(v != v for v in vals):  # NaN check
        return False
    if bar.volume < 0:
        return False
    if bar.high + 1e-12 < max(bar.open, bar.close, bar.low):
        return False
    if bar.low - 1e-12 > min(bar.open, bar.close, bar.high):
        return False
    return True


def match_limit_daily_ohlc(
    order: LimitOrder,
    bar: DailyBar,
    *,
    lot_size: int = 100,
    max_participation: float = 0.05,
    board_limit_pct: float = 0.10,
) -> TouchFill:
    """
    daily_ohlc_v1 fill model (no tick / no queue).

    Touch rules
    -----------
    BUY  : low  <= limit_price
    SELL : high >= limit_price

    Fill price (gap-through aware)
    ------------------------------
    BUY  : min(limit_price, open)  if touched
    SELL : max(limit_price, open)  if touched

    Size
    ----
    shares capped by lot size and max_participation * day volume.
    """
    shares = floor_to_lot(order.shares, lot=lot_size)
    if shares <= 0:
        return TouchFill(shares=0, price=0.0, reason_if_zero="zero_lot")

    if not _bar_ok(bar):
        return TouchFill(shares=0, price=0.0, reason_if_zero="invalid_bar")

    if order.side == "BUY":
        if is_buy_blocked_limit_up(bar.open, bar.prev_close, board_limit_pct):
            return TouchFill(shares=0, price=0.0, reason_if_zero="buy_blocked_limit_up")
        if bar.low > order.limit_price + 1e-9:
            return TouchFill(shares=0, price=0.0, reason_if_zero="not_touched")
        price = min(order.limit_price, bar.open)
    else:
        if is_sell_blocked_limit_down(bar.open, bar.prev_close, board_limit_pct):
            return TouchFill(shares=0, price=0.0, reason_if_zero="sell_blocked_limit_down")
        if bar.high < order.limit_price - 1e-9:
            return TouchFill(shares=0, price=0.0, reason_if_zero="not_touched")
        price = max(order.limit_price, bar.open)

    price = round_price(price)
    if price <= 0:
        return TouchFill(shares=0, price=0.0, reason_if_zero="invalid_bar")

    vol_cap = floor_to_lot(bar.volume * max_participation, lot=lot_size)
    fill_shares = min(shares, vol_cap) if max_participation < 1.0 else shares
    if fill_shares <= 0:
        return TouchFill(shares=0, price=price, reason_if_zero="insufficient_volume")

    return TouchFill(shares=fill_shares, price=price, reason_if_zero=None)
