"""AO-B4: load_or_fetch must not tight-loop acquire on frequency wall (2002)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_infra.data import tushare_source as ts_src
from ashare_infra.data.tushare_rate_limit import (
    reset_tushare_rate_limiter,
    set_tushare_rate_limiter,
    TushareRateLimiter,
)
from ashare_infra.data.tushare_source import (
    TushareDailyBarsRequest,
    load_or_fetch_daily_bars,
)
from datetime import date


@pytest.fixture(autouse=True)
def _isolate_limiter() -> None:
    reset_tushare_rate_limiter()
    yield
    reset_tushare_rate_limiter()


def test_freq_wall_2002_does_not_retry_three_times(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 23),
    )
    set_tushare_rate_limiter(lim)

    attempts: list[int] = []

    def wall_fetch(_: TushareDailyBarsRequest):
        attempts.append(1)
        # Simulate acquire already happened inside real fetch; count via attempts.
        raise RuntimeError("抱歉，您每分钟最多访问该接口180次，code 2002")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", wall_fetch)
    monkeypatch.setattr(ts_src.time, "sleep", lambda *_: None)

    req = TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240301", end_date="20240301"
    )
    with pytest.raises(RuntimeError, match="2002"):
        load_or_fetch_daily_bars(
            req, cache_dir=tmp_path / "cache", retries=3, backoff_base=0.01
        )
    assert len(attempts) == 1
