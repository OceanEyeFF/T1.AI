"""Rebuild daily holdings and cash from a broker ledger, then reconcile independently."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from ashare_infra.account_ledger import (
    MARKET_CURRENCIES,
    cents,
    csv_rows,
    iso_day,
    read_ledger,
    symbol_code,
)

REPORT_FIELDS = {
    "positions_daily": "date,symbol,shares,close_cents,price_date,price_status,market_value_cents",
    "account_daily": "date,cash_cents,cash_change_cents,known_market_value_cents,equity_cents,"
    "valuation_status,ledger_status,event_ids",
    "reconciliation": "date,metric,symbol,replayed,broker,difference,status,statement_batch_id",
    "operations": "id,date,action,symbol,side,shares,order_id,reason,fill_ids,batch_id,source_line,decision_at",
}


def _calendar(start: str, end: str):
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    for offset in range((last - first).days + 1):
        yield (first + timedelta(days=offset)).isoformat()


def _prices(path: Path | None, market: str):
    prices = defaultdict(dict)
    if path is None:
        return prices, None
    raw = path.read_bytes()
    for line, row in csv_rows(raw, "date,symbol,close"):
        day = iso_day(row["date"])
        symbol = symbol_code(row["symbol"], market)
        price = cents(row["close"])
        if price <= 0 or symbol in prices[day]:
            raise ValueError(f"{path}:{line}: expected one positive raw close per date and symbol")
        prices[day][symbol] = (day, price)
    return prices, hashlib.sha256(raw).hexdigest()


def _valuations(day: str, held: dict, latest: dict):
    rows = []
    for symbol, quantity in sorted(held.items()):
        price_day, price = latest.get(symbol, (None, None))
        status = "missing" if price is None else ("current" if price_day == day else "carried")
        rows.append(
            {
                "date": day,
                "symbol": symbol,
                "shares": quantity,
                "close_cents": price,
                "price_date": price_day,
                "price_status": status,
                "market_value_cents": None if price is None else quantity * price,
            }
        )
    return rows


def _comparison(
    day: str,
    metric: str,
    symbol: str,
    value: int,
    broker: int | None,
    statement: dict | None,
    complete: bool,
):
    difference = None if broker is None else value - broker
    if not complete:
        status = "incomplete"
    elif difference is None:
        status = "unverified"
    else:
        status = "pass" if difference == 0 else "mismatch"
    return {
        "date": day,
        "metric": metric,
        "symbol": symbol,
        "replayed": value,
        "broker": broker,
        "difference": difference,
        "status": status,
        "statement_batch_id": statement["batch_id"] if statement else None,
    }


def _reconcile(day: str, cash: int, held: dict, statement: dict | None, complete: bool):
    broker_positions = statement["positions"] if statement else {}
    yield _comparison(
        day,
        "cash_cents",
        "",
        cash,
        statement["cash_cents"] if statement else None,
        statement,
        complete,
    )
    for symbol in sorted(held.keys() | broker_positions.keys()):
        yield _comparison(
            day,
            "shares",
            symbol,
            held.get(symbol, 0),
            broker_positions.get(symbol, 0) if statement else None,
            statement,
            complete,
        )


def _covered(day: str, coverage: list[tuple[str, str]]) -> bool:
    return any(start <= day <= end for start, end in coverage)


def _manual_operations(records: dict, opening: str, through: str):
    fills_by_order = defaultdict(list)
    for event in sorted(records["events"].values(), key=lambda e: (e["event_date"], e["id"])):
        if (
            event["type"] in {"buy_fill", "sell_fill"}
            and event["order_id"]
            and opening < event["effective_date"] <= through
        ):
            fills_by_order[event["order_id"]].append(event["id"])
    return [
        dict(row, fill_ids="|".join(fills_by_order[row["order_id"]]))
        for row in sorted(records["operations"].values(), key=lambda r: (r["date"], r["id"]))
        if opening <= row["date"] <= through
    ]


def _write_reports(
    out_dir: Path, reports: dict, manifest: dict, *, decisions=None, pnl=None, sales=None
):
    if out_dir.exists():
        raise ValueError(f"output directory already exists: {out_dir}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out_dir.parent) as scratch:
        staged = Path(scratch) / "reports"
        staged.mkdir()
        for name, fields in REPORT_FIELDS.items():
            with (staged / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields.split(","))
                writer.writeheader()
                writer.writerows(reports[name])
        (staged / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if decisions is not None:
            from ashare_infra.account_attribution import SALE_FIELDS
            from ashare_infra.account_decisions import PNL_FIELDS

            (staged / "decision_replay.json").write_text(
                json.dumps(decisions, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            for name, fields, rows in (
                ("pnl_daily.csv", PNL_FIELDS, pnl),
                ("sales_pnl.csv", SALE_FIELDS, sales),
            ):
                with (staged / name).open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields.split(","))
                    writer.writeheader()
                    writer.writerows(rows)
        staged.rename(out_dir)


def replay_account(
    db: Path,
    account: str,
    opening: str,
    through: str,
    out_dir: Path,
    *,
    prices_csv: Path | None = None,
    through_batch: int | None = None,
    external_cache_dir: Path | None = None,
) -> dict:
    if iso_day(opening) >= iso_day(through):
        raise ValueError("through date must be after the opening close")
    market, batches, records = read_ledger(db, account, through_batch)
    snapshot = records["opening"].get(opening)
    if snapshot is None:
        raise ValueError(f"opening snapshot {opening} is missing for {account}")
    cash = snapshot["cash_cents"]
    held = {symbol: quantity for symbol, quantity in snapshot["positions"].items() if quantity}
    events_by_day = defaultdict(list)
    for event in records["events"].values():
        events_by_day[event["effective_date"]].append(event)
    coverage = [
        (batch["coverage_start"], batch["coverage_end"])
        for batch in batches
        if batch["kind"] == "events"
    ]
    prices, price_digest = _prices(prices_csv, market)
    latest: dict = {}
    for day in sorted(prices):
        if day >= opening:
            break
        latest.update(prices[day])

    reports = {name: [] for name in REPORT_FIELDS}
    first_gap = None
    for day in _calendar(opening, through):
        cash_change = 0
        events = events_by_day.get(day, []) if day != opening else []
        for event in events:
            cash_change += event["cash_delta_cents"]
            symbol = event["symbol"]
            if event["shares_delta"]:
                held[symbol] = held.get(symbol, 0) + event["shares_delta"]
                if event["type"] in {"share_adjustment", "correction"}:
                    latest.pop(symbol, None)
        if any(quantity < 0 for quantity in held.values()):
            raise ValueError(
                f"{day}: negative end-of-day holdings; check opening and broker events"
            )
        held = {symbol: quantity for symbol, quantity in held.items() if quantity}
        cash += cash_change
        if day != opening and first_gap is None and not _covered(day, coverage):
            first_gap = day

        latest.update(prices.get(day, {}))
        positions = _valuations(day, held, latest)
        known_value = sum(row["market_value_cents"] or 0 for row in positions)
        price_states = {row["price_status"] for row in positions}
        price_status = (
            "missing"
            if "missing" in price_states
            else ("carried" if "carried" in price_states else "current")
        )
        reports["positions_daily"].extend(positions)
        reports["account_daily"].append(
            {
                "date": day,
                "cash_cents": cash,
                "cash_change_cents": cash_change,
                "known_market_value_cents": known_value,
                "equity_cents": None if price_status == "missing" else cash + known_value,
                "valuation_status": price_status,
                "ledger_status": "complete" if first_gap is None else "incomplete",
                "event_ids": "|".join(event["id"] for event in events),
            }
        )
        if day != opening:
            reports["reconciliation"].extend(
                _reconcile(
                    day,
                    cash,
                    held,
                    records["statement"].get(day),
                    first_gap is None,
                )
            )

    reports["operations"] = _manual_operations(records, opening, through)
    comparisons = reports["reconciliation"]
    if first_gap:
        status = "incomplete"
    elif any(row["status"] == "mismatch" for row in comparisons):
        status = "mismatch"
    elif through not in records["statement"]:
        status = "unverified"
    else:
        status = "pass"
    manifest = {
        "account": account,
        "market": market,
        "currency": MARKET_CURRENCIES[market],
        "opening": opening,
        "through": through,
        "status": status,
        "first_coverage_gap": first_gap,
        "through_batch": batches[-1]["id"],
        "batches": batches,
        "prices_sha256": price_digest,
        "schema_version": 1,
    }
    decisions = pnl = sales = None
    if external_cache_dir is not None:
        from ashare_infra.account_decisions import decision_reports

        decisions, pnl, sales = decision_reports(
            records,
            market,
            opening,
            through,
            reports["account_daily"],
            reports["positions_daily"],
            external_cache_dir,
            first_gap,
        )
        manifest["decision_count"] = len(decisions)
        manifest["pnl_since_open_cents"] = pnl[-1]["pnl_since_open_cents"]
        manifest["attribution_status"] = pnl[-1]["attribution_status"]
    _write_reports(out_dir, reports, manifest, decisions=decisions, pnl=pnl, sales=sales)
    return manifest
