from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

import numpy as np
import pandas as pd

from ashare_infra.sim.broker import PaperBroker, SimConfig
from ashare_infra.sim.types import DailyBar, DayMatchResult, LimitOrder
from ashare_infra.types import Fill


class PlanProvider(Protocol):
    """
    Emit day orders using only information available before the session.

    ``history`` is sliced to ``prev_date`` inclusive (no peek at ``today`` bars).
    """

    def plans(
        self,
        today: date,
        prev_date: date | None,
        history: dict[str, pd.DataFrame],
        broker: PaperBroker,
    ) -> list[LimitOrder]: ...


@dataclass(frozen=True)
class ReplayConfig:
    sim: SimConfig = field(default_factory=SimConfig)
    # AkShare/TuShare daily volume is in lots (手 = 100 shares);
    # ODP/yfinance volume is already in shares → set False for odp frames.
    volume_in_lots: bool = True


@dataclass
class ReplayResult:
    equity_curve: pd.DataFrame  # date index: equity, cash
    fills: pd.DataFrame
    rejects: pd.DataFrame
    day_results: list[DayMatchResult]
    diagnostics: dict[str, int]


def _to_date(ts: pd.Timestamp | date) -> date:
    if isinstance(ts, date) and not isinstance(ts, pd.Timestamp):
        return ts
    return pd.Timestamp(ts).date()


def build_calendar(data_by_symbol: dict[str, pd.DataFrame]) -> list[date]:
    dates: set[date] = set()
    for df in data_by_symbol.values():
        for ts in pd.DatetimeIndex(df.index):
            dates.add(_to_date(ts))
    return sorted(dates)


def row_to_bar(
    row: pd.Series,
    prev_close: float,
    *,
    volume_in_lots: bool = True,
) -> DailyBar | None:
    try:
        o = float(row["open"])
        h = float(row["high"])
        l = float(row["low"])
        c = float(row["close"])
        v = float(row["volume"])
        pc = float(prev_close)
    except (KeyError, TypeError, ValueError):
        return None
    if not all(np.isfinite(x) for x in (o, h, l, c, v, pc)):
        return None
    if volume_in_lots:
        v *= 100.0
    return DailyBar(open=o, high=h, low=l, close=c, volume=v, prev_close=pc)


def bars_for_day(
    data_by_symbol: dict[str, pd.DataFrame],
    today: date,
    *,
    volume_in_lots: bool = True,
) -> dict[str, DailyBar]:
    """Build today's DailyBar map; prev_close = prior close in that symbol's series."""
    today_ts = pd.Timestamp(today)
    out: dict[str, DailyBar] = {}
    for symbol, df in data_by_symbol.items():
        if today_ts not in df.index:
            continue
        loc = df.index.get_loc(today_ts)
        if isinstance(loc, slice) or not np.isscalar(loc):
            continue
        i = int(loc)
        if i <= 0:
            continue
        prev_close = float(df.iloc[i - 1]["close"])
        bar = row_to_bar(df.iloc[i], prev_close, volume_in_lots=volume_in_lots)
        if bar is not None:
            out[symbol] = bar
    return out


def history_until(
    data_by_symbol: dict[str, pd.DataFrame],
    end_inclusive: date | None,
) -> dict[str, pd.DataFrame]:
    if end_inclusive is None:
        return {s: df.iloc[0:0].copy() for s, df in data_by_symbol.items()}
    end_ts = pd.Timestamp(end_inclusive)
    return {s: df.loc[:end_ts].copy() for s, df in data_by_symbol.items()}


class ReplayEngine:
    """
    Day-by-day paper replay:

    1. Plan with history ≤ T-1 (no look-ahead)
    2. Match plans against T bars
    3. Mark equity at T close
    """

    def __init__(self, config: ReplayConfig | None = None) -> None:
        self._config = config or ReplayConfig()

    def run(
        self,
        data_by_symbol: dict[str, pd.DataFrame],
        planner: PlanProvider,
        broker: PaperBroker | None = None,
    ) -> ReplayResult:
        broker = broker or PaperBroker(self._config.sim)
        calendar = build_calendar(data_by_symbol)
        equity_rows: list[dict[str, float | date]] = []
        all_fills: list[Fill] = []
        reject_rows: list[dict[str, object]] = []
        day_results: list[DayMatchResult] = []
        diagnostics = {
            "days": 0,
            "plan_orders": 0,
            "fills": 0,
            "rejects": 0,
            "days_without_bars": 0,
        }

        for i, today in enumerate(calendar):
            prev_date = calendar[i - 1] if i > 0 else None
            hist = history_until(data_by_symbol, prev_date)
            orders = planner.plans(today, prev_date, hist, broker)
            diagnostics["plan_orders"] += len(orders)
            if orders:
                broker.submit(orders)

            bars = bars_for_day(
                data_by_symbol,
                today,
                volume_in_lots=self._config.volume_in_lots,
            )
            if not bars and orders:
                diagnostics["days_without_bars"] += 1

            day = broker.match_day(today, bars)
            day_results.append(day)
            diagnostics["days"] += 1
            diagnostics["fills"] += len(day.fills)
            diagnostics["rejects"] += len(day.rejects)
            all_fills.extend(day.fills)
            for r in day.rejects:
                reject_rows.append(
                    {
                        "date": today,
                        "symbol": r.order.symbol,
                        "side": r.order.side,
                        "shares": r.order.shares,
                        "limit_price": r.order.limit_price,
                        "order_id": r.order.order_id,
                        "reason": r.reason,
                    }
                )

            # Holdings without today's bar (e.g. suspension) contribute 0 to the
            # mark — the equity curve dips on those days and recovers after.
            equity = broker.mark_to_market(bars, price_attr="close") if bars else broker.cash
            equity_rows.append({"date": today, "equity": float(equity), "cash": float(broker.cash)})

        equity_curve = pd.DataFrame(equity_rows).set_index("date")
        fills_df = pd.DataFrame([f.__dict__ for f in all_fills])
        rejects_df = pd.DataFrame(reject_rows)
        return ReplayResult(
            equity_curve=equity_curve,
            fills=fills_df,
            rejects=rejects_df,
            day_results=day_results,
            diagnostics=diagnostics,
        )


@dataclass
class ScriptedPlanner:
    """Deterministic plans keyed by trade date — useful for tests and manual scenarios."""

    schedule: dict[date, list[LimitOrder]]

    def plans(
        self,
        today: date,
        prev_date: date | None,
        history: dict[str, pd.DataFrame],
        broker: PaperBroker,
    ) -> list[LimitOrder]:
        _ = prev_date, history, broker
        return list(self.schedule.get(today, []))
