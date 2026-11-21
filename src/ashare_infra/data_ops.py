"""Local operations for market data, account replay and research artifacts."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
from collections import Counter
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from zoneinfo import ZoneInfo

import requests

from ashare_infra import ops_backup
from ashare_infra.account_ledger import MARKET_CURRENCIES, import_csv
from ashare_infra.account_replay import replay_account
from ashare_infra.data import managed_daily
from ashare_infra.data.external_daily import SERIES
from ashare_infra.data.tushare_batch import (
    R4BatchPolicy,
    expand_job_api_calls,
    is_frequency_wall_error,
    run_batch,
)
from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimitExceeded,
    get_tushare_rate_limiter,
)
from ashare_infra.lake.r4_contract import (
    R4_CACHE_ROOT,
    R4_POOL_REGISTRY,
    R4_RATE_LIMITS_CONFIG,
    filter_r4_trial_symbols,
    make_r4_datalake,
)

try:
    import tomllib
except ImportError:  # pragma: no cover - deployment uses 3.11
    import tomli as tomllib

SHANGHAI = ZoneInfo("Asia/Shanghai")
GIB = 1024**3
RUN_ERRORS = (OSError, ValueError, TypeError, KeyError, RuntimeError, sqlite3.Error, csv.Error)
REGISTRY = Path("workspace/registry/certified.json")
FEATURE = Path("inputs/configs/features/mainline_11d_v1.toml")
DATASETS = Path("workspace/datasets")
REPORTS = Path("outputs/reports/account_replay")
PRIVATE_ACCOUNTS = Path("inputs/data/private/broker")
ACCOUNT_RUNS = Path("workspace/runs/account_replay")
DEMO_OPENING, DEMO_THROUGH = "2026-11-20", "2026-11-26"


class OpsBlocked(RuntimeError):
    """An environmental prerequisite prevents a managed write."""


@dataclass(frozen=True)
class Layout:
    root: Path

    @property
    def cache(self):
        return self.root / R4_CACHE_ROOT

    @property
    def runs(self):
        return self.root / "workspace/runs/data_ops"

    @property
    def calendar(self):
        return self.cache / "tushare_calendar" / "sse.json"

    @property
    def suspensions(self):
        return self.cache / "tushare_calendar" / "suspensions.json"

    def accounts(self):
        account_dir = self.root / ACCOUNT_RUNS
        return {
            db.parent.name: db
            for db in sorted(account_dir.glob("*/ledger.sqlite"))
            if not db.parent.name.startswith(".")
        }

    def backup_paths(self):
        private = [self.root / PRIVATE_ACCOUNTS / alias for alias in self.accounts()]
        return [
            self.cache,
            self.runs,
            *self.accounts().values(),
            *private,
            self.root / REGISTRY,
            self.root / FEATURE,
            self.root / R4_POOL_REGISTRY,
            self.root / R4_RATE_LIMITS_CONFIG,
            *(self.root / DATASETS).rglob("metadata.json"),
            *(
                manifest
                for alias in self.accounts()
                for manifest in (self.root / REPORTS / alias).rglob("manifest.json")
            ),
        ]


def json_file(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
    ) as stream:
        temp = Path(stream.name)
        try:
            json.dump(payload, stream, ensure_ascii=False, indent=2, default=str)
            stream.write("\n")
            stream.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


@contextmanager
def write_lock(layout):
    import fcntl

    layout.runs.mkdir(parents=True, exist_ok=True)
    with (layout.runs / ".lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise OpsBlocked("another data operations command holds the write lock") from exc
        managed_daily.recover_qfq(layout.cache)
        yield


def disk_status(root):
    free = shutil.disk_usage(root).free
    return {
        "free_bytes": free,
        "status": "blocked" if free < 2 * GIB else "warning" if free < 3 * GIB else "ok",
    }


def _require_space(layout):
    if disk_status(layout.root)["status"] == "blocked":
        raise OpsBlocked("repository volume has less than 2 GiB free")


def _token(root):
    value = os.environ.get("TUSHARE_TOKEN", "").strip()
    dotenv = root / ".env"
    if not value and dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8-sig").splitlines():
            if match := re.fullmatch(
                r"""\s*(?:export\s+)?TUSHARE_TOKEN\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s#]+))\s*(?:#.*)?""",
                line,
            ):
                value = next(part for part in match.groups() if part is not None)
    if not value or value == "your_tushare_token_here":
        raise OpsBlocked("configure TUSHARE_TOKEN in the environment or private .env")
    return value


