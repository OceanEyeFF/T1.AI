"""AO-R1: batch executor → DataLake/load_or_fetch → acquire counts (zero network)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.data.tushare_batch import (
    dry_run_batch,
    make_r4_refresh_executor,
    plan_batch,
    run_batch,
)
from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimiter,
    get_tushare_rate_limiter,
    reset_tushare_rate_limiter,
    set_tushare_rate_limiter,
)
from ashare_infra.data import tushare_source as ts_src
from ashare_infra.lake.r4_contract import make_r4_datalake


@pytest.fixture(autouse=True)
def _isolate_limiter() -> None:
    reset_tushare_rate_limiter()
    yield
    reset_tushare_rate_limiter()


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume", "amount"]
    )


def test_batch_executor_acquire_matches_dry_run_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 23),
    )
    set_tushare_rate_limiter(lim)

    acquires: list[str] = []

    def _counting_acquire(api_name: str, *, dry_run: bool = False) -> float:
        if not dry_run:
            acquires.append(api_name)
        return lim.acquire(api_name, dry_run=dry_run)

    monkeypatch.setattr(ts_src, "acquire_tushare_call", _counting_acquire)

    def _fake_daily(req):  # noqa: ANN001
        # Mirror real qfq path: acquire daily + adj_factor then return empty.
        ts_src.acquire_tushare_call("daily")
        ts_src.acquire_tushare_call("adj_factor")
        return _empty_bars()

    def _fake_basic(req):  # noqa: ANN001
        ts_src.acquire_tushare_call("daily_basic")
        return pd.DataFrame(columns=list(ts_src.SUPPORTED_DAILY_BASIC_FIELDS))

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", _fake_daily)
    monkeypatch.setattr(ts_src, "fetch_tushare_daily_basic", _fake_basic)

    cache = tmp_path / "cache"
    lake = make_r4_datalake(cache_dir=cache, refresh=True, tushare_token="test-token")
    m = plan_batch(
        ["600000.SH"],
        apis=("daily", "daily_basic"),
        start_date="20240101",
        end_date="20240105",
    )
    report = dry_run_batch(m, limiter=get_tushare_rate_limiter())
    needed = report["estimates"]["pending_calls_by_api"]
    assert needed == {"daily": 1, "adj_factor": 1, "daily_basic": 1}

    executor = make_r4_refresh_executor(lake=lake)
    result = run_batch(m, executor, limiter=lim)
    assert result.paused is False
    assert m.state == "completed"
    # Live acquires must match dry_run expansion (not double-count under job.api).
    assert acquires.count("daily") == 1
    assert acquires.count("adj_factor") == 1
    assert acquires.count("daily_basic") == 1
    assert len(acquires) == 3
