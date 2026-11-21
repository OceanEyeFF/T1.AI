"""Validate and maintain canonical R4 market partitions through HTTPS."""

import json
import shutil
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from ashare_infra.data import tushare_source
from ashare_infra.data.tushare_batch import chunk_symbols, plan_batch
from ashare_infra.data.tushare_https import query
from ashare_infra.lake.r4_contract import R4_HISTORY_START, R4_INDEX_ANCHOR

HISTORY_START = date.fromisoformat(R4_HISTORY_START)
DATASETS = {
    "qfq": ("tushare_qfq", tushare_source.SUPPORTED_FIELDS),
    "fund_daily": ("tushare_qfq", tushare_source.SUPPORTED_FIELDS),
    "daily_basic": ("tushare_daily_basic", tushare_source.SUPPORTED_DAILY_BASIC_FIELDS),
    "moneyflow": ("tushare_moneyflow", tushare_source.SUPPORTED_MONEYFLOW_FIELDS),
}


def days(start, end):
    return (start + timedelta(days=offset) for offset in range((end - start).days + 1))


def read_calendar(path):
    if not path.is_file():
        return {}
    return {
        date.fromisoformat(day): opened
        for day, opened in json.loads(path.read_text(encoding="utf-8")).items()
    }


def calendar_start(calendar, through):
    return (
        max(HISTORY_START, min(max(calendar) + timedelta(days=1), through - timedelta(days=9)))
        if calendar
        else HISTORY_START
    )


def _table(data, columns):
    fields, items = data.get("fields"), data.get("items")
    if (
        not isinstance(fields, list)
        or not all(isinstance(field, str) for field in fields)
        or len(set(fields)) != len(fields)
        or not isinstance(items, list)
        or any(not isinstance(row, list) or len(row) != len(fields) for row in items)
    ):
        raise ValueError("malformed TuShare table")
    if not items:
        return pd.DataFrame(columns=columns)
    if not set(columns).issubset(fields):
        raise ValueError("TuShare table is missing required columns")
    return pd.DataFrame(items, columns=fields)


def refresh_calendar(through, calendar, token, session):
    start = calendar_start(calendar, through)
    data = query(
        "trade_cal",
        {
            "exchange": "SSE",
            "start_date": start.strftime("%Y%m%d"),
            "end_date": through.strftime("%Y%m%d"),
        },
        token,
        fields="exchange,cal_date,is_open",
        session=session,
    )
    rows = _table(data, ("exchange", "cal_date", "is_open"))
    parsed = _dates(rows["cal_date"])
    expected = set(days(start, through))
    if (
        set(parsed) != expected
        or parsed.has_duplicates
        or not rows["exchange"].eq("SSE").all()
        or not rows["is_open"].astype(str).isin(("0", "1")).all()
    ):
        raise ValueError("TuShare SSE calendar did not cover every requested day")
    return {**calendar, **dict(zip(parsed, rows["is_open"].astype(str).eq("1"), strict=True))}


def _dates(values):
    return pd.Index(pd.to_datetime(values.astype(str), format="%Y%m%d", errors="raise").dt.date)


def _directory(cache, api, symbol):
    return cache / DATASETS[api][0] / symbol


def _prior_generation(directory):
    return directory.with_name(f".{directory.name}.previous")


def recover_qfq(cache):
    """Recover a generation interrupted between the two directory renames."""
    for previous in (cache / DATASETS["qfq"][0]).glob(".*.previous"):
        if not previous.is_dir():
            continue
        directory = previous.with_name(previous.name[1:].removesuffix(".previous"))
        if not directory.exists():
            previous.rename(directory)


def _read_symbol(directory, *, dates_only=False):
    if not directory.exists():
        directory = _prior_generation(directory)
    parts = []
    for path in sorted(directory.glob("year=*/part.parquet")):
        frame = pd.read_parquet(path, columns=["date"] if dates_only else None)
        stamp = pd.DatetimeIndex(pd.to_datetime(frame.pop("date"), errors="raise"), name="date")
        if stamp.hasnans or any(stamp.year != int(path.parent.name.removeprefix("year="))):
            raise ValueError(f"invalid dates in {path.parent.name}/part.parquet")
        parts.append(frame.set_index(stamp))
    if not parts:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="date"))
    result = pd.concat(parts).sort_index()
    if result.index.has_duplicates:
        raise ValueError("duplicate dates in canonical partitions")
    return result


