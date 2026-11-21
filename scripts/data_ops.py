"""Operate the local T1.AI data infrastructure from WSL."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ashare_infra import data_ops, ops_backup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "tests/fixtures/account_replay/with_context"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="operational data root")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="inventory local data without fetching")
    daily = commands.add_parser("daily", help="refresh the market caches")
    daily.add_argument("--dry-run", action="store_true", help="estimate calls without writing")
    daily.add_argument("--symbol", action="append", help="limit the A-share scope to a pool symbol")
    commands.add_parser("replay-demo", help="import and reconcile both simulated accounts")
    backup = commands.add_parser("backup", help="snapshot the operational data")
    backup.add_argument("--dest", type=Path, required=True)
    restore = commands.add_parser("restore", help="verify and restore to an isolated directory")
    restore.add_argument("--source", type=Path, required=True)
    restore.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args(argv)
    layout = data_ops.Layout(args.root.resolve())
    now = datetime.now(timezone.utc)

    try:
        if args.command == "restore":
            report = ops_backup.restore(args.source, args.dest)
        elif args.command == "status":
            report = data_ops.status(layout, now)
        elif args.command == "daily" and args.dry_run:
            report = data_ops.daily(layout, now, selected=args.symbol, dry_run=True)
        else:
            with data_ops.write_lock(layout):
                if args.command == "daily":
                    report = data_ops.daily(layout, now, selected=args.symbol)
                elif args.command == "backup":
                    report = ops_backup.backup(layout.root, args.dest, layout.backup_paths())
                else:
                    report = data_ops.replay_demo(layout, FIXTURES)
                    accounts = report["accounts"]
                    report["status"] = (
                        "pass"
                        if all(
                            item["status"] == item["attribution"] == "pass"
                            for item in accounts.values()
                        )
                        else "partial"
                    )
    except data_ops.OpsBlocked as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        return 2
    except data_ops.RUN_ERRORS as exc:
        print(f"data ops: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    if report.get("status") == "blocked":
        return 2
    return 1 if report.get("status") == "partial" else 0


if __name__ == "__main__":
    raise SystemExit(main())
