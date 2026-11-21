"""Capture TuShare external daily bars and replay them at a decision cutoff."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from ashare_infra.data.external_daily import SERIES
from ashare_infra.lake import DataLake
from ashare_infra.lake.r4_contract import R4_CACHE_ROOT

MARKET_ZONES = {"CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong"}
RUN_ERRORS = (ValueError, TypeError, RuntimeError, OSError, sqlite3.Error, csv.Error)
OPERATION_FIELDS = [
    "id",
    "market",
    "decision_at",
    "action",
    "symbol",
    "side",
    "shares",
    "order_id",
    "reason",
]


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an ISO date (YYYY-MM-DD)") from exc


def _instant_arg(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(
            value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
        )
        if instant.utcoffset() is not None:
            return instant
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected an ISO datetime with a UTC offset")


def _decision_snapshot(lake: DataLake, market: str, as_of: datetime, start: date | None) -> dict:
    bars = lake.load_external_daily(as_of=as_of, start=start)
    stamp = as_of.astimezone(ZoneInfo(MARKET_ZONES[market]))
    return {
        "market": market,
        "decision_at": stamp.isoformat(),
        "series": {
            symbol: {"rows": len(rows), "latest": rows[-1] if rows else None}
            for symbol, rows in bars.items()
        },
    }


def _replay_operations(lake: DataLake, path: Path, start: date | None) -> list[dict]:
    reports = []
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != OPERATION_FIELDS:
            raise ValueError(f"expected operations CSV header {','.join(OPERATION_FIELDS)}")
        for raw in reader:
            line = reader.line_num
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError(f"line {line}: wrong number of columns")
            row = {key: value.strip() for key, value in raw.items()}
            if not row["id"] or row["id"] in seen:
                raise ValueError(f"line {line}: operation ID must be nonempty and unique")
            if row["market"] not in MARKET_ZONES:
                raise ValueError(f"line {line}: market must be CN or HK")
            try:
                instant = _instant_arg(row["decision_at"])
            except argparse.ArgumentTypeError as exc:
                raise ValueError(f"line {line}: {exc}") from exc
            seen.add(row["id"])
            reports.append({**row, **_decision_snapshot(lake, row["market"], instant, start)})
    if not reports:
        raise ValueError("operations CSV has no data rows")
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=R4_CACHE_ROOT)
    subs = parser.add_subparsers(dest="command", required=True)
    capture = subs.add_parser("capture")
    capture.add_argument("--start", type=_date_arg, required=True)
    capture.add_argument("--end", type=_date_arg, required=True)
    capture.add_argument("--symbol", choices=SERIES, action="append")
    replay = subs.add_parser("replay")
    replay.add_argument("--market", choices=MARKET_ZONES, required=True)
    replay.add_argument("--as-of", type=_instant_arg, required=True)
    replay.add_argument("--start", type=_date_arg)
    operations = subs.add_parser("replay-operations", help="attach visible bars to a manual log")
    operations.add_argument("--csv", type=Path, required=True)
    operations.add_argument("--start", type=_date_arg)
    args = parser.parse_args(argv)

    lake = DataLake(cache_dir=args.cache_dir)
    if args.command == "capture":
        captured = []
        errors = {}
        with requests.Session() as session:
            for symbol in dict.fromkeys(args.symbol or SERIES):
                try:
                    captured.append(
                        lake.refresh_external_daily(symbol, args.start, args.end, session=session)
                    )
                except RUN_ERRORS as exc:
                    errors[symbol] = str(exc)
        print(json.dumps({"captured": captured, "errors": errors}, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    try:
        if args.command == "replay-operations":
            report = {"operations": _replay_operations(lake, args.csv, args.start)}
        else:
            report = _decision_snapshot(lake, args.market, args.as_of, args.start)
    except RUN_ERRORS as exc:
        print(f"external daily: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
