"""Fund/ETF fallback when stock daily is empty (e.g. 510300.SH)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from ashare_infra.data import tushare_source as ts_src
from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimiter,
    reset_tushare_rate_limiter,
    set_tushare_rate_limiter,
)
from ashare_infra.data.tushare_source import (
    TushareDailyBarsRequest,
    load_or_fetch_daily_bars,
)


@pytest.fixture(autouse=True)
def _isolate_limiter() -> None:
    reset_tushare_rate_limiter()
    yield
    reset_tushare_rate_limiter()


def test_fund_daily_fallback_writes_qfq_cache(
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

    def _acq(api: str, *, dry_run: bool = False) -> float:
        if not dry_run:
            acquires.append(api)
        return lim.acquire(api, dry_run=dry_run)

    monkeypatch.setattr(ts_src, "acquire_tushare_call", _acq)

    empty = pd.DataFrame()
    fund_raw = pd.DataFrame(
        {
            "ts_code": ["510300.SH", "510300.SH"],
            "trade_date": ["20230104", "20230105"],
            "open": [4.0, 4.1],
            "high": [4.2, 4.3],
            "low": [3.9, 4.0],
            "close": [4.1, 4.2],
            "vol": [1000.0, 1100.0],
            "amount": [4000.0, 4500.0],
        }
    )

    pro = SimpleNamespace(
        daily=lambda **_: empty,
        fund_daily=lambda **_: fund_raw,
        adj_factor=lambda **_: (_ for _ in ()).throw(AssertionError("no adj for fund")),
    )
    monkeypatch.setattr(ts_src, "_get_tushare_pro", lambda token=None: pro)

    req = TushareDailyBarsRequest(
        symbol="510300.SH", start_date="20230101", end_date="20230131", adjust="qfq"
    )
    df = load_or_fetch_daily_bars(req, cache_dir=tmp_path / "cache", refresh=True)
    assert len(df) == 2
    assert acquires == ["daily", "fund_daily"]
    part = tmp_path / "cache" / "tushare_qfq" / "510300.SH" / "year=2023" / "part.parquet"
    assert part.is_file()