def _symbols(layout, selected):
    with (layout.root / R4_POOL_REGISTRY / "symbols.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        pool = filter_r4_trial_symbols([row["symbol"].strip() for row in csv.DictReader(stream)])
    qualified = tuple(
        symbol if "." in symbol else f"{symbol}.{'SH' if symbol.startswith('6') else 'SZ'}"
        for symbol in pool
    )
    if selected:
        if absent := set(selected) - set(qualified):
            raise ValueError(f"symbols outside the maintained R4 pool: {', '.join(sorted(absent))}")
        return [symbol for symbol in qualified if symbol in selected]
    return qualified


def _account_status(layout):
    result = {}
    reports = layout.root / REPORTS
    for alias, path in layout.accounts().items():
        try:
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
                has_profiles = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_profiles'"
                ).fetchone()
                profile = (
                    db.execute(
                        "SELECT market FROM account_profiles WHERE account=?", (alias,)
                    ).fetchone()
                    if has_profiles
                    else None
                )
                count, batch = db.execute(
                    "SELECT count(*), max(id) FROM batches WHERE account=?", (alias,)
                ).fetchone()
                opening, statement = (
                    db.execute(
                        "SELECT max(key) FROM records WHERE account=? AND kind=?", (alias, kind)
                    ).fetchone()[0]
                    for kind in ("opening", "statement")
                )
            if not count:
                continue
            market = profile[0] if profile else "CN"
            manifests = [
                report
                for file in sorted((reports / alias).rglob("manifest.json"))
                if (report := json_file(file)) and report.get("account") == alias
            ]
            latest = max(
                manifests,
                key=lambda item: (item.get("through_batch", 0), item.get("through", "")),
                default={},
            )
            reconciliation = (
                latest["status"]
                if latest.get("through_batch") == batch
                else "stale"
                if latest
                else "unverified"
            )
            result[alias] = {
                "market": market,
                "currency": MARKET_CURRENCIES[market],
                "batch_count": count,
                "latest_batch": batch,
                "opening": opening,
                "statement": statement,
                "reconciliation": reconciliation,
                "reconciled_through": latest.get("through"),
            }
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            result[alias] = {"reconciliation": "error", "error": str(exc)}
    return result


def _research_status(layout):
    metadata = layout.root / DATASETS
    datasets = {}
    for path in sorted(metadata.rglob("metadata.json")):
        try:
            data = json_file(path)
            datasets[str(path.parent.relative_to(metadata))] = {
                key: data[key]
                for key in (
                    "dataset_id",
                    "dataset_type",
                    "feature_contract_id",
                    "feature_contract_hash",
                    "feature_contract_version",
                )
                if key in data
            } | {"metadata_sha256": ops_backup.digest(path)}
        except (OSError, ValueError, TypeError) as exc:
            datasets[str(path.parent.relative_to(metadata))] = {"error": str(exc)}
    feature = layout.root / FEATURE
    contract = (
        tomllib.loads(feature.read_text(encoding="utf-8"))["contract"] if feature.is_file() else {}
    )
    certified = json_file(layout.root / REGISTRY, {})
    return {
        "feature_contract": contract,
        "certification": certified.get("status", "missing"),
        "certified_pairs": sorted(certified.get("pairs", {})),
        "datasets": datasets,
    }


def _external_status(lake, now):
    result = {}
    for symbol, rows in lake.load_external_daily(as_of=now).items():
        last = rows[-1] if rows else {}
        day, observed = last.get("trade_date"), last.get("available_at")
        today = now.astimezone(ZoneInfo(SERIES[symbol][1])).date()
        result[symbol] = {
            "rows": len(rows),
            "latest": day,
            "available_at": observed,
            "status": "missing"
            if not day
            else "stale"
            if (today - date.fromisoformat(day)).days > 10
            else "ok",
        }
    return result


def status(layout, now):
    symbols = _symbols(layout, None)
    through = now.astimezone(SHANGHAI).date() - timedelta(days=1)
    calendar = managed_daily.read_calendar(layout.calendar)
    inventory = managed_daily.inventory(layout.cache, symbols)
    latest = json_file(layout.runs / "latest.json", {})
    return {
        "as_of": now.isoformat(),
        "disk": disk_status(layout.root),
        "calendar": {
            "through": max(calendar, default=None),
            "target": through,
            "status": "ok" if through in calendar else "unverified",
        },
        "ashare": list(
            managed_daily.coverage(inventory, calendar, through, json_file(layout.suspensions, {}))
        ),
        "external": _external_status(make_r4_datalake(layout.cache), now),
        "accounts": _account_status(layout),
        "research": _research_status(layout),
        "latest_run": (
            {key: latest.get(key) for key in ("id", "status", "through", "scope")}
            | {"manifest": str(layout.runs / latest["id"] / "manifest.json")}
            if latest
            else None
        ),
    }


