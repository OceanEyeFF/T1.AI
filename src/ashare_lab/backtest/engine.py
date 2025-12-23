from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import numpy as np
import pandas as pd

from ashare_lab.backtest.book import PositionBook
from ashare_lab.types import Fill, Order
from ashare_lab.utils import floor_to_lot, round_price


class Strategy(Protocol):
    def target_weights(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        ...


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    max_daily_loss: float = 0.02
    total_friction_rate: float = 0.001
    min_cost_rmb: float = 5.0
    lot_size: int = 100


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame  # columns: equity, cash
    fills: pd.DataFrame
    stats: dict[str, float]
    diagnostics: dict[str, int]


def _limit_prices(prev_close: float) -> tuple[float, float]:
    limit_up = round_price(prev_close * 1.10)
    limit_down = round_price(prev_close * 0.90)
    return limit_up, limit_down


def _is_buy_blocked(open_px: float, prev_close: float) -> bool:
    limit_up, _ = _limit_prices(prev_close)
    return open_px >= limit_up - 1e-9


def _is_sell_blocked(open_px: float, prev_close: float) -> bool:
    _, limit_down = _limit_prices(prev_close)
    return open_px <= limit_down + 1e-9


class BacktestEngine:
    def __init__(self, config: BacktestConfig) -> None:
        self._config = config

    def run(self, data_by_symbol: dict[str, pd.DataFrame], strategy: Strategy) -> BacktestResult:
        calendar = _build_calendar(data_by_symbol)
        history = _align_history(data_by_symbol, calendar)

        cash = float(self._config.initial_cash)
        book = PositionBook()
        fills: list[Fill] = []
        equity_rows: list[dict[str, float | pd.Timestamp]] = []
        diagnostics = {
            "buy_blocked_limit_up": 0,
            "sell_blocked_limit_down": 0,
            "sell_blocked_tplus1": 0,
            "not_tradable_missing_open": 0,
            "not_tradable_missing_prev_close": 0,
            "risk_buy_disabled": 0,
        }

        prev_close_equity = cash

        for i in range(1, len(calendar)):
            today_ts = calendar[i]
            prev_ts = calendar[i - 1]
            today_d = today_ts.date()

            open_equity = self._mark_to_market(history, today_ts, book, cash, price_col="open")
            day_ret_open = open_equity / prev_close_equity - 1.0
            allow_buy = day_ret_open > -self._config.max_daily_loss
            if not allow_buy:
                diagnostics["risk_buy_disabled"] += 1

            targets = strategy.target_weights(today_ts, _slice_history(history, prev_ts))
            target_shares = self._weights_to_target_shares(
                targets=targets,
                today=today_ts,
                history=history,
                equity=open_equity,
            )

            orders = self._diff_to_orders(book, target_shares)

            sell_orders = [o for o in orders if o.side == "SELL"]
            buy_orders = [o for o in orders if o.side == "BUY"]

            cash = self._execute_orders(
                today=today_d,
                orders=sell_orders,
                history=history,
                book=book,
                cash=cash,
                fills=fills,
                allow_buy=True,
                diagnostics=diagnostics,
            )

            cash = self._execute_orders(
                today=today_d,
                orders=buy_orders,
                history=history,
                book=book,
                cash=cash,
                fills=fills,
                allow_buy=allow_buy,
                diagnostics=diagnostics,
            )

            close_equity = self._mark_to_market(history, today_ts, book, cash, price_col="close")
            equity_rows.append({"date": today_ts, "equity": close_equity, "cash": cash})
            prev_close_equity = close_equity

        equity_curve = pd.DataFrame(equity_rows).set_index("date")
        fills_df = pd.DataFrame([f.__dict__ for f in fills])
        stats = _calc_stats(equity_curve, fills_df)
        return BacktestResult(
            equity_curve=equity_curve,
            fills=fills_df,
            stats=stats,
            diagnostics=diagnostics,
        )

    def _mark_to_market(
        self,
        history: dict[str, pd.DataFrame],
        today: pd.Timestamp,
        book: PositionBook,
        cash: float,
        price_col: str,
    ) -> float:
        value = cash
        for symbol in book.symbols():
            shares = book.total_shares(symbol)
            if shares <= 0:
                continue
            bars = history[symbol]
            px = bars.at[today, price_col] if today in bars.index else np.nan
            if np.isnan(px):
                px = bars.at[today, "close"] if today in bars.index else np.nan
            if np.isnan(px):
                continue
            value += float(px) * shares
        return float(value)

    def _weights_to_target_shares(
        self,
        targets: dict[str, float],
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
        equity: float,
    ) -> dict[str, int]:
        out: dict[str, int] = {}
        for symbol, w in targets.items():
            if w <= 0:
                continue
            bars = history.get(symbol)
            if bars is None or today not in bars.index:
                continue
            open_px = float(bars.at[today, "open"])
            if np.isnan(open_px):
                continue
            target_value = equity * float(w)
            target_shares = floor_to_lot(target_value / open_px, lot=self._config.lot_size)
            out[symbol] = target_shares
        return out

    def _diff_to_orders(self, book: PositionBook, target_shares: dict[str, int]) -> list[Order]:
        symbols = set(book.symbols()) | set(target_shares.keys())
        orders: list[Order] = []
        for symbol in sorted(symbols):
            cur = book.total_shares(symbol)
            tgt = int(target_shares.get(symbol, 0))
            delta = tgt - cur
            if delta == 0:
                continue
            if delta > 0:
                orders.append(Order(symbol=symbol, side="BUY", shares=delta))
            else:
                orders.append(Order(symbol=symbol, side="SELL", shares=-delta))
        return orders

    def _execute_orders(
        self,
        today: date,
        orders: list[Order],
        history: dict[str, pd.DataFrame],
        book: PositionBook,
        cash: float,
        fills: list[Fill],
        allow_buy: bool,
        diagnostics: dict[str, int],
    ) -> float:
        for order in orders:
            bars = history.get(order.symbol)
            if bars is None:
                continue
            today_ts = pd.Timestamp(today)
            if today_ts not in bars.index:
                continue
            open_px = float(bars.at[today_ts, "open"])
            if np.isnan(open_px):
                diagnostics["not_tradable_missing_open"] += 1
                continue

            prev_close = float(bars.at[today_ts, "prev_close"])
            if not np.isfinite(prev_close):
                diagnostics["not_tradable_missing_prev_close"] += 1
                continue
            if order.side == "BUY":
                if not allow_buy:
                    continue
                if _is_buy_blocked(open_px, prev_close):
                    diagnostics["buy_blocked_limit_up"] += 1
                    continue
                shares = floor_to_lot(order.shares, lot=self._config.lot_size)
                if shares <= 0:
                    continue
                turnover = open_px * shares
                cost = max(self._config.min_cost_rmb, turnover * self._config.total_friction_rate)
                if turnover + cost > cash + 1e-9:
                    affordable = max(0.0, cash - self._config.min_cost_rmb)
                    shares = floor_to_lot(affordable / open_px, lot=self._config.lot_size)
                    if shares <= 0:
                        continue
                    turnover = open_px * shares
                    cost = max(self._config.min_cost_rmb, turnover * self._config.total_friction_rate)
                    if turnover + cost > cash + 1e-9:
                        continue
                cash -= turnover + cost
                book.apply_buy(order.symbol, shares, today=today)
                fills.append(
                    Fill(
                        date=today,
                        symbol=order.symbol,
                        side="BUY",
                        shares=shares,
                        price=open_px,
                        turnover=turnover,
                        cost=cost,
                    )
                )
            else:
                sellable = book.sellable_shares(order.symbol, today=today)
                shares = floor_to_lot(min(order.shares, sellable), lot=self._config.lot_size)
                if shares <= 0:
                    diagnostics["sell_blocked_tplus1"] += 1
                    continue
                if _is_sell_blocked(open_px, prev_close):
                    diagnostics["sell_blocked_limit_down"] += 1
                    continue
                executed = book.apply_sell(order.symbol, shares, today=today)
                if executed <= 0:
                    continue
                turnover = open_px * executed
                cost = max(self._config.min_cost_rmb, turnover * self._config.total_friction_rate)
                cash += turnover - cost
                fills.append(
                    Fill(
                        date=today,
                        symbol=order.symbol,
                        side="SELL",
                        shares=executed,
                        price=open_px,
                        turnover=turnover,
                        cost=cost,
                    )
                )
        return cash


def _build_calendar(data_by_symbol: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    dates: set[pd.Timestamp] = set()
    for df in data_by_symbol.values():
        dates.update(pd.DatetimeIndex(df.index).to_pydatetime())
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(list(dates))))
    return calendar


