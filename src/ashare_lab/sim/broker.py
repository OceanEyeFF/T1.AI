from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ashare_lab.backtest.book import PositionBook
from ashare_lab.sim.fill_model import match_limit_daily_ohlc
from ashare_lab.sim.types import DailyBar, DayMatchResult, LimitOrder, Reject
from ashare_lab.types import Fill
from ashare_lab.utils import floor_to_lot


@dataclass(frozen=True)
class SimConfig:
    initial_cash: float = 20_000.0
    lot_size: int = 100
    total_friction_rate: float = 0.001
    min_cost_rmb: float = 5.0
    max_participation: float = 0.05
    board_limit_pct: float = 0.10


class PaperBroker:
    """
    Ultra-light local paper broker: limit orders in, daily bars match, ledger out.

    Operating assumption
    --------------------
    Orders are fixed before the session (morning/afternoon plan). This broker does
    not support revise/cancel during the bar; unmatched day orders expire at EOD.
    """

    def __init__(self, config: SimConfig | None = None) -> None:
        self._config = config or SimConfig()
        self._cash = float(self._config.initial_cash)
        self._book = PositionBook()
        self._pending: list[LimitOrder] = []

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def book(self) -> PositionBook:
        return self._book

    def submit(self, orders: list[LimitOrder]) -> None:
        for order in orders:
            shares = floor_to_lot(order.shares, lot=self._config.lot_size)
            if shares <= 0:
                continue
            self._pending.append(
                LimitOrder(
                    symbol=order.symbol,
                    side=order.side,
                    shares=shares,
                    limit_price=float(order.limit_price),
                    order_id=order.order_id,
                )
            )

    def match_day(self, trade_date: date, bars: dict[str, DailyBar]) -> DayMatchResult:
        """Match pending day orders against today's bars; expire leftovers."""
        sells = [o for o in self._pending if o.side == "SELL"]
        buys = [o for o in self._pending if o.side == "BUY"]
        self._pending = []

        result = DayMatchResult(date=trade_date)
        self._run_side(trade_date, sells, bars, result)
        self._run_side(trade_date, buys, bars, result)
        result.cash_end = self._cash
        return result

    def mark_to_market(self, bars: dict[str, DailyBar], price_attr: str = "close") -> float:
        value = self._cash
        for symbol in self._book.symbols():
            shares = self._book.total_shares(symbol)
            if shares <= 0:
                continue
            bar = bars.get(symbol)
            if bar is None:
                continue
            px = float(getattr(bar, price_attr))
            if px != px:  # NaN
                continue
            value += px * shares
        return float(value)

    def _run_side(
        self,
        trade_date: date,
        orders: list[LimitOrder],
        bars: dict[str, DailyBar],
        result: DayMatchResult,
    ) -> None:
        for order in orders:
            bar = bars.get(order.symbol)
            if bar is None:
                result.rejects.append(Reject(order=order, reason="missing_bar"))
                continue

            touch = match_limit_daily_ohlc(
                order,
                bar,
                lot_size=self._config.lot_size,
                max_participation=self._config.max_participation,
                board_limit_pct=self._config.board_limit_pct,
            )
            if touch.shares <= 0:
                reason = touch.reason_if_zero or "not_touched"
                result.rejects.append(Reject(order=order, reason=reason))
                continue

            if order.side == "BUY":
                self._apply_buy(trade_date, order, touch.shares, touch.price, result)
            else:
                self._apply_sell(trade_date, order, touch.shares, touch.price, result)

    def _friction(self, turnover: float) -> float:
        return max(self._config.min_cost_rmb, turnover * self._config.total_friction_rate)

    def _apply_buy(
        self,
        trade_date: date,
        order: LimitOrder,
        shares: int,
        price: float,
        result: DayMatchResult,
    ) -> None:
        shares = floor_to_lot(shares, lot=self._config.lot_size)
        if shares <= 0:
            result.rejects.append(Reject(order=order, reason="zero_lot"))
            return

        turnover = price * shares
        cost = self._friction(turnover)
        if turnover + cost > self._cash + 1e-9:
            affordable = max(0.0, self._cash - self._config.min_cost_rmb)
            shares = floor_to_lot(affordable / price, lot=self._config.lot_size)
            if shares <= 0:
                result.rejects.append(Reject(order=order, reason="insufficient_cash"))
                return
            turnover = price * shares
            cost = self._friction(turnover)
            if turnover + cost > self._cash + 1e-9:
                result.rejects.append(Reject(order=order, reason="insufficient_cash"))
                return

        self._cash -= turnover + cost
        self._book.apply_buy(order.symbol, shares, today=trade_date)
        result.fills.append(
            Fill(
                date=trade_date,
                symbol=order.symbol,
                side="BUY",
                shares=shares,
                price=price,
                turnover=turnover,
                cost=cost,
            )
        )

    def _apply_sell(
        self,
        trade_date: date,
        order: LimitOrder,
        shares: int,
        price: float,
        result: DayMatchResult,
    ) -> None:
        sellable = self._book.sellable_shares(order.symbol, today=trade_date)
        shares = floor_to_lot(min(shares, sellable), lot=self._config.lot_size)
        if shares <= 0:
            result.rejects.append(Reject(order=order, reason="sell_blocked_tplus1"))
            return

        executed = self._book.apply_sell(order.symbol, shares, today=trade_date)
        if executed <= 0:
            result.rejects.append(Reject(order=order, reason="sell_blocked_tplus1"))
            return

        turnover = price * executed
        cost = self._friction(turnover)
        self._cash += turnover - cost
        result.fills.append(
            Fill(
                date=trade_date,
                symbol=order.symbol,
                side="SELL",
                shares=executed,
                price=price,
                turnover=turnover,
                cost=cost,
            )
        )
