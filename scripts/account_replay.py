"""Import broker exports and replay a manually operated account."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

from ashare_infra.account_ledger import CSV_FIELDS, MARKET_CURRENCIES, import_csv
from ashare_infra.account_replay import replay_account


def _arguments(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, required=True)
    common.add_argument("--account", required=True, help="local account alias")
    ingest = commands.add_parser("import", parents=[common])
    ingest.add_argument("--kind", choices=CSV_FIELDS, required=True)
    ingest.add_argument(
        "--market", choices=MARKET_CURRENCIES, default="CN", help="CN/CNY or HK/HKD"
    )
    ingest.add_argument("--csv", type=Path, required=True)
    ingest.add_argument("--coverage-start", default="")
    ingest.add_argument("--coverage-end", default="")
    replay = commands.add_parser("replay", parents=[common])
    replay.add_argument("--opening", required=True)
    replay.add_argument("--through", required=True)
    replay.add_argument("--out-dir", type=Path, required=True)
    replay.add_argument("--prices-csv", type=Path, help="optional unadjusted closes")
    replay.add_argument("--through-batch", type=int, help="replay with a previous import cutoff")
    replay.add_argument(
        "--external-cache-dir", type=Path, help="attach observed markets and native P&L"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        if args.command == "import":
            result = import_csv(
                args.db,
                args.account,
                args.kind,
                args.csv,
                coverage_start=args.coverage_start,
                coverage_end=args.coverage_end,
                market=args.market,
            )
            print(json.dumps(result))
            return 0
        manifest = replay_account(
            args.db,
            args.account,
            args.opening,
            args.through,
            args.out_dir,
            prices_csv=args.prices_csv,
            through_batch=args.through_batch,
            external_cache_dir=args.external_cache_dir,
        )
    except (OSError, ValueError, csv.Error, sqlite3.Error) as exc:
        print(f"account replay: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "market": manifest["market"],
                "currency": manifest["currency"],
                "through_batch": manifest["through_batch"],
                "out_dir": str(args.out_dir),
            }
        )
    )
    return 0 if manifest["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
