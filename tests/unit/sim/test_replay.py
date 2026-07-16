from __future__ import annotations

from datetime import date

import pandas as pd

from ashare_lab.sim import (
    LimitOrder,
    PaperBroker,
    ReplayConfig,
    ReplayEngine,
    ScriptedPlanner,
    SimConfig,
)


def _ohlcv(rows: list[tuple[str, float, float, float, float, float]]) -> pd.DataFrame:
    # (YYYY-MM-DD, open, high, low, close, volume_lots)
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
            "volume": [r[5] for r in rows],
        },
        index=idx,
    )


def test_replay_no_lookahead_planner_sees_only_prev_history() -> None:
    symbol = "600000"
    df = _ohlcv(
        [
            ("2024-01-02", 10.0, 10.2, 9.8, 10.0, 10_000),
            ("2024-01-03", 10.0, 10.5, 9.5, 10.2, 10_000),
            ("2024-01-04", 10.2, 10.4, 10.0, 10.1, 10_000),
        ]
    )
    seen: list[tuple[date, date | None, int]] = []

    class _Probe:
        def plans(self, today, prev_date, history, broker):
            n = len(history[symbol])
            seen.append((today, prev_date, n))
            return []

    ReplayEngine(ReplayConfig(sim=SimConfig(max_participation=1.0))).run(
        {symbol: df}, planner=_Probe()
    )
    assert seen[0] == (date(2024, 1, 2), None, 0)
    assert seen[1] == (date(2024, 1, 3), date(2024, 1, 2), 1)
    assert seen[2] == (date(2024, 1, 4), date(2024, 1, 3), 2)


def test_replay_scripted_buy_then_sell() -> None:
    symbol = "600000"
    df = _ohlcv(
        [
            ("2024-01-02", 10.0, 10.2, 9.8, 10.0, 10_000),
            ("2024-01-03", 10.0, 10.5, 9.5, 10.2, 10_000),
            ("2024-01-04", 10.2, 10.8, 10.0, 10.5, 10_000),
        ]
    )
    planner = ScriptedPlanner(
        {
            date(2024, 1, 3): [
                LimitOrder(symbol=symbol, side="BUY", shares=100, limit_price=10.0)
            ],
            date(2024, 1, 4): [
                LimitOrder(symbol=symbol, side="SELL", shares=100, limit_price=10.2)
            ],
        }
    )
    broker = PaperBroker(SimConfig(initial_cash=20_000, max_participation=1.0))
    result = ReplayEngine(ReplayConfig(sim=SimConfig(max_participation=1.0))).run(
        {symbol: df}, planner=planner, broker=broker
    )

    assert len(result.fills) == 2
    assert list(result.fills["side"]) == ["BUY", "SELL"]
    assert result.diagnostics["fills"] == 2
    assert broker.book.total_shares(symbol) == 0
    # Day1 has no prev_close bar for matching plans (none submitted); equity tracks.
    assert len(result.equity_curve) == 3
    assert result.equity_curve.iloc[-1]["cash"] > 0


def test_replay_volume_lots_converted_to_shares() -> None:
    symbol = "600000"
    # volume=10 lots -> 1000 shares; 5% participation -> 50 shares -> lot floor 0
    # with max_participation=0.05 and volume 100 lots -> 10000 shares * 0.05 = 500
    df = _ohlcv(
        [
            ("2024-01-02", 10.0, 10.0, 10.0, 10.0, 100),
            ("2024-01-03", 10.0, 10.2, 9.8, 10.0, 100),
        ]
    )
    planner = ScriptedPlanner(
        {
            date(2024, 1, 3): [
                LimitOrder(symbol=symbol, side="BUY", shares=10_000, limit_price=10.0)
            ],
        }
    )
    broker = PaperBroker(SimConfig(initial_cash=1_000_000, max_participation=0.05))
    result = ReplayEngine(
        ReplayConfig(sim=SimConfig(max_participation=0.05), volume_in_lots=True)
    ).run({symbol: df}, planner=planner, broker=broker)

    assert len(result.fills) == 1
    assert result.fills.iloc[0]["shares"] == 500


def test_first_calendar_day_cannot_build_bar_without_prev_close() -> None:
    symbol = "600000"
    df = _ohlcv(
        [
            ("2024-01-02", 10.0, 10.2, 9.8, 10.0, 10_000),
            ("2024-01-03", 9.5, 9.6, 9.0, 9.2, 10_000),
        ]
    )
    planner = ScriptedPlanner(
        {
            date(2024, 1, 2): [
                LimitOrder(symbol=symbol, side="BUY", shares=100, limit_price=10.0)
            ],
        }
    )
    result = ReplayEngine(ReplayConfig(sim=SimConfig(max_participation=1.0))).run(
        {symbol: df}, planner=planner
    )
    # No prev_close on first day => missing_bar reject, no fill.
    assert result.fills.empty
    assert not result.rejects.empty
    assert result.rejects.iloc[0]["reason"] == "missing_bar"
