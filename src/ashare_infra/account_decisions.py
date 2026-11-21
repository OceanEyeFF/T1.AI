"""Attach point-in-time account and external-data context to manual decisions."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from ashare_infra.account_attribution import ATTRIBUTION_COLUMNS, attribute_pnl
from ashare_infra.account_ledger import MARKET_CURRENCIES, MARKET_ZONES
from ashare_infra.lake import DataLake

PNL_FIELDS = (
    "date,currency,cash_cents,pending_settlement_cents,market_value_cents,"
    "equity_with_pending_cents,net_transfers_cents,pnl_since_open_cents,pnl_change_cents,status,"
    + ATTRIBUTION_COLUMNS
)


def _timeline(records: dict, opening: str, through: str) -> list[tuple]:
    timeline = []
    cash_orders = {
        row["order_id"]
        for row in records["events"].values()
        if row["type"] == "trade_cash" and row["order_id"]
    }
    for event in records["events"].values():
        if (
            event["effective_date"] <= opening
            or min(event["effective_date"], event["event_date"]) > through
        ):
            continue
        if not event.get("effective_at"):
            raise ValueError(f"event {event['id']}: decision replay requires effective_at")
        delayed_cash = _settlement(event) and event["event_date"] < event["effective_date"]
        if delayed_cash and not event.get("known_at"):
            raise ValueError(f"event {event['id']}: delayed cash requires known_at")
        if event["type"] in {"buy_fill", "sell_fill"} and event["order_id"] not in cash_orders:
            raise ValueError(f"fill {event['id']}: P&L requires a linked trade_cash record")
        effective = datetime.fromisoformat(event["effective_at"])
        known = datetime.fromisoformat(event.get("known_at", event["effective_at"]))
        timeline.append((effective, known, event))
    return timeline


def _settlement(event: dict) -> bool:
    return event["type"] in {"trade_cash", "fee"}


def _pending(timeline: list[tuple], cutoff: datetime) -> int:
    return sum(
        row["cash_delta_cents"]
        for effective, known, row in timeline
        if _settlement(row) and known < cutoff <= effective
    )


def _state_before(snapshot: dict, timeline: list[tuple], cutoff: datetime) -> dict:
    cash = snapshot["cash_cents"]
    positions = snapshot["positions"].copy()
    for effective, known, event in timeline:
        if effective >= cutoff or known >= cutoff:
            continue
        cash += event["cash_delta_cents"]
        if event["shares_delta"]:
            symbol = event["symbol"]
            positions[symbol] = positions.get(symbol, 0) + event["shares_delta"]
    if any(quantity < 0 for quantity in positions.values()):
        raise ValueError(f"negative position before decision at {cutoff.isoformat()}")
    return {
        "cash_cents": cash,
        "positions": {
            symbol: quantity for symbol, quantity in sorted(positions.items()) if quantity
        },
        "pending_settlement_cents": _pending(timeline, cutoff),
    }


def _daily_pnl(account_daily: list[dict], timeline: list[tuple], market: str) -> list[dict]:
    rows = []
    previous = None
    baseline = None
    zone = ZoneInfo(MARKET_ZONES[market])
    for daily in account_daily:
        day = daily["date"]
        cutoff = datetime.combine(date.fromisoformat(day) + timedelta(days=1), time.min, zone)
        pending = _pending(timeline, cutoff)
        transfers = sum(
            row["cash_delta_cents"]
            for _, _, row in timeline
            if row["type"] == "transfer" and row["effective_date"] <= day
        )
        quoted_equity = daily["equity_cents"]
        complete = daily["ledger_status"] == "complete"
        missing_settlement = any(
            _settlement(row)
            and row["event_date"] <= day < row["effective_date"]
            and known >= cutoff
            for _, known, row in timeline
        )
        equity = (
            quoted_equity + pending
            if quoted_equity is not None and complete and not missing_settlement
            else None
        )
        if not rows:
            baseline = equity
        pnl = equity - baseline - transfers if equity is not None and baseline is not None else None
        rows.append(
            {
                "date": day,
                "currency": MARKET_CURRENCIES[market],
                "cash_cents": daily["cash_cents"],
                "pending_settlement_cents": pending if complete else None,
                "market_value_cents": daily["known_market_value_cents"]
                if quoted_equity is not None
                else None,
                "equity_with_pending_cents": equity,
                "net_transfers_cents": transfers,
                "pnl_since_open_cents": pnl,
                "pnl_change_cents": pnl - previous
                if pnl is not None and previous is not None
                else None,
                "status": (
                    "incomplete_ledger"
                    if not complete
                    else "unknown_settlement"
                    if missing_settlement
                    else daily["valuation_status"]
                    if pnl is not None
                    else "missing_valuation"
                ),
            }
        )
        previous = pnl
    return rows


def decision_reports(
    records: dict,
    market: str,
    opening: str,
    through: str,
    account_daily: list[dict],
    positions_daily: list[dict],
    external_cache_dir: Path,
    first_gap: str | None,
) -> tuple[list[dict], list[dict], list[dict]]:
    timeline = _timeline(records, opening, through)
    lake = DataLake(cache_dir=external_cache_dir)
    zone = ZoneInfo(MARKET_ZONES[market])
    snapshot = records["opening"][opening]
    decisions = []
    for operation in records["operations"].values():
        if not opening < operation["date"] <= through:
            continue
        if not operation.get("decision_at"):
            raise ValueError(f"operation {operation['id']}: decision replay requires decision_at")
        cutoff = datetime.fromisoformat(operation["decision_at"])
        if first_gap is not None and first_gap <= operation["date"]:
            raise ValueError(
                f"operation {operation['id']}: account coverage has a gap since {first_gap}"
            )
        state = _state_before(snapshot, timeline, cutoff)
        series = lake.load_external_daily(as_of=cutoff)
        decisions.append(
            {
                **operation,
                **state,
                "market": market,
                "currency": MARKET_CURRENCIES[market],
                "decision_at": cutoff.astimezone(zone).isoformat(),
                "external": {
                    code: {"rows": len(bars), "latest": bars[-1] if bars else None}
                    for code, bars in series.items()
                },
            }
        )
    decisions.sort(key=lambda row: (row["decision_at"], row["id"]))
    pnl = _daily_pnl(account_daily, timeline, market)
    sales = attribute_pnl(pnl, positions_daily, snapshot, timeline, MARKET_ZONES[market])
    return decisions, pnl, sales
