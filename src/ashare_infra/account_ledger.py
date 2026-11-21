"""Import normalized broker CSVs for manually operated cash accounts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CSV_FIELDS = {
    "opening": "date,field,symbol,value",
    "statement": "date,field,symbol,value",
    "events": "id,type,event_date,effective_date,symbol,shares_delta,cash_delta,order_id,ref_id",
    "operations": "id,date,action,symbol,side,shares,order_id,reason",
}
MARKET_CURRENCIES = {"CN": "CNY", "HK": "HKD"}
MARKET_SYMBOLS = {"CN": r"[0-9]{6}\.(SH|SZ|BJ)", "HK": r"[0-9]{5}\.HK"}
MARKET_ZONES = {"CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong"}
TIMED_FIELDS = {
    "events": (
        ("effective_at", "known_at"),
        ("effective_at", "known_at", "gross_amount", "embedded_fee"),
    ),
    "operations": (("decision_at",),),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS account_profiles (
    account TEXT PRIMARY KEY,
    market TEXT NOT NULL CHECK (market IN ('CN', 'HK'))
);
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY,
    account TEXT NOT NULL,
    kind TEXT NOT NULL,
    digest TEXT NOT NULL,
    source TEXT NOT NULL,
    coverage_start TEXT NOT NULL,
    coverage_end TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (account, kind, digest, coverage_start, coverage_end)
);
CREATE TABLE IF NOT EXISTS records (
    account TEXT NOT NULL,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    payload TEXT NOT NULL,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    source_line INTEGER NOT NULL,
    PRIMARY KEY (account, kind, key)
);
"""


def iso_day(value: str) -> str:
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError(f"expected YYYY-MM-DD, got {value!r}")
    return value


def cents(value: str) -> int:
    match = re.fullmatch(r"([+-]?)([0-9]+)(?:\.([0-9]{1,2}))?", value)
    if not match:
        raise ValueError(f"expected an amount to two decimal places, got {value!r}")
    sign, whole, fraction = match.groups()
    amount = int(whole) * 100 + int((fraction or "").ljust(2, "0"))
    return -amount if sign == "-" else amount


def shares(value: str, *, signed: bool = False) -> int:
    if not re.fullmatch(r"[+-]?\d+" if signed else r"\d+", value):
        raise ValueError(f"invalid share quantity {value!r}")
    return int(value)


def symbol_code(value: str, market: str = "CN") -> str:
    if not re.fullmatch(MARKET_SYMBOLS[market], value):
        raise ValueError(f"invalid {market} market stock code: {value!r}")
    return value


def csv_rows(raw: bytes, fields: str, extra: tuple[tuple[str, ...], ...] = ()):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    expected = fields.split(",")
    if reader.fieldnames not in (expected, *(expected + list(columns) for columns in extra)):
        raise ValueError(f"expected CSV header {fields}")
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"line {reader.line_num}: wrong number of columns")
        yield reader.line_num, {name: value.strip() for name, value in row.items()}


def _timestamp(value: str, market: str, day: str | None = None) -> str:
    stamp = datetime.fromisoformat(
        value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    )
    if stamp.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    if day and stamp.astimezone(ZoneInfo(MARKET_ZONES[market])).date().isoformat() != day:
        raise ValueError("timestamp does not match the local ledger date")
    return stamp.astimezone(timezone.utc).isoformat()


def _snapshot(rows, market: str):
    day = None
    cash = None
    source_line = None
    positions = {}
    for line, row in rows:
        row_day = iso_day(row["date"])
        if day is not None and row_day != day:
            raise ValueError(f"line {line}: a snapshot must describe one date")
        day = row_day
        if row["field"] == "cash" and not row["symbol"] and cash is None:
            cash = cents(row["value"])
            source_line = line
        elif row["field"] == "position":
            symbol = symbol_code(row["symbol"], market)
            if symbol in positions:
                raise ValueError(f"line {line}: duplicate position for {symbol}")
            positions[symbol] = shares(row["value"])
        else:
            raise ValueError(f"line {line}: expected one cash row and optional position rows")
    if day is None or cash is None:
        raise ValueError("snapshot requires a cash row")
    yield day, {"cash_cents": cash, "positions": positions}, source_line


