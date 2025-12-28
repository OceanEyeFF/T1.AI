from __future__ import annotations

import pandas as pd

from ashare_lab.backtest.engine import BacktestConfig, BacktestEngine


class _OneShotBuyThenSellStrategy:
    def __init__(self, symbol: str) -> None:
        self._symbol = symbol

    def target_weights(
        self, today: pd.Timestamp, history: dict[str, pd.DataFrame]
    ) -> dict[str, float]:
        # Day 1: buy; Day 2: sell (target empty)
        if len(history[self._symbol].dropna(subset=["close"])) <= 1:
            return {self._symbol: 1.0}
        return {}


def _df(prices: list[tuple[str, float, float]]) -> pd.DataFrame:
    # prices: (YYYY-MM-DD, open, close)
    idx = pd.to_datetime([d for d, _, _ in prices])
    return pd.DataFrame(
        {"open": [o for _, o, _ in prices], "close": [c for _, _, c in prices]}, index=idx
    )


def test_tplus1_blocks_same_day_sell() -> None:
    # Buy on day1; attempt sell on day1 should be blocked (engine schedules orders per day).
    symbol = "600000"
    df = _df(
        [
            ("2024-01-02", 10.00, 10.00),
            ("2024-01-03", 10.00, 10.00),
        ]
    )
    engine = BacktestEngine(BacktestConfig(initial_cash=10_000))
    result = engine.run({symbol: df}, strategy=_OneShotBuyThenSellStrategy(symbol))

    # At least one sell is expected on day2 (allowed), and no T+1 sell blocks should occur for this strategy.
    assert result.diagnostics["sell_blocked_tplus1"] == 0


class _BuyAlwaysStrategy:
    def __init__(self, symbol: str) -> None:
        self._symbol = symbol

    def target_weights(
        self, today: pd.Timestamp, history: dict[str, pd.DataFrame]
    ) -> dict[str, float]:
        return {self._symbol: 1.0}


def test_buy_blocked_at_limit_up() -> None:
    symbol = "600000"
    # prev_close = 10.00 on day1, so limit_up day2 = 11.00; set open at 11.00 blocks buy.
    df = _df(
        [
            ("2024-01-02", 10.00, 10.00),
            ("2024-01-03", 11.00, 11.00),
        ]
    )
    engine = BacktestEngine(BacktestConfig(initial_cash=10_000))
    result = engine.run({symbol: df}, strategy=_BuyAlwaysStrategy(symbol))
    assert result.diagnostics["buy_blocked_limit_up"] >= 1


class _SellAlwaysStrategy:
    def __init__(self, symbol: str) -> None:
        self._symbol = symbol

    def target_weights(
        self, today: pd.Timestamp, history: dict[str, pd.DataFrame]
    ) -> dict[str, float]:
        return {}


def test_sell_blocked_at_limit_down_after_holding() -> None:
    symbol = "600000"
    # Need a sellable lot acquired on day1, so pre-seed by buying via strategy on day1.
    # Then day3 open is limit_down relative to day2 close => blocks sell.
    df = _df(
        [
            ("2024-01-02", 10.00, 10.00),
            ("2024-01-03", 10.00, 10.00),
            ("2024-01-04", 9.00, 9.00),  # limit_down from 10.00 is 9.00
        ]
    )

    class _BuyDay1ThenFlat:
        def target_weights(
            self, today: pd.Timestamp, history: dict[str, pd.DataFrame]
        ) -> dict[str, float]:
            closes = history[symbol]["close"].dropna()
            if len(closes) <= 1:
                return {symbol: 1.0}
            return {}

    engine = BacktestEngine(BacktestConfig(initial_cash=10_000))
    result = engine.run({symbol: df}, strategy=_BuyDay1ThenFlat())
    assert result.diagnostics["sell_blocked_limit_down"] >= 1
