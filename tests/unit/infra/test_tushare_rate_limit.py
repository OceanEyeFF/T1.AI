"""WT-R4-A3-T1: approved caps enforced on TuShare fetch path (no live)."""

from __future__ import annotations

from datetime import date

import pytest

from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimitExceeded,
    TushareRateLimiter,
    acquire_tushare_call,
    get_tushare_rate_limiter,
    reset_tushare_rate_limiter,
    set_tushare_rate_limiter,
)
from ashare_infra.lake.r4_contract import r4_approved_daily_per_api, r4_approved_rpm


@pytest.fixture(autouse=True)
def _isolate_limiter() -> None:
    reset_tushare_rate_limiter()
    yield
    reset_tushare_rate_limiter()


def test_from_r4_approved_binds_repo_caps() -> None:
    lim = TushareRateLimiter.from_r4_approved(sleep=lambda _: None)
    assert lim.rpm == r4_approved_rpm() == 180
    assert lim.daily_per_api == r4_approved_daily_per_api() == 80000
    assert lim.min_interval_s == pytest.approx(60.0 / 180.0)


def test_daily_budget_blocks_after_cap() -> None:
    clock = {"t": 0.0}
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=2,
        clock=lambda: clock["t"],
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    lim.acquire("daily")
    clock["t"] += 1.0
    lim.acquire("daily")
    clock["t"] += 1.0
    with pytest.raises(TushareRateLimitExceeded, match="daily cap exceeded"):
        lim.acquire("daily")
    assert lim.remaining_daily("daily") == 0
    assert lim.remaining_daily("moneyflow") == 2  # per-API budgets


def test_rpm_spacing_sleeps_between_calls() -> None:
    clock = {"t": 100.0}
    slept: list[float] = []

    def _sleep(s: float) -> None:
        slept.append(s)
        clock["t"] += s

    lim = TushareRateLimiter(
        rpm=60,  # min_interval = 1.0s
        daily_per_api=100,
        clock=lambda: clock["t"],
        sleep=_sleep,
        today=lambda: date(2026, 7, 22),
    )
    assert lim.acquire("daily") == 0.0
    clock["t"] += 0.25  # only 0.25s elapsed → wait 0.75
    waited = lim.acquire("daily")
    assert waited == pytest.approx(0.75)
    assert slept == [pytest.approx(0.75)]


def test_day_roll_resets_counts() -> None:
    day = {"d": date(2026, 7, 22)}
    clock = {"t": 0.0}
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=1,
        clock=lambda: clock["t"],
        sleep=lambda _: None,
        today=lambda: day["d"],
    )
    lim.acquire("daily")
    with pytest.raises(TushareRateLimitExceeded):
        lim.acquire("daily")
    day["d"] = date(2026, 7, 23)
    clock["t"] += 10.0
    lim.acquire("daily")  # new day
    assert lim.remaining_daily("daily") == 0


def test_singleton_uses_approved_caps() -> None:
    lim = get_tushare_rate_limiter()
    assert lim.rpm == 180
    assert lim.daily_per_api == 80000
    acquire_tushare_call("daily", dry_run=True)  # dry_run does not consume
    assert lim.remaining_daily("daily") == 80000


def test_fetch_daily_bars_acquires_before_pro_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch path must call acquire for each HTTP/SDK call (no live)."""
    from ashare_infra.data import tushare_source as src

    calls: list[str] = []

    def _fake_acquire(api_name: str, *, dry_run: bool = False) -> float:
        calls.append(api_name)
        return 0.0

    class _Pro:
        def daily(self, **kwargs):  # noqa: ANN003
            return __import__("pandas").DataFrame(
                {
                    "trade_date": ["20240102"],
                    "open": [1.0],
                    "high": [1.0],
                    "low": [1.0],
                    "close": [1.0],
                    "vol": [100.0],
                    "amount": [1000.0],
                }
            )

        def adj_factor(self, **kwargs):  # noqa: ANN003
            return __import__("pandas").DataFrame(
                {"trade_date": ["20240102"], "adj_factor": [1.0]}
            )

    monkeypatch.setattr(src, "acquire_tushare_call", _fake_acquire)
    monkeypatch.setattr(src, "_get_tushare_pro", lambda token=None: _Pro())

    req = src.TushareDailyBarsRequest(
        symbol="600000.SH",
        start_date="20240102",
        end_date="20240102",
        adjust="qfq",
    )
    df = src.fetch_tushare_daily_bars(req)
    assert not df.empty
    assert calls == ["daily", "adj_factor"]


def test_set_limiter_for_tests() -> None:
    custom = TushareRateLimiter(
        rpm=10,
        daily_per_api=5,
        sleep=lambda _: None,
        today=lambda: date(2026, 1, 1),
    )
    set_tushare_rate_limiter(custom)
    assert get_tushare_rate_limiter() is custom
    assert get_tushare_rate_limiter().rpm == 10