def _event(row, start: str, end: str, market: str):
    row["event_date"] = iso_day(row["event_date"])
    effective = iso_day(row["effective_date"])
    if not start <= effective <= end:
        raise ValueError("effective_date is outside the declared export coverage")
    quantity = shares(row.pop("shares_delta") or "0", signed=True)
    amount = cents(row.pop("cash_delta") or "0")
    if row["symbol"]:
        symbol_code(row["symbol"], market)
    kind = row["type"]
    if kind == "buy_fill":
        valid = quantity > 0 and amount == 0
    elif kind == "sell_fill":
        valid = quantity < 0 and amount == 0
    elif kind == "share_adjustment":
        valid = quantity != 0 and amount == 0
    elif kind in {"trade_cash", "fee", "transfer", "dividend"}:
        valid = quantity == 0 and amount != 0
        if kind == "fee":
            valid = valid and amount < 0
    elif kind == "correction":
        valid = bool(row["ref_id"]) and bool(quantity or amount)
    else:
        raise ValueError(f"unsupported event type {kind!r}")
    if not valid or (quantity and not row["symbol"]):
        raise ValueError(f"invalid share or cash movement for {kind}")
    if bool(row["ref_id"]) != (kind == "correction") or row["ref_id"] == row["id"]:
        raise ValueError("ref_id must identify an earlier event and is only used for corrections")
    effective_at = row.pop("effective_at", "")
    known_at = row.pop("known_at", "")
    if effective_at:
        row["effective_at"] = _timestamp(effective_at, market, effective)
    if known_at:
        row["known_at"] = _timestamp(known_at, market)
    gross = row.pop("gross_amount", "")
    embedded_fee = row.pop("embedded_fee", "")
    if gross:
        if kind not in {"buy_fill", "sell_fill"} or cents(gross) <= 0:
            raise ValueError("gross_amount must be a positive fill amount before fees")
        row["gross_amount_cents"] = cents(gross)
    if embedded_fee:
        if kind != "trade_cash" or cents(embedded_fee) < 0:
            raise ValueError(
                "embedded_fee must be a nonnegative fee already included in trade_cash"
            )
        row["embedded_fee_cents"] = cents(embedded_fee)
    return {**row, "shares_delta": quantity, "cash_delta_cents": amount}


def _operation(row, market: str):
    iso_day(row["date"])
    symbol_code(row["symbol"], market)
    if row["action"] not in {"plan", "submit", "cancel", "hold", "note"}:
        raise ValueError(f"unsupported manual action {row['action']!r}")
    if row["side"] not in {"", "buy", "sell"}:
        raise ValueError("manual side must be buy, sell or empty")
    if row["shares"]:
        row["shares"] = shares(row["shares"])
    decision_at = row.pop("decision_at", "")
    if decision_at:
        row["decision_at"] = _timestamp(decision_at, market, row["date"])
    return row


def _parse(raw: bytes, kind: str, start: str, end: str, market: str):
    rows = csv_rows(raw, CSV_FIELDS[kind], TIMED_FIELDS.get(kind, ()))
    if kind in {"opening", "statement"}:
        yield from _snapshot(rows, market)
        return
    for line, row in rows:
        try:
            if not row["id"]:
                raise ValueError("record ID is required")
            payload = (
                _event(row, start, end, market) if kind == "events" else _operation(row, market)
            )
        except ValueError as exc:
            raise ValueError(f"line {line}: {exc}") from exc
        yield row["id"], payload, line


