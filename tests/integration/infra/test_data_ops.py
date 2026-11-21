import json
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from ashare_infra import data_ops, ops_backup
from ashare_infra.data import managed_daily
from ashare_infra.data.tushare_batch import FetchJob
from ashare_infra.lake.r4_contract import R4_POOL_REGISTRY
from scripts.data_ops import FIXTURES, main


def _provider_table(fields, rows):
    return {"fields": fields, "items": rows}


def _layout(root):
    pool = root / R4_POOL_REGISTRY / "symbols.csv"
    pool.parent.mkdir(parents=True)
    pool.write_text("symbol\n600519\n", encoding="utf-8")
    return data_ops.Layout(root)


def test_qfq_rejects_incomplete_response_and_publishes_consistent_history(tmp_path, monkeypatch):
    target = tmp_path / "tushare_qfq/600519.SH"
    old = pd.DataFrame(
        {"close": [8.0, 10.0]}, index=pd.DatetimeIndex(["2025-12-31", "2026-01-05"], name="date")
    )
    managed_daily.tushare_source._write_partitioned(old, target)
    before = {part.name + part.parent.name: part.read_bytes() for part in target.rglob("*.parquet")}
    session_days = [date(2025, 12, 31), date(2026, 1, 5), date(2026, 1, 6)]
    dates = [day.strftime("%Y%m%d") for day in session_days]
    omit = {"daily": dates[0], "adj_factor": None}

    def provider(endpoint, _params, _token, *, fields, **kwargs):
        values = (
            [[day, factor] for day, factor in zip(dates, [1.0, 1.0, 2.0], strict=True)]
            if endpoint == "adj_factor"
            else [[day, 10, 11, 9, 10, 1000, 10000] for day in dates]
        )
        return _provider_table(
            fields.split(","), [["600519.SH", *row] for row in values if row[0] != omit[endpoint]]
        )

    monkeypatch.setattr(managed_daily, "query", provider)
    job = FetchJob("sample", "qfq", "600519.SH", dates[0], dates[-1])
    with pytest.raises(ValueError, match="omitted previously cached"):
        managed_daily.refresh_symbol(tmp_path, job, "fixture", None, set(session_days))
    omit.update(daily=None, adj_factor=dates[1])
    with pytest.raises(ValueError, match="adjustment factor"):
        managed_daily.refresh_symbol(tmp_path, job, "fixture", None, set(session_days))
    assert {
        part.name + part.parent.name: part.read_bytes() for part in target.rglob("*.parquet")
    } == before
    omit["adj_factor"] = None
    monkeypatch.setattr(managed_daily, "HISTORY_START", date(2026, 1, 1))
    assert managed_daily.refresh_symbol(tmp_path, job, "fixture", None, set(session_days[1:])) == {
        "rows": 3,
        "missing_dates": [],
    }
    assert managed_daily._read_symbol(target)["close"].tolist() == [5.0, 5.0, 10.0]


def test_daily_dry_run_pauses_and_resumes_without_refetching_done_jobs(tmp_path, monkeypatch):
    layout = _layout(tmp_path)
    monkeypatch.setattr(managed_daily, "HISTORY_START", date(2026, 11, 20))
    now = datetime(2026, 11, 22, 6, tzinfo=timezone.utc)
    monkeypatch.setenv("TUSHARE_TOKEN", "fixture")
    dry_run = data_ops.daily(layout, now, dry_run=True)
    assert dry_run["calendar_estimated"]
    assert dry_run["budget"]["estimated_calls"]["daily"] == 1
    assert not layout.cache.exists() and not layout.runs.exists()

    def refresh_calendar(_through, _stored, _token, _session):
        return {date(2026, 11, 20): True, date(2026, 11, 21): False}

    calls = []
    blocked = True

    def refresh_symbol(cache, job, _token, _session, opened):
        calls.append(job.api)
        assert opened == {date(2026, 11, 20)}
        if blocked and job.api == "daily_basic":
            raise RuntimeError("provider 2002")
        path = cache / managed_daily.DATASETS[job.api][0] / job.symbol / "year=2026"
        path.mkdir(parents=True)
        pd.DataFrame({"date": pd.to_datetime(["2026-11-20"])}).to_parquet(path / "part.parquet")
        return {"rows": 1, "missing_dates": []}

    class External:
        def refresh_external_daily(self, symbol, start, end, *, session):
            return {}

    monkeypatch.setattr(managed_daily, "refresh_calendar", refresh_calendar)
    monkeypatch.setattr(managed_daily, "refresh_symbol", refresh_symbol)
    monkeypatch.setattr(data_ops, "make_r4_datalake", lambda *args, **kwargs: External())
    monkeypatch.setattr(data_ops, "_external_status", lambda *_: {})

    def run():
        with data_ops.write_lock(layout):
            return data_ops.daily(layout, now)

    first = run()
    assert first["status"] == "partial"
    assert calls == ["qfq", "daily_basic"]
    assert Path(first["manifest"]).is_file()
    assert any(item.startswith("daily_basic:") for item in first["resume"])
    blocked = False
    calls.clear()
    assert run()["status"] == "pass"
    assert calls == ["daily_basic", "moneyflow", "fund_daily"]


