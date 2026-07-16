from __future__ import annotations

from datetime import date

from ashare_lab.sim import DailyBar, LimitOrder, PaperBroker, SimConfig


def test_mark_to_market_includes_cash_and_positions() -> None:
    broker = PaperBroker(SimConfig(initial_cash=10_000, max_participation=1.0))
    broker.submit([LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=10.0)])
    bar = DailyBar(open=10.0, high=10.5, low=9.5, close=10.2, volume=1_000_000, prev_close=10.0)
    broker.match_day(date(2024, 1, 2), {"600000": bar})

    # cash = 10000 - 1000 - max(5, 1) = 8995; equity = 8995 + 100*10.2
    equity = broker.mark_to_market({"600000": bar}, price_attr="close")
    assert abs(equity - (8995 + 1020)) < 1e-9


def test_sell_before_buy_within_same_day_when_prior_lot_exists() -> None:
    broker = PaperBroker(SimConfig(initial_cash=20_000, max_participation=1.0))
    bar = DailyBar(open=10.0, high=10.5, low=9.5, close=10.0, volume=1_000_000, prev_close=10.0)

    broker.submit([LimitOrder(symbol="600000", side="BUY", shares=200, limit_price=10.0)])
    broker.match_day(date(2024, 1, 2), {"600000": bar})

    # Next day: sell 100 and buy 100 in same batch; sells run first.
    broker.submit(
        [
            LimitOrder(symbol="600000", side="SELL", shares=100, limit_price=10.0),
            LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=10.0, order_id="b2"),
        ]
    )
    result = broker.match_day(date(2024, 1, 3), {"600000": bar})
    sides = [f.side for f in result.fills]
    assert sides == ["SELL", "BUY"]
    assert broker.book.total_shares("600000") == 200
    # After day3: 100 shares from day2 lot + 100 from day3 lot.
    assert broker.book.sellable_shares("600000", today=date(2024, 1, 3)) == 100
    assert broker.book.sellable_shares("600000", today=date(2024, 1, 4)) == 200