def _align_history(
    data_by_symbol: dict[str, pd.DataFrame], calendar: pd.DatetimeIndex
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for symbol, df in data_by_symbol.items():
        dfx = df.reindex(calendar)
        dfx["close"] = dfx["close"].ffill()
        dfx["prev_close"] = dfx["close"].shift(1)
        out[symbol] = dfx
    return out


def _slice_history(
    history: dict[str, pd.DataFrame], end_ts_inclusive: pd.Timestamp
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for symbol, df in history.items():
        out[symbol] = df.loc[:end_ts_inclusive].copy()
    return out


def _calc_stats(equity_curve: pd.DataFrame, fills_df: pd.DataFrame) -> dict[str, float]:
    if equity_curve.empty:
        return {}

    equity = equity_curve["equity"]
    rets = equity.pct_change().dropna()

    days = float(len(rets))
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (252.0 / max(days, 1.0)) - 1.0)

    peak = equity.cummax()
    dd = equity / peak - 1.0
    mdd = float(dd.min())

    total_cost = float(fills_df["cost"].sum()) if not fills_df.empty else 0.0
    total_turnover = float(fills_df["turnover"].sum()) if not fills_df.empty else 0.0
    avg_equity = float(equity.mean())
    turnover_ratio = float(total_turnover / max(avg_equity, 1e-9))

    return {
        "final_equity": float(equity.iloc[-1]),
        "cagr": cagr,
        "mdd": mdd,
        "turnover_ratio": turnover_ratio,
        "total_turnover": total_turnover,
        "total_cost": total_cost,
        "trade_count": float(len(fills_df)),
    }
