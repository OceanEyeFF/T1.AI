"""TuShare benchmark and futures daily bars with observation-time replay."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# TuShare code -> (endpoint, exchange-local timezone).
SERIES = {
    "SPX": ("index_global", "America/New_York"),
    "IXIC": ("index_global", "America/New_York"),
    "AU.SHF": ("fut_daily", "Asia/Shanghai"),
    "HSI": ("index_global", "Asia/Hong_Kong"),
    "HKTECH": ("index_global", "Asia/Hong_Kong"),
    "CU.SHF": ("fut_daily", "Asia/Shanghai"),
    "SC.INE": ("fut_daily", "Asia/Shanghai"),
    "PG.DCE": ("fut_daily", "Asia/Shanghai"),
    "TA.ZCE": ("fut_daily", "Asia/Shanghai"),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_versions (
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    available_at TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (symbol, trade_date, available_at)
);
"""


def _utc_text(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("decision time must include a timezone or UTC offset")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / "tushare_external" / "daily.sqlite"


def _query_tushare(
    endpoint: str,
    symbol: str,
    start: date,
    end: date,
    token: str,
    *,
    session: requests.Session | None = None,
) -> dict:
    from ashare_infra.data.tushare_https import query

    fields = "ts_code,trade_date,open,high,low,close,vol,amount"
    if endpoint == "fut_daily":
        fields += ",settle,oi"
    return query(
        endpoint,
        {
            "ts_code": symbol,
            "start_date": start.strftime("%Y%m%d"),
            "end_date": end.strftime("%Y%m%d"),
        },
        token,
        fields=fields,
        session=session,
    )


def _normalize(data: dict, symbol: str, start: date, end: date) -> dict[str, str]:
    fields, items = data.get("fields"), data.get("items")
    if not isinstance(fields, list) or not isinstance(items, list):
        raise TypeError(f"{symbol}: invalid TuShare daily response shape")
    if any(not isinstance(field, str) for field in fields) or len(set(fields)) != len(fields):
        raise ValueError(f"{symbol}: invalid TuShare field names")
    # A saturated response may have been truncated by the upstream endpoint.
    if len(items) >= 2000:
        raise ValueError(f"{symbol}: response may be truncated; split the requested date range")
    required = {"ts_code", "trade_date", "open", "high", "low", "close"}
    bar_fields = (required - {"ts_code", "trade_date"}) | {"vol", "amount", "settle", "oi"}
    if items and not required.issubset(fields):
        raise ValueError(f"{symbol}: response is missing daily fields")
    bars = {}
    for item in items:
        if not isinstance(item, list) or len(item) != len(fields):
            raise ValueError(f"{symbol}: invalid daily row")
        row = dict(zip(fields, item, strict=True))
        day_key = str(row.pop("trade_date"))
        if len(day_key) != 8 or not day_key.isascii() or not day_key.isdecimal():
            raise ValueError(f"{symbol}: invalid TuShare trade date")
        traded = date.fromisoformat(f"{day_key[:4]}-{day_key[4:6]}-{day_key[6:]}")
        if row.pop("ts_code") != symbol or not start <= traded <= end:
            raise ValueError(f"{symbol}: unexpected symbol or trade date in daily response")
        row = {key: value for key, value in row.items() if key in bar_fields}
        for key, value in row.items():
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError(f"{symbol} {traded}: invalid {key}")
        if row["close"] is None:
            raise ValueError(f"{symbol} {traded}: missing close")
        day = traded.isoformat()
        if day in bars:
            raise ValueError(f"{symbol} {traded}: duplicate trade date")
        bars[day] = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return bars


def _save(
    cache_dir: Path, symbol: str, endpoint: str, bars: dict[str, str], available_at: str
) -> int:
    if not bars:
        return 0
    path = _cache_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    inserted = 0
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        for day, payload in sorted(bars.items()):
            previous = conn.execute(
                "SELECT available_at, payload FROM daily_versions WHERE symbol=? AND trade_date=? "
                "ORDER BY available_at DESC LIMIT 1",
                (symbol, day),
            ).fetchone()
            if previous and previous[1] == payload:
                continue
            if previous and available_at <= previous[0]:
                raise ValueError(f"{symbol} {day}: observation arrived out of order; retry fetch")
            conn.execute(
                "INSERT INTO daily_versions VALUES (?, ?, ?, ?, ?)",
                (symbol, day, available_at, endpoint, payload),
            )
            inserted += 1
    return inserted


def refresh_external_daily(
    cache_dir: Path,
    symbol: str,
    start: date,
    end: date,
    token: str | None = None,
    *,
    session: requests.Session | None = None,
) -> dict:
    """Capture completed daily bars. The date of the open exchange-local day is excluded."""
    if start > end:
        raise ValueError("start date must be on or before end date")
    if symbol not in SERIES:
        raise ValueError(f"unsupported external symbol: {symbol}")
    endpoint, zone = SERIES[symbol]
    effective_end = min(end, _now().astimezone(ZoneInfo(zone)).date() - timedelta(days=1))
    if start > effective_end:
        return {
            "symbol": symbol,
            "rows": 0,
            "inserted": 0,
            "available_at": None,
            "effective_end": effective_end.isoformat(),
        }
    token = token or os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise ValueError("TUSHARE_TOKEN is required to refresh external data")
    data = _query_tushare(endpoint, symbol, start, effective_end, token, session=session)
    observed_at = _utc_text(_now())
    bars = _normalize(data, symbol, start, effective_end)
    inserted = _save(cache_dir, symbol, endpoint, bars, observed_at)
    return {
        "symbol": symbol,
        "rows": len(bars),
        "inserted": inserted,
        "available_at": observed_at,
        "effective_end": effective_end.isoformat(),
    }


def read_external_daily(
    cache_dir: Path, as_of: datetime, *, start: date | None = None
) -> dict[str, list[dict]]:
    """Read the version of each bar observable by the cutoff in one cache snapshot."""
    cutoff = _utc_text(as_of)
    result: dict[str, list[dict]] = {symbol: [] for symbol in SERIES}
    path = _cache_path(cache_dir)
    if not path.is_file():
        return result
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        rows = conn.execute(
            """SELECT symbol, trade_date, available_at, endpoint, payload FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY symbol, trade_date ORDER BY available_at DESC
                ) AS version
                FROM daily_versions WHERE available_at<=? AND trade_date>=?
            ) WHERE version=1 ORDER BY symbol, trade_date""",
            (cutoff, start.isoformat() if start else date.min.isoformat()),
        )
        for symbol, day, observed_at, endpoint, payload in rows:
            result[symbol].append(
                {
                    "trade_date": day,
                    "available_at": observed_at,
                    "source": "tushare",
                    "endpoint": endpoint,
                    **json.loads(payload),
                }
            )
    return result
