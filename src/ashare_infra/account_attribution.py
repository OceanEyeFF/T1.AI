"""Attribute replay-window P&L to FIFO sales, remaining lots, income and fees."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ATTRIBUTION_COLUMNS = (
    "realized_gross_cents,realized_net_cents,unrealized_cents,fees_cents,income_cents,"
    "attribution_difference_cents,attribution_status"
)
SALE_FIELDS = (
    "date,currency,symbol,fill_id,order_id,shares,gross_proceeds_cents,fifo_cost_cents,"
    "sell_fees_cents,realized_gross_cents,realized_net_cents,confirmed_at,fifo_lots"
)
FILL_TYPES = {"buy_fill", "sell_fill"}


@dataclass
class Lot:
    source: str
    shares: int
    cost: int


def _allocate(amount: int, portion: int, remaining: int) -> int:
    return amount * portion // remaining


def _take_cost(lots: deque[Lot], quantity: int) -> tuple[int, list[dict]]:
    details = []
    while quantity:
        if not lots:
            raise ValueError("FIFO sale exceeds available lots")
        lot = lots[0]
        taken = min(quantity, lot.shares)
        cost = _allocate(lot.cost, taken, lot.shares)
        details.append({"source": lot.source, "shares": taken, "cost_cents": cost})
        lot.shares -= taken
        lot.cost -= cost
        quantity -= taken
        if not lot.shares:
            lots.popleft()
    return sum(row["cost_cents"] for row in details), details


def _order_amounts(order: list[tuple]) -> tuple[list[tuple], int, datetime] | str:
    fills = sorted(
        (item for item in order if item[2]["type"] in FILL_TYPES), key=lambda x: (x[0], x[2]["id"])
    )
    cash = [row for _, _, row in order if row["type"] == "trade_cash"]
    if not fills or not cash or any("gross_amount_cents" not in row for _, _, row in fills):
        return "missing_trade_amount"
    sides = {row["type"] for _, _, row in fills}
    symbols = {row["symbol"] for _, _, row in order if row["symbol"]}
    if (
        len(sides) != 1
        or len(symbols) != 1
        or any(row["event_date"] != row["effective_date"] for _, _, row in fills)
    ):
        return "unsupported_trade_basis"
    gross = sum(row["gross_amount_cents"] for _, _, row in fills)
    embedded_fees = sum(row.get("embedded_fee_cents", 0) for row in cash)
    signed_gross = gross if "sell_fill" in sides else -gross
    if sum(row["cash_delta_cents"] for row in cash) != signed_gross - embedded_fees:
        return "trade_cash_mismatch"
    fees = embedded_fees - sum(
        row["cash_delta_cents"] for _, _, row in order if row["type"] == "fee"
    )
    return fills, fees, max(known for _, known, _ in order)


def _unavailable(pnl: list[dict], status: str) -> list[dict]:
    fields = ATTRIBUTION_COLUMNS.split(",")
    for row in pnl:
        row.update(dict.fromkeys(fields))
        row["attribution_status"] = status
    return []


def _opening_lots(opening: dict, positions: list[dict], day: str) -> dict[str, deque[Lot]]:
    marks = {row["symbol"]: row["market_value_cents"] for row in positions if row["date"] == day}
    lots = defaultdict(deque)
    for symbol, qty in opening["positions"].items():
        if qty:
            if marks.get(symbol) is None:
                raise ValueError("missing opening valuation")
            lots[symbol].append(Lot("opening", qty, marks[symbol]))
    return lots


def attribute_pnl(
    pnl: list[dict], positions: list[dict], opening: dict, timeline: list[tuple], market_zone: str
) -> list[dict]:
    """Add daily P&L columns in place, returning one audit row per supported sell fill."""
    first, last = pnl[0]["date"], pnl[-1]["date"]
    try:
        lots = _opening_lots(opening, positions, first)
    except ValueError:
        return _unavailable(pnl, "missing_opening_valuation")
    orders = defaultdict(list)
    income_by_day = defaultdict(int)
    fees_by_day = defaultdict(int)
    known_by_day = defaultdict(list)
    for effective, known, event in timeline:
        day, kind = event["event_date"], event["type"]
        if kind in {"share_adjustment", "correction"} and event["effective_date"] <= last:
            return _unavailable(pnl, "unsupported_adjustment")
        if kind == "dividend":
            income_by_day[event["effective_date"]] += event["cash_delta_cents"]
            known_by_day[event["effective_date"]].append(known)
        elif first < day <= last and kind in (FILL_TYPES | {"trade_cash", "fee"}):
            if kind == "fee" and not event["order_id"]:
                fees_by_day[day] -= event["cash_delta_cents"]
                known_by_day[day].append(known)
            else:
                orders[(day, event["order_id"])].append((effective, known, event))

    fills_by_day = defaultdict(list)
    for (day, _), order in orders.items():
        details = _order_amounts(order)
        if isinstance(details, str):
            return _unavailable(pnl, details)
        fills, fees, known = details
        fees_by_day[day] += fees
        known_by_day[day].append(known)
        remaining = sum(row["gross_amount_cents"] for _, _, row in fills)
        for effective, _, row in fills:
            gross = row["gross_amount_cents"]
            allocated_fee = _allocate(fees, gross, remaining)
            fees -= allocated_fee
            remaining -= gross
            fills_by_day[day].append((effective, row, allocated_fee, known))

    gross_realized = fees = income = 0
    confirmed = None
    sales = []
    zone = ZoneInfo(market_zone)
    for daily in pnl:
        day = daily["date"]
        for _, row, sell_fee, known in sorted(fills_by_day[day], key=lambda x: (x[0], x[1]["id"])):
            symbol = row["symbol"]
            qty, gross = row["shares_delta"], row["gross_amount_cents"]
            if qty > 0:
                lots[symbol].append(Lot(row["id"], qty, gross))
                continue
            cost, matched_lots = _take_cost(lots[symbol], -qty)
            gross_realized += gross - cost
            sales.append(
                {
                    "date": day,
                    "currency": daily["currency"],
                    "symbol": symbol,
                    "fill_id": row["id"],
                    "order_id": row["order_id"],
                    "shares": -qty,
                    "gross_proceeds_cents": gross,
                    "fifo_cost_cents": cost,
                    "sell_fees_cents": sell_fee,
                    "realized_gross_cents": gross - cost,
                    "realized_net_cents": gross - cost - sell_fee,
                    "confirmed_at": known.isoformat(),
                    "fifo_lots": json.dumps(matched_lots),
                }
            )
        fees += fees_by_day[day]
        income += income_by_day[day]
        if known_by_day[day]:
            last_known = max(known_by_day[day])
            confirmed = last_known if confirmed is None else max(confirmed, last_known)
        cutoff = datetime.combine(date.fromisoformat(day) + timedelta(days=1), time.min, zone)
        if confirmed is not None and confirmed >= cutoff:
            _unavailable([daily], "unknown_cost_or_fee")
            continue
        known_value = daily["market_value_cents"]
        cost_remaining = sum(lot.cost for group in lots.values() for lot in group)
        unrealized = known_value - cost_remaining if known_value is not None else None
        net_realized = gross_realized + income - fees
        total = daily["pnl_since_open_cents"]
        difference = (
            net_realized + unrealized - total
            if unrealized is not None and total is not None
            else None
        )
        daily.update(
            {
                "realized_gross_cents": gross_realized,
                "realized_net_cents": net_realized,
                "unrealized_cents": unrealized,
                "fees_cents": fees,
                "income_cents": income,
                "attribution_difference_cents": difference,
                "attribution_status": "unverified"
                if difference is None
                else ("pass" if difference == 0 else "mismatch"),
            }
        )
    cutoff = datetime.combine(date.fromisoformat(last) + timedelta(days=1), time.min, zone)
    return [sale for sale in sales if datetime.fromisoformat(sale["confirmed_at"]) < cutoff]
