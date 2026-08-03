"""Runtime enforce of MS-R4 approved TuShare L2 rate caps.

Caps source: ``ashare_infra.lake.r4_contract`` →
``inputs/configs/tushare_rate_limits.toml`` (rpm=180, daily_api_calls_per_api=80000).

T1 wires acquire-before-call into ``fetch_tushare_*``. Frequency-wall pause /
resume manifests live in ``tushare_batch`` (T2).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from ashare_infra.lake.r4_contract import r4_approved_daily_per_api, r4_approved_rpm

SHANGHAI = ZoneInfo("Asia/Shanghai")


class TushareRateLimitExceeded(RuntimeError):
    """Raised when an API would exceed the approved daily per-API budget."""


@dataclass
class RateLimitSnapshot:
    rpm: int
    daily_per_api: int
    calendar_day: date
    calls_today: dict[str, int]
    min_interval_s: float
    last_call_monotonic: float | None


@dataclass
class TushareRateLimiter:
    """Process-local limiter: RPM spacing + per-API Shanghai calendar-day budget.

    Inject ``clock`` / ``sleep`` / ``today`` for deterministic unit tests.
    """

    rpm: int
    daily_per_api: int
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    today: Callable[[], date] = field(
        default=lambda: datetime.now(SHANGHAI).date()
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _day: date | None = field(default=None, init=False, repr=False)
    _counts: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _last_call_monotonic: float | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_r4_approved(cls, **kwargs: Any) -> TushareRateLimiter:
        return cls(
            rpm=int(r4_approved_rpm()),
            daily_per_api=int(r4_approved_daily_per_api()),
            **kwargs,
        )

    @property
    def min_interval_s(self) -> float:
        if self.rpm <= 0:
            return 0.0
        return 60.0 / float(self.rpm)

    def _roll_day_locked(self) -> None:
        day = self.today()
        if self._day != day:
            self._day = day
            self._counts.clear()

    def remaining_daily(self, api_name: str) -> int:
        with self._lock:
            self._roll_day_locked()
            used = int(self._counts.get(api_name, 0))
            return max(0, self.daily_per_api - used)

    def can_afford(self, api_name: str, n: int = 1) -> bool:
        if n < 0:
            raise ValueError("n must be >= 0")
        return self.remaining_daily(api_name) >= n

    def snapshot(self) -> RateLimitSnapshot:
        with self._lock:
            self._roll_day_locked()
            assert self._day is not None
            return RateLimitSnapshot(
                rpm=self.rpm,
                daily_per_api=self.daily_per_api,
                calendar_day=self._day,
                calls_today=dict(self._counts),
                min_interval_s=self.min_interval_s,
                last_call_monotonic=self._last_call_monotonic,
            )

    def reset(self) -> None:
        with self._lock:
            self._day = None
            self._counts.clear()
            self._last_call_monotonic = None

    def acquire(self, api_name: str, *, dry_run: bool = False) -> float:
        """Reserve one call for ``api_name``.

        Returns seconds slept for RPM spacing (0 if none / dry_run).
        Raises ``TushareRateLimitExceeded`` if daily budget would be exceeded.
        """
        name = str(api_name or "").strip() or "unknown"
        slept = 0.0

        if dry_run:
            with self._lock:
                self._roll_day_locked()
                used = int(self._counts.get(name, 0))
                if used >= self.daily_per_api:
                    raise TushareRateLimitExceeded(
                        f"TuShare daily cap exceeded for api={name!r}: "
                        f"{used}/{self.daily_per_api} "
                        f"(day={self._day}, rpm={self.rpm})"
                    )
            return 0.0

        while True:
            wait = 0.0
            with self._lock:
                self._roll_day_locked()
                used = int(self._counts.get(name, 0))
                if used >= self.daily_per_api:
                    raise TushareRateLimitExceeded(
                        f"TuShare daily cap exceeded for api={name!r}: "
                        f"{used}/{self.daily_per_api} "
                        f"(day={self._day}, rpm={self.rpm})"
                    )

                interval = self.min_interval_s
                if interval > 0 and self._last_call_monotonic is not None:
                    elapsed = self.clock() - self._last_call_monotonic
                    wait = interval - elapsed

                if wait <= 0:
                    self._counts[name] = used + 1
                    self._last_call_monotonic = self.clock()
                    return slept

            # Sleep outside the lock so other threads can make progress.
            self.sleep(wait)
            slept += wait


_limiter: TushareRateLimiter | None = None
_limiter_lock = threading.Lock()


def get_tushare_rate_limiter() -> TushareRateLimiter:
    """Process singleton bound to current R4 approved caps."""
    global _limiter
    with _limiter_lock:
        if _limiter is None:
            _limiter = TushareRateLimiter.from_r4_approved()
        return _limiter


def set_tushare_rate_limiter(limiter: TushareRateLimiter | None) -> None:
    """Replace or clear the process singleton (tests)."""
    global _limiter
    with _limiter_lock:
        _limiter = limiter


def reset_tushare_rate_limiter() -> None:
    """Drop singleton so next get rebuilds from approved caps."""
    set_tushare_rate_limiter(None)


def acquire_tushare_call(api_name: str, *, dry_run: bool = False) -> float:
    """Convenience: acquire on the process singleton."""
    return get_tushare_rate_limiter().acquire(api_name, dry_run=dry_run)


__all__ = [
    "RateLimitSnapshot",
    "TushareRateLimitExceeded",
    "TushareRateLimiter",
    "acquire_tushare_call",
    "get_tushare_rate_limiter",
    "reset_tushare_rate_limiter",
    "set_tushare_rate_limiter",
]