def _publish_qfq(frame, directory):
    """Stage every year before switching a symbol to the new adjustment basis."""
    parent, previous = directory.parent, _prior_generation(directory)
    parent.mkdir(parents=True, exist_ok=True)
    if previous.exists():
        if directory.exists():
            shutil.rmtree(previous)
        else:
            previous.rename(directory)
    with TemporaryDirectory(prefix=f".{directory.name}-", dir=parent) as temp:
        staged = Path(temp) / directory.name
        tushare_source._write_partitioned(frame, staged)
        if directory.exists():
            directory.rename(previous)
        try:
            staged.rename(directory)
        except OSError:
            if previous.exists():
                previous.rename(directory)
            raise
        if previous.exists():
            shutil.rmtree(previous)


def inventory(cache, symbols):
    result = {}
    for api, symbol_list in (
        ("qfq", symbols),
        ("daily_basic", symbols),
        ("moneyflow", symbols),
        ("fund_daily", [R4_INDEX_ANCHOR]),
    ):
        for symbol in symbol_list:
            try:
                dates = _read_symbol(_directory(cache, api, symbol), dates_only=True).index.date
                result[api, symbol] = (set(dates), None)
            except (OSError, ValueError, KeyError) as exc:
                result[api, symbol] = (set(), str(exc))
    return result


def coverage(inventory_by_job, calendar, through, suspensions=None):
    opened = {day for day, is_open in calendar.items() if is_open and day <= through}
    latest = max(opened, default=None)
    for (api, symbol), (dates, error) in inventory_by_job.items():
        applicable = opened
        if api in ("daily_basic", "moneyflow"):
            applicable = opened & inventory_by_job["qfq", symbol][0]
        absent = applicable - dates
        suspended = (
            absent & {date.fromisoformat(day) for day in (suspensions or {}).get(symbol, ())}
            if api == "qfq"
            else set()
        )
        missing = sorted(absent - suspended)
        yield {
            "api": api,
            "symbol": symbol,
            "first": min(dates, default=None),
            "latest": max(dates, default=None),
            "rows": len(dates),
            "expected_latest": latest,
            "missing_dates": missing,
            "suspended_dates": sorted(suspended),
            "error": error,
            "status": (
                "error"
                if error
                else "missing"
                if not dates
                else "unverified"
                if not calendar
                else "gap"
                if missing
                else "ok"
            ),
        }


def batches(inventory_by_job, calendar, through, checked, policy, suspensions=None):
    grouped = defaultdict(list)
    opened = {day for day, is_open in calendar.items() if is_open and day <= through}
    for row in coverage(inventory_by_job, calendar, through, suspensions):
        api, symbol = row["api"], row["symbol"]
        days_to_check = set(row["missing_dates"])
        if api in ("daily_basic", "moneyflow") and not row["error"]:
            # Include trailing open days even when a new qfq partition is scheduled in this run.
            latest = row["latest"] or HISTORY_START - timedelta(days=1)
            days_to_check.update(day for day in opened if day > latest)
        last_check = checked.get(f"{api}:{symbol}")
        if last_check:
            days_to_check.difference_update(date.fromisoformat(day) for day in last_check)
        if days_to_check:
            dates = inventory_by_job[api, symbol][0]
            if max(dates, default=through) > through:
                raise ValueError(f"{api}:{symbol} has dates beyond the requested cutoff")
            start = min(days_to_check)
            if api == "qfq":
                start = min(start, min(dates, default=start))
            grouped[api, start].append(symbol)
    for (api, start), symbols in grouped.items():
        for chunk in chunk_symbols(symbols, max_batch_symbols=policy.max_batch_symbols):
            yield plan_batch(
                chunk,
                apis=(api,),
                start_date=start.strftime("%Y%m%d"),
                end_date=through.strftime("%Y%m%d"),
                policy=policy,
            )


def _fetch(endpoint, symbol, start, end, token, session, fields):
    data = query(
        endpoint,
        {"ts_code": symbol, "start_date": start, "end_date": end},
        token,
        fields=",".join(("ts_code", "trade_date", *fields)),
        session=session,
    )
    rows = _table(data, ("ts_code", "trade_date", *fields))
    parsed = _dates(rows["trade_date"])
    first, last = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    if (
        parsed.has_duplicates
        or not rows["ts_code"].eq(symbol).all()
        or any(not first <= day <= last for day in parsed)
    ):
        raise ValueError(f"{endpoint} returned unexpected symbol or dates")
    return rows


def suspended_dates(symbol, missing, token, session):
    fields = ("ts_code", "trade_date", "suspend_type", "suspend_timing")
    raw = query(
        "suspend_d",
        {
            "ts_code": symbol,
            "start_date": min(missing).strftime("%Y%m%d"),
            "end_date": max(missing).strftime("%Y%m%d"),
            "suspend_type": "S",
        },
        token,
        fields=",".join(fields),
        session=session,
    )
    rows = _table(raw, fields)
    full_day = (
        rows["ts_code"].eq(symbol)
        & rows["suspend_type"].eq("S")
        & rows["suspend_timing"].fillna("").eq("")
    )
    return set(_dates(rows.loc[full_day, "trade_date"])) & set(missing)


