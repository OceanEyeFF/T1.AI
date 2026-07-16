from __future__ import annotations

from datetime import date

from ashare_lab.sim import DailyBar, LimitOrder, PaperBroker, SimConfig, match_limit_daily_ohlc


def _bar(
    *,
    open_: float = 10.0,
    high: float = 10.5,
    low: float = 9.5,
    close: float = 10.0,
    volume: float = 1_000_000,
    prev_close: float = 10.0,
) -> DailyBar:
    return DailyBar(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        prev_close=prev_close,
    )


def test_buy_not_touched_when_low_above_limit() -> None:
    order = LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=9.40)
    touch = match_limit_daily_ohlc(order, _bar(low=9.50))
    assert touch.shares == 0
    assert touch.reason_if_zero == "not_touched"


def test_buy_touched_fills_at_limit_when_open_above_limit() -> None:
    order = LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=9.80)
    touch = match_limit_daily_ohlc(order, _bar(open_=10.0, low=9.70))
    assert touch.shares == 100
    assert touch.price == 9.80


def test_buy_gap_through_fills_at_open() -> None:
    order = LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=10.00)
    touch = match_limit_daily_ohlc(
        order, _bar(open_=9.50, low=9.40, high=9.80, close=9.60)
    )
    assert touch.shares == 100
    assert touch.price == 9.50


def test_sell_not_touched_when_high_below_limit() -> None:
    order = LimitOrder(symbol="600000", side="SELL", shares=100, limit_price=10.60)
    touch = match_limit_daily_ohlc(order, _bar(high=10.50))
    assert touch.shares == 0
    assert touch.reason_if_zero == "not_touched"


def test_sell_gap_through_fills_at_open() -> None:
    order = LimitOrder(symbol="600000", side="SELL", shares=100, limit_price=10.00)
    touch = match_limit_daily_ohlc(
        order, _bar(open_=10.50, high=10.80, low=10.20, close=10.40)
    )
    assert touch.shares == 100
    assert touch.price == 10.50


def test_buy_blocked_at_limit_up_open() -> None:
    order = LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=11.00)
    touch = match_limit_daily_ohlc(
        order,
        _bar(open_=11.00, high=11.00, low=11.00, close=11.00, prev_close=10.00),
    )
    assert touch.shares == 0
    assert touch.reason_if_zero == "buy_blocked_limit_up"


def test_volume_participation_caps_fill() -> None:
    order = LimitOrder(symbol="600000", side="BUY", shares=10_000, limit_price=10.00)
    # 5% of 10_000 volume = 500 -> lot floor 500
    touch = match_limit_daily_ohlc(
        order,
        _bar(open_=9.90, low=9.80, volume=10_000),
        max_participation=0.05,
    )
    assert touch.shares == 500


def test_broker_buy_then_tplus1_blocks_same_day_sell() -> None:
    broker = PaperBroker(SimConfig(initial_cash=20_000, max_participation=1.0))
    d1 = date(2024, 1, 2)
    d2 = date(2024, 1, 3)
    bar = _bar(open_=10.0, high=10.2, low=9.8, close=10.0, volume=1_000_000)

    broker.submit([LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=10.0)])
    day1 = broker.match_day(d1, {"600000": bar})
    assert len(day1.fills) == 1
    assert day1.fills[0].side == "BUY"
    assert broker.book.total_shares("600000") == 100

    broker.submit([LimitOrder(symbol="600000", side="SELL", shares=100, limit_price=10.0)])
    day1_sell = broker.match_day(d1, {"600000": bar})
    assert day1_sell.fills == []
    assert any(r.reason == "sell_blocked_tplus1" for r in day1_sell.rejects)

    broker.submit([LimitOrder(symbol="600000", side="SELL", shares=100, limit_price=10.0)])
    day2 = broker.match_day(d2, {"600000": bar})
    assert len(day2.fills) == 1
    assert day2.fills[0].side == "SELL"
    assert broker.book.total_shares("600000") == 0


def test_broker_min_commission_on_small_trade() -> None:
    broker = PaperBroker(
        SimConfig(initial_cash=20_000, max_participation=1.0, total_friction_rate=0.001, min_cost_rmb=5.0)
    )
    # 100 shares * 10 = 1000 turnover; 0.1% = 1 < min 5
    broker.submit([LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=10.0)])
    result = broker.match_day(date(2024, 1, 2), {"600000": _bar()})
    assert len(result.fills) == 1
    assert result.fills[0].cost == 5.0
    assert abs(broker.cash - (20_000 - 1000 - 5)) < 1e-9


def test_broker_insufficient_cash_rejects() -> None:
    broker = PaperBroker(SimConfig(initial_cash=500, max_participation=1.0))
    broker.submit([LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=10.0)])
    result = broker.match_day(date(2024, 1, 2), {"600000": _bar()})
    assert result.fills == []
    assert any(r.reason == "insufficient_cash" for r in result.rejects)


def test_broker_unmatched_orders_expire() -> None:
    broker = PaperBroker(SimConfig(initial_cash=20_000, max_participation=1.0))
    broker.submit([LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=9.0)])
    day1 = broker.match_day(date(2024, 1, 2), {"600000": _bar(low=9.5)})
    assert day1.fills == []
    assert any(r.reason == "not_touched" for r in day1.rejects)

    # pending cleared; no automatic retry next day
    day2 = broker.match_day(date(2024, 1, 3), {"600000": _bar(low=8.5)})
    assert day2.fills == []
    assert day2.rejects == []
