"""Infra A unit: limit-up + missing_bar edges from fixture bars."""

from __future__ import annotations

from datetime import date

from ashare_infra.sim import LimitOrder, PaperBroker, SimConfig, match_limit_daily_ohlc
from tests.support import infra_a as fx


def test_limit_up_buy_blocked_on_fixture_day() -> None:
    day = date.fromisoformat(fx.expected("limit_up_buy_blocked_on"))
    bar = fx.bars_for_day("600004", day)
    assert bar is not None
    # open at limit-up vs prev_close
    assert abs(bar.open - round(bar.prev_close * 1.10, 2)) < 1e-9

    order = LimitOrder(symbol="600004", side="BUY", shares=100, limit_price=11.0)
    touch = match_limit_daily_ohlc(order, bar, lot_size=100, max_participation=1.0)
    assert touch.shares == 0
    assert touch.reason_if_zero == "buy_blocked_limit_up"

    broker = PaperBroker(SimConfig(initial_cash=50_000, max_participation=1.0))
    broker.submit([order])
    result = broker.match_day(day, {"600004": bar})
    assert not result.fills
    assert result.rejects and result.rejects[0].reason == "buy_blocked_limit_up"


def test_missing_bar_rejects_order() -> None:
    day = date.fromisoformat(fx.expected("missing_bar_day"))
    bar_normal = fx.bars_for_day("600000", day)
    assert bar_normal is not None

    broker = PaperBroker(SimConfig(initial_cash=50_000, max_participation=1.0))
    broker.submit(
        [LimitOrder(symbol="600003", side="BUY", shares=100, limit_price=20.0)]
    )
    # only normal bar present — 600003 missing
    result = broker.match_day(day, {"600000": bar_normal})
    assert result.rejects[0].reason == "missing_bar"