def test_only_full_day_suspensions_explain_missing_trading_dates(monkeypatch):
    symbol = "600519.SH"
    days = [date(2026, 11, day) for day in (16, 17, 18)]

    def provider(endpoint, params, _token, *, fields, **_kwargs):
        assert endpoint == "suspend_d" and params["ts_code"] == symbol
        return _provider_table(
            fields.split(","),
            [
                [symbol, "20261116", "S", None],
                [symbol, "20261117", "S", "09:30-10:00"],
                [symbol, "20261118", "R", None],
            ],
        )

    monkeypatch.setattr(managed_daily, "query", provider)
    confirmed = managed_daily.suspended_dates(symbol, days, "fixture", None)
    assert confirmed == {days[0]}
    (row,) = managed_daily.coverage(
        {("qfq", symbol): ({date(2026, 11, 13)}, None)},
        dict.fromkeys(days, True),
        days[-1],
        {symbol: [day.isoformat() for day in confirmed]},
    )
    assert row["suspended_dates"] == days[:1]
    assert row["missing_dates"] == days[1:]
    assert row["status"] == "gap"


def test_private_backup_restores_both_accounts_and_rejects_tampering(tmp_path):
    layout = _layout(tmp_path / "source")
    for market in ("cn", "hk"):
        ledger = layout.root / data_ops.ACCOUNT_RUNS / f"demo-{market}" / "ledger.sqlite"
        assert not ledger.exists()
    assert main(["--root", str(layout.root), "replay-demo"]) == 0
    before = data_ops._account_status(layout)
    assert [item["reconciliation"] for item in before.values()] == ["pass", "pass"]
    (layout.root / ".env").write_text("TUSHARE_TOKEN=fixture", encoding="utf-8")
    source = tmp_path / "backup"
    restored = tmp_path / "restored"
    with data_ops.write_lock(layout):
        ops_backup.backup(layout.root, source, layout.backup_paths())
    assert not (source / ".env").exists()
    ops_backup.restore(source, restored)
    assert main(["--root", str(restored), "replay-demo"]) == 0
    assert data_ops._account_status(data_ops.Layout(restored)) == before
    for market in ("cn", "hk"):
        assert (restored / data_ops.PRIVATE_ACCOUNTS / f"demo-{market}" / "prices.csv").is_file()
    manifest = json.loads((source / ops_backup.MANIFEST).read_text(encoding="utf-8"))
    member = source / manifest["files"][0]["path"]
    member.write_bytes(b"modified")
    with pytest.raises(ValueError, match="checksum mismatch"):
        ops_backup.restore(source, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_backup_reads_the_committed_wal_and_restores_into_an_empty_directory(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    target = tmp_path / "restored"
    target.mkdir()
    ledger = root / "ledger.sqlite"
    with closing(sqlite3.connect(ledger)) as write:
        write.execute("PRAGMA journal_mode=WAL")
        write.execute("CREATE TABLE test (value)")
        write.execute("INSERT INTO test VALUES (42)")
        write.commit()
        assert (root / "ledger.sqlite-wal").is_file()
        ops_backup.backup(root, tmp_path / "backup", [root])
    ops_backup.restore(tmp_path / "backup", target)
    with closing(sqlite3.connect(target / "ledger.sqlite")) as restored:
        assert restored.execute("SELECT value FROM test").fetchone() == (42,)
    assert not (target / "ledger.sqlite-wal").exists()


def test_disk_gate_uses_the_same_threshold_as_status(tmp_path, monkeypatch):
    layout = data_ops.Layout(tmp_path)
    monkeypatch.setattr(
        shutil, "disk_usage", lambda _: shutil._ntuple_diskusage(10 * data_ops.GIB, 0, data_ops.GIB)
    )
    assert data_ops.disk_status(layout.root)["status"] == "blocked"
    with pytest.raises(data_ops.OpsBlocked, match="less than 2 GiB"):
        data_ops.replay_demo(layout, FIXTURES)