def import_csv(
    db: Path,
    account: str,
    kind: str,
    path: Path,
    *,
    coverage_start: str = "",
    coverage_end: str = "",
    market: str = "CN",
) -> dict[str, int]:
    """Import one file atomically. Overlapping exports deduplicate on stable IDs."""
    if kind not in CSV_FIELDS or not account.strip():
        raise ValueError("valid import kind and account alias are required")
    if market not in MARKET_CURRENCIES:
        raise ValueError(f"unsupported account market: {market!r}")
    if kind == "events":
        if iso_day(coverage_start) > iso_day(coverage_end):
            raise ValueError("coverage start must precede or equal coverage end")
    elif coverage_start or coverage_end:
        raise ValueError("coverage dates apply only to events")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    items = list(_parse(raw, kind, coverage_start, coverage_end, market))
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        profile = conn.execute(
            "SELECT market FROM account_profiles WHERE account=?",
            (account,),
        ).fetchone()
        # Existing ledgers without a profile were all CN/CNY.
        existing_market = profile[0] if profile else None
        if (
            existing_market is None
            and conn.execute(
                "SELECT 1 FROM batches WHERE account=? LIMIT 1",
                (account,),
            ).fetchone()
        ):
            existing_market = "CN"
        if existing_market is not None and existing_market != market:
            raise ValueError(
                f"account {account!r} is already bound to {existing_market}, got {market}"
            )
        if profile is None:
            conn.execute("INSERT INTO account_profiles VALUES (?, ?)", (account, market))
        params = (account, kind, digest, coverage_start, coverage_end)
        previous = conn.execute(
            """SELECT id FROM batches WHERE account=? AND kind=? AND digest=?
               AND coverage_start=? AND coverage_end=?""",
            params,
        ).fetchone()
        if previous:
            return {"batch_id": previous[0], "inserted": 0, "duplicates": len(items)}
        batch = conn.execute(
            """INSERT INTO batches (account, kind, digest, coverage_start, coverage_end, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (*params, path.name),
        ).lastrowid
        duplicates = 0
        for key, payload, line in items:
            encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            old = conn.execute(
                "SELECT payload FROM records WHERE account=? AND kind=? AND key=?",
                (account, kind, key),
            ).fetchone()
            if old:
                if old[0] != encoded:
                    raise ValueError(f"line {line}: conflicting {kind} record {key!r}")
                duplicates += 1
                continue
            if kind == "events" and payload["ref_id"]:
                reference = conn.execute(
                    "SELECT payload FROM records WHERE account=? AND kind='events' AND key=?",
                    (account, payload["ref_id"]),
                ).fetchone()
                if reference is None or json.loads(reference[0])["symbol"] != payload["symbol"]:
                    raise ValueError(f"line {line}: correction requires an existing matching event")
            conn.execute(
                "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?)",
                (account, kind, key, encoded, batch, line),
            )
        return {"batch_id": batch, "inserted": len(items) - duplicates, "duplicates": duplicates}


def read_ledger(db: Path, account: str, through_batch: int | None = None):
    """Read records and provenance under one consistent SQLite snapshot."""
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        market = "CN"
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_profiles'",
        ).fetchone():
            profile = conn.execute(
                "SELECT market FROM account_profiles WHERE account=?",
                (account,),
            ).fetchone()
            if profile:
                market = profile[0]
        batches = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM batches WHERE account=? ORDER BY id",
                (account,),
            )
        ]
        if through_batch is not None:
            if not any(batch["id"] == through_batch for batch in batches):
                raise ValueError(f"unknown batch {through_batch} for {account}")
            batches = [batch for batch in batches if batch["id"] <= through_batch]
        records: dict[str, dict] = {kind: {} for kind in CSV_FIELDS}
        if batches:
            for row in conn.execute(
                "SELECT * FROM records WHERE account=? AND batch_id<=? ORDER BY key",
                (account, batches[-1]["id"]),
            ):
                records[row["kind"]][row["key"]] = {
                    **json.loads(row["payload"]),
                    "batch_id": row["batch_id"],
                    "source_line": row["source_line"],
                }
        return market, batches, records