def _provider_budget(manifests, external_count, calendar_calls):
    calls = Counter({"trade_cal": calendar_calls})
    for manifest in manifests:
        for job in manifest.jobs:
            calls.update(expand_job_api_calls(job))
    if external_count:
        calls.update(endpoint for endpoint, _ in SERIES.values())
    limiter = get_tushare_rate_limiter()
    remaining = {api: limiter.remaining_daily(api) for api in calls}
    return {
        "estimated_calls": dict(calls),
        "remaining": remaining,
        "blocking_apis": sorted(api for api in calls if calls[api] > remaining[api]),
    }


def daily(layout, now, *, selected=None, dry_run=False):
    through = now.astimezone(SHANGHAI).date() - timedelta(days=1)
    policy = R4BatchPolicy.from_r4_config(layout.root / R4_RATE_LIMITS_CONFIG)
    symbols = _symbols(layout, selected)
    checked_path = layout.runs / "checked_gaps.json"
    checked = json_file(checked_path, {})
    stored = managed_daily.read_calendar(layout.calendar)
    suspensions = json_file(layout.suspensions, {})
    start = managed_daily.calendar_start(stored, through)
    inventory = managed_daily.inventory(layout.cache, symbols)
    disk = disk_status(layout.root)
    external_from = through - timedelta(days=9)
    report = {
        "through": through,
        "calendar_from": start,
        "external_from": external_from,
        "disk": disk,
        "symbols": len(symbols),
        "scope": "canary" if selected else "full",
    }
    if dry_run:
        estimated = {
            day: stored.get(day, day.weekday() < 5)
            for day in managed_daily.days(managed_daily.HISTORY_START, through)
        }
        manifests = list(
            managed_daily.batches(inventory, estimated, through, checked, policy, suspensions)
        )
        return report | {
            "status": "dry_run",
            "calendar_estimated": through not in stored,
            "cn_jobs": [job.to_dict() for manifest in manifests for job in manifest.jobs],
            "budget": _provider_budget(manifests, len(SERIES), 1),
            "suspension_calls_max": len(symbols),
        }
    job_dir = Path(mkdtemp(prefix=now.strftime("%Y%m%dT%H%M%S-"), dir=layout.runs))
    report |= {
        "id": job_dir.name,
        "manifest": str(job_dir / "manifest.json"),
        "started_at": now.isoformat(),
        "status": "running",
        "cn": {},
        "external": {},
        "errors": {},
        "resume": [],
    }

    def save():
        write_json(job_dir / "manifest.json", report)
        write_json(layout.runs / "latest.json", report)

    save()
    try:
        _require_space(layout)
        token = _token(layout.root)
    except OpsBlocked as exc:
        report["errors"]["preflight"] = str(exc)
        report["status"] = "blocked"
        save()
        return report
    with requests.Session() as session:
        try:
            calendar = managed_daily.refresh_calendar(through, stored, token, session)
            write_json(
                layout.calendar, {day.isoformat(): opened for day, opened in calendar.items()}
            )
            report["calendar"] = "ok"
        except RUN_ERRORS as exc:
            report["errors"]["trade_cal"] = str(exc)
            calendar = stored

        if through in calendar:
            manifests = list(
                managed_daily.batches(inventory, calendar, through, checked, policy, suspensions)
            )
            report["budget"] = _provider_budget(manifests, len(SERIES), 0)
            report["plan"] = [job.job_id for manifest in manifests for job in manifest.jobs]
            report["resume"] = report["plan"].copy()
            opened = {day for day, is_open in calendar.items() if is_open}
            recent = set(sorted(opened)[-3:])

            def execute(job):
                _require_space(layout)
                result = managed_daily.refresh_symbol(layout.cache, job, token, session, opened)
                key = f"{job.api}:{job.symbol}"
                checked[key] = sorted(
                    set(checked.get(key, ()))
                    | {day.isoformat() for day in result["missing_dates"] if day not in recent}
                )
                write_json(checked_path, checked)
                report["cn"][job.job_id] = result
                report["resume"].remove(job.job_id)
                save()

            save()
            for index, manifest in enumerate(manifests, 1):
                batch_path = job_dir / f"batch-{index}.json"
                while manifest.pending_jobs():
                    result = run_batch(manifest, execute, manifest_path=batch_path)
                    if result.paused:
                        report["errors"]["cn_batch"] = manifest.pause_reason
                        save()
                        break
                    failed = [job for job in manifest.jobs if job.status == "failed"]
                    for job in failed:
                        report["errors"][job.job_id] = job.error
                    save()
                    if any("less than 2 GiB" in (job.error or "") for job in failed):
                        break
                if result.paused or disk_status(layout.root)["status"] == "blocked":
                    break
        else:
            report["errors"]["cn_calendar"] = "trading calendar does not cover the target date"
            report["resume"].append("trade_cal")

        inventory = managed_daily.inventory(layout.cache, symbols)
        if not report["errors"].get("cn_batch") and through in calendar:
            for row in managed_daily.coverage(inventory, calendar, through, suspensions):
                if row["api"] != "qfq" or not row["rows"] or not row["missing_dates"]:
                    continue
                try:
                    _require_space(layout)
                    symbol = row["symbol"]
                    confirmed = managed_daily.suspended_dates(
                        symbol, row["missing_dates"], token, session
                    )
                    if confirmed:
                        suspensions[symbol] = sorted(
                            set(suspensions.get(symbol, ()))
                            | {day.isoformat() for day in confirmed}
                        )
                        write_json(layout.suspensions, suspensions)
                except RUN_ERRORS as exc:
                    report["errors"]["suspend_d"] = str(exc)
                    report["resume"].append(f"suspend_d:{row['symbol']}")
                    break

        lake = make_r4_datalake(layout.cache, tushare_token=token)
        report["resume"].extend(SERIES)
        save()
        for symbol in SERIES:
            try:
                _require_space(layout)
                report["external"][symbol] = lake.refresh_external_daily(
                    symbol, external_from, through, session=session
                )
                report["resume"].remove(symbol)
            except RUN_ERRORS as exc:
                report["errors"][symbol] = str(exc)
                if isinstance(
                    exc, (OpsBlocked, TushareRateLimitExceeded)
                ) or is_frequency_wall_error(exc):
                    break
            finally:
                save()
        finished = datetime.now(timezone.utc)
        # Include every version observed in this run even if the host clock stepped back.
        observed = [
            datetime.fromisoformat(item["available_at"])
            for item in report["external"].values()
            if item.get("available_at")
        ]
        report["external_state"] = _external_status(lake, max(now, finished, *observed))
        report["cn_coverage"] = [
            row
            for row in managed_daily.coverage(inventory, calendar, through, suspensions)
            if row["error"] or row["missing_dates"] or row["suspended_dates"]
        ]
    disk = disk_status(layout.root)
    report["disk"] = disk
    report["finished_at"] = finished.isoformat()
    report["status"] = (
        "blocked"
        if disk["status"] == "blocked"
        else (
            "partial"
            if report["errors"]
            or any(item["status"] != "ok" for item in report["cn_coverage"])
            or any(item["status"] != "ok" for item in report["external_state"].values())
            else "pass"
        )
    )
    save()
    return report