def capture_execution_bars(cache, symbol, start, end, token, session, expected_sessions):
    """Cache raw OHLCV plus the provider's previous close for opening-price replay."""
    fields = ("open", "high", "low", "close", "pre_close", "vol", "amount")
    raw = _fetch(
        "daily", symbol, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), token, session, fields
    )
    bars = tushare_source._normalize_tushare_daily(raw)
    if bars.empty or not bars.index.equals(expected_sessions):
        raise ValueError(f"{symbol}: raw prices did not match the expected trading dates")
    raw.index = pd.to_datetime(raw["trade_date"], format="%Y%m%d")
    bars["pre_close"] = pd.to_numeric(raw["pre_close"], errors="raise")
    if (
        not np.isfinite(bars.to_numpy()).all()
        or not (bars[["open", "close", "pre_close"]] > 0).all().all()
    ):
        raise ValueError(f"{symbol}: invalid raw execution prices")
    directory = cache / "tushare" / symbol
    previous = _read_symbol(directory)
    if not previous.empty:
        bars = pd.concat((previous.loc[~previous.index.isin(bars.index)], bars)).sort_index()
    tushare_source._write_partitioned(bars, directory)


def _bars(endpoint, job, token, session, open_days):
    args = (job.symbol, job.start_date, job.end_date, token, session)
    stock_fields = ("open", "high", "low", "close", "vol", "amount")
    daily = tushare_source._normalize_tushare_daily(_fetch(endpoint, *args, stock_fields))
    if daily.empty:
        return daily
    if (
        not np.isfinite(daily.to_numpy()).all()
        or (daily[["open", "high", "low", "close"]] <= 0).any().any()
        or not set(daily.index.date) <= open_days
    ):
        raise ValueError("invalid OHLCV or non-trading date")
    if endpoint == "fund_daily":
        return daily
    factors = tushare_source._normalize_tushare_adj_factor(
        _fetch("adj_factor", *args, ("adj_factor",))
    )
    factor = (
        factors["adj_factor"].reindex(daily.index)
        if not factors.empty
        else pd.Series(np.nan, index=daily.index)
    )
    if not np.isfinite(factor).all() or not (factor > 0).all():
        raise ValueError("missing or invalid adjustment factor on a trading date")
    return tushare_source._apply_price_adjustment(daily, factors, "qfq")


def refresh_symbol(cache, job, token, session, open_days):
    directory = _directory(cache, job.api, job.symbol)
    previous = _read_symbol(directory)
    known = set(previous.index.date)
    start, end = pd.Timestamp(job.start_date).date(), pd.Timestamp(job.end_date).date()
    requested = {day for day in open_days if start <= day <= end}
    if job.api in ("qfq", "fund_daily"):
        endpoint = "daily" if job.api == "qfq" else job.api
        # Earlier cached history shares the same adjustment basis but predates the R4 calendar.
        legacy_dates = {day for day in known if day < HISTORY_START}
        fresh = _bars(endpoint, job, token, session, open_days | legacy_dates)
        got = set(fresh.index.date) if not fresh.empty else set()
        if not (known & requested) <= got:
            raise ValueError("provider omitted previously cached trading dates; retained cache")
        if job.api == "qfq" and not known <= got:
            raise ValueError(
                "qfq refresh does not cover the existing adjustment span; retained cache"
            )
        if job.api == "fund_daily" and requested - got:
            raise ValueError("ETF anchor is missing requested trading dates; retained cache")
        missing = requested - got
    else:
        fields = DATASETS[job.api][1]
        raw = _fetch(job.api, job.symbol, job.start_date, job.end_date, token, session, fields)
        fresh = tushare_source._normalize_tushare_table(raw, fields)
        got = set(fresh.index.date) if not fresh.empty else set()
        if not got <= open_days or not (known & requested) <= got:
            raise ValueError("provider returned invalid coverage; retained cache")
        if not fresh.empty and not np.isfinite(fresh.to_numpy()).any(axis=1).all():
            raise ValueError("provider returned a row with no finite values; retained cache")
        stock_dates = _read_symbol(_directory(cache, "qfq", job.symbol), dates_only=True)
        missing = (requested & set(stock_dates.index.date)) - got
    if not fresh.empty and (job.api != "qfq" or not missing or got - known):
        combined = (
            fresh
            if job.api == "qfq"
            else (pd.concat([previous, fresh]) if not previous.empty else fresh)
        )
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        if job.api == "qfq":
            _publish_qfq(combined, directory)
        else:
            tushare_source._write_partitioned(combined, directory)
    elif not known:
        raise ValueError("provider returned no data for an uncached symbol")
    return {"rows": len(fresh), "missing_dates": sorted(missing)}