def replay_demo(layout, fixtures):
    _require_space(layout)
    result = {}
    for market in MARKET_CURRENCIES:
        alias = f"demo-{market.lower()}"
        file_dir = fixtures / market.lower()
        private = layout.root / PRIVATE_ACCOUNTS / alias
        private.mkdir(parents=True, exist_ok=True)
        for source in file_dir.glob("*.csv"):
            target = private / source.name
            if target.exists() and ops_backup.digest(target) != ops_backup.digest(source):
                raise ValueError(f"demo input differs from the original sample: {target.name}")
            if not target.exists():
                shutil.copyfile(source, target)
        ledger = layout.root / ACCOUNT_RUNS / alias / "ledger.sqlite"
        imports = {}
        for kind in ("opening", "events", "operations", "statement"):
            coverage = {"coverage_start": "2026-11-21", "coverage_end": DEMO_THROUGH}
            common = (ledger, alias, kind, private / f"{kind}.csv")
            options = {"market": market} | (coverage if kind == "events" else {})
            first = import_csv(*common, **options)
            second = import_csv(*common, **options)
            if second["inserted"] or first["batch_id"] != second["batch_id"]:
                raise ValueError(f"duplicate import changed a demo batch: {alias}/{kind}")
            imports[kind] = second
        reports = layout.root / REPORTS / alias
        reports.mkdir(parents=True, exist_ok=True)
        # Replay publishes to a newly named directory, preserving previous evidence.
        run = mkdtemp(prefix="run-", dir=reports)
        output = Path(run) / "replay"
        manifest = replay_account(
            ledger,
            alias,
            DEMO_OPENING,
            DEMO_THROUGH,
            output,
            prices_csv=private / "prices.csv",
            external_cache_dir=layout.cache,
        )
        with (output / "sales_pnl.csv").open(encoding="utf-8", newline="") as stream:
            sales = list(csv.DictReader(stream))
        result[market] = {
            "currency": manifest["currency"],
            "status": manifest["status"],
            "attribution": manifest["attribution_status"],
            "final_pnl_cents": manifest["pnl_since_open_cents"],
            "sales_net_cents": [int(row["realized_net_cents"]) for row in sales],
            "imports_repeated": imports,
            "reports": str(output),
            "price_source": "synthetic",
        }
    return {"accounts": result}
