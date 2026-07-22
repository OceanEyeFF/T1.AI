"""R4 TuShare limited-live batch runner: frequency-wall pause + resume.

Built on T1 ``tushare_rate_limit``. T2 delivers dry-run / pause / resume
without network. T3 supplies a live executor under M1/normal approve.

Policy (A1 approved + toml ``[policy]``):
- concurrency = 1
- burst_pause_on_freq_wall = true
- per-batch symbols ≤ 50
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimitExceeded,
    TushareRateLimiter,
    get_tushare_rate_limiter,
)
from ashare_infra.lake.r4_contract import R4_RATE_LIMITS_CONFIG, load_r4_rate_limits

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

JobStatus = Literal["pending", "done", "failed", "skipped"]
ManifestState = Literal[
    "planned",
    "dry_run",
    "running",
    "paused_freq_wall",
    "paused_daily_cap",
    "completed",
    "failed",
]

R4_MAX_BATCH_SYMBOLS = 50
R4_DEFAULT_CONCURRENCY = 1

# TuShare freq-wall / throttle heuristics (doc + field reports).
_FREQ_WALL_PATTERNS = (
    re.compile(r"\b2002\b"),
    re.compile(r"频率", re.I),
    re.compile(r"freq(?:uency)?\s*limit", re.I),
    re.compile(r"too\s+many\s+requests", re.I),
    re.compile(r"ip\s*次数", re.I),
)


class FrequencyWallPause(RuntimeError):
    """Raised (or recorded) when a TuShare frequency wall is detected."""


class BatchPolicyError(ValueError):
    """Invalid batch planning input."""


@dataclass(frozen=True)
class R4BatchPolicy:
    concurrency: int = R4_DEFAULT_CONCURRENCY
    burst_pause_on_freq_wall: bool = True
    max_batch_symbols: int = R4_MAX_BATCH_SYMBOLS
    rpm: int = 180
    daily_api_calls_per_api: int = 80000

    @classmethod
    def from_r4_config(cls, config_path: Path | str | None = None) -> R4BatchPolicy:
        path = Path(config_path) if config_path else R4_RATE_LIMITS_CONFIG
        caps = load_r4_rate_limits(str(path) if config_path else None)
        approved = caps.get("approved_caps") or {}
        concurrency = R4_DEFAULT_CONCURRENCY
        burst = True
        if path.is_file():
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
            policy = raw.get("policy") or {}
            concurrency = int(policy.get("concurrency", R4_DEFAULT_CONCURRENCY))
            burst = bool(policy.get("burst_pause_on_freq_wall", True))
        if concurrency != 1:
            # A1 lock: single worker only for R4 L2.
            concurrency = 1
        return cls(
            concurrency=concurrency,
            burst_pause_on_freq_wall=burst,
            max_batch_symbols=R4_MAX_BATCH_SYMBOLS,
            rpm=int(approved.get("rpm", 180)),
            daily_api_calls_per_api=int(approved.get("daily_api_calls_per_api", 80000)),
        )


@dataclass
class FetchJob:
    job_id: str
    api: str
    symbol: str
    start_date: str
    end_date: str
    estimated_calls: int = 1
    status: JobStatus = "pending"
    error: str | None = None
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FetchJob:
        return cls(
            job_id=str(payload["job_id"]),
            api=str(payload["api"]),
            symbol=str(payload["symbol"]),
            start_date=str(payload["start_date"]),
            end_date=str(payload["end_date"]),
            estimated_calls=int(payload.get("estimated_calls", 1)),
            status=payload.get("status", "pending"),  # type: ignore[arg-type]
            error=payload.get("error"),
            attempts=int(payload.get("attempts", 0)),
        )


@dataclass
class BatchManifest:
    manifest_id: str
    created_at: str
    policy: dict[str, Any]
    jobs: list[FetchJob] = field(default_factory=list)
    state: ManifestState = "planned"
    pause_reason: str | None = None
    updated_at: str | None = None

    def pending_jobs(self) -> list[FetchJob]:
        return [j for j in self.jobs if j.status == "pending"]

    def estimate_calls_by_api(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for job in self.jobs:
            if job.status in ("done", "skipped"):
                continue
            totals[job.api] = totals.get(job.api, 0) + int(job.estimated_calls)
        return totals

    def estimate_total_calls(self) -> int:
        return sum(self.estimate_calls_by_api().values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "state": self.state,
            "pause_reason": self.pause_reason,
            "policy": dict(self.policy),
            "jobs": [j.to_dict() for j in self.jobs],
            "estimates": {
                "pending_calls_by_api": self.estimate_calls_by_api(),
                "pending_total_calls": self.estimate_total_calls(),
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BatchManifest:
        return cls(
            manifest_id=str(payload["manifest_id"]),
            created_at=str(payload["created_at"]),
            policy=dict(payload.get("policy") or {}),
            jobs=[FetchJob.from_dict(j) for j in payload.get("jobs") or []],
            state=payload.get("state", "planned"),  # type: ignore[arg-type]
            pause_reason=payload.get("pause_reason"),
            updated_at=payload.get("updated_at"),
        )

    def save(self, path: Path | str) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = _utc_now()
        out.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return out

    @classmethod
    def load(cls, path: Path | str) -> BatchManifest:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


@dataclass
class BatchRunResult:
    manifest: BatchManifest
    processed: int
    paused: bool
    pause_kind: str | None
    dry_run: bool


JobExecutor = Callable[[FetchJob], None]


def is_frequency_wall_error(exc: BaseException | str) -> bool:
    text = str(exc)
    return any(p.search(text) for p in _FREQ_WALL_PATTERNS)


def chunk_symbols(
    symbols: Sequence[str],
    *,
    max_batch_symbols: int = R4_MAX_BATCH_SYMBOLS,
) -> list[list[str]]:
    if max_batch_symbols <= 0:
        raise BatchPolicyError("max_batch_symbols must be > 0")
    uniq: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        s = str(raw).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    return [
        uniq[i : i + max_batch_symbols]
        for i in range(0, len(uniq), max_batch_symbols)
    ]


def plan_batch(
    symbols: Sequence[str],
    *,
    apis: Sequence[str] = ("daily",),
    start_date: str,
    end_date: str,
    estimated_calls_per_job: int | dict[str, int] = 1,
    policy: R4BatchPolicy | None = None,
    allow_truncate: bool = False,
    manifest_id: str | None = None,
) -> BatchManifest:
    """Build a resumable manifest. Default: single chunk ≤50 symbols."""
    pol = policy or R4BatchPolicy.from_r4_config()
    chunks = chunk_symbols(symbols, max_batch_symbols=pol.max_batch_symbols)
    if not chunks:
        raise BatchPolicyError("no symbols to plan")
    if len(chunks) > 1 and not allow_truncate:
        raise BatchPolicyError(
            f"symbol count exceeds max_batch_symbols={pol.max_batch_symbols}; "
            "pre-chunk with chunk_symbols() or pass allow_truncate=True "
            "to plan only the first chunk"
        )
    # Single-manifest plan uses first chunk only (caller loops for more).
    selected = chunks[0]
    api_list = [str(a).strip() for a in apis if str(a).strip()]
    if not api_list:
        raise BatchPolicyError("apis must be non-empty")

    def _est(api: str) -> int:
        if isinstance(estimated_calls_per_job, dict):
            return int(estimated_calls_per_job.get(api, 1))
        return int(estimated_calls_per_job)

    jobs: list[FetchJob] = []
    for symbol in selected:
        for api in api_list:
            jobs.append(
                FetchJob(
                    job_id=f"{api}:{symbol}:{start_date}:{end_date}",
                    api=api,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    estimated_calls=max(1, _est(api)),
                )
            )

    return BatchManifest(
        manifest_id=manifest_id or str(uuid.uuid4()),
        created_at=_utc_now(),
        policy={
            "concurrency": pol.concurrency,
            "burst_pause_on_freq_wall": pol.burst_pause_on_freq_wall,
            "max_batch_symbols": pol.max_batch_symbols,
            "rpm": pol.rpm,
            "daily_api_calls_per_api": pol.daily_api_calls_per_api,
            "planned_symbol_count": len(selected),
            "planned_api_count": len(api_list),
        },
        jobs=jobs,
        state="planned",
    )


def dry_run_batch(
    manifest: BatchManifest,
    *,
    limiter: TushareRateLimiter | None = None,
) -> dict[str, Any]:
    """Budget preview: no network, no counter consume beyond dry_run checks."""
    lim = limiter or get_tushare_rate_limiter()
    by_api = manifest.estimate_calls_by_api()
    affordability: dict[str, Any] = {}
    blocking: list[str] = []
    for api, n in by_api.items():
        rem = lim.remaining_daily(api)
        ok = rem >= n
        affordability[api] = {
            "needed": n,
            "remaining_daily": rem,
            "affordable": ok,
        }
        if not ok:
            blocking.append(api)
        else:
            # Validate path without consuming.
            lim.acquire(api, dry_run=True)

    report = {
        "manifest_id": manifest.manifest_id,
        "job_count": len(manifest.jobs),
        "pending_jobs": len(manifest.pending_jobs()),
        "estimates": {
            "pending_calls_by_api": by_api,
            "pending_total_calls": sum(by_api.values()),
        },
        "affordability": affordability,
        "blocking_apis": blocking,
        "policy": dict(manifest.policy),
        "dry_run": True,
    }
    manifest.state = "dry_run"
    return report


def run_batch(
    manifest: BatchManifest,
    executor: JobExecutor,
    *,
    dry_run: bool = False,
    limiter: TushareRateLimiter | None = None,
    manifest_path: Path | str | None = None,
    max_jobs: int | None = None,
) -> BatchRunResult:
    """Serially execute pending jobs (concurrency=1).

    On frequency wall (when policy.burst_pause_on_freq_wall) or daily cap:
    pause, persist optional manifest_path, and return without tight-loop retry.
    """
    if dry_run:
        dry_run_batch(manifest, limiter=limiter)
        if manifest_path:
            manifest.save(manifest_path)
        return BatchRunResult(
            manifest=manifest,
            processed=0,
            paused=False,
            pause_kind=None,
            dry_run=True,
        )

    lim = limiter or get_tushare_rate_limiter()
    burst_pause = bool(manifest.policy.get("burst_pause_on_freq_wall", True))
    # Serialize even if caller spins threads around us.
    lock = getattr(run_batch, "_serial_lock", None)
    if lock is None:
        lock = threading.Lock()
        setattr(run_batch, "_serial_lock", lock)

    processed = 0
    manifest.state = "running"
    manifest.pause_reason = None

    with lock:
        for job in list(manifest.pending_jobs()):
            if max_jobs is not None and processed >= max_jobs:
                break
            # Pre-check daily budget before executor (still counts on real fetch via T1).
            needed = max(1, int(job.estimated_calls))
            if not lim.can_afford(job.api, needed):
                job.status = "failed"
                job.error = (
                    f"daily cap would be exceeded for api={job.api!r} "
                    f"(need={needed}, remaining={lim.remaining_daily(job.api)})"
                )
                manifest.state = "paused_daily_cap"
                manifest.pause_reason = job.error
                if manifest_path:
                    manifest.save(manifest_path)
                return BatchRunResult(
                    manifest=manifest,
                    processed=processed,
                    paused=True,
                    pause_kind="daily_cap",
                    dry_run=False,
                )

            job.attempts += 1
            try:
                executor(job)
            except TushareRateLimitExceeded as exc:
                job.status = "failed"
                job.error = str(exc)
                manifest.state = "paused_daily_cap"
                manifest.pause_reason = str(exc)
                if manifest_path:
                    manifest.save(manifest_path)
                return BatchRunResult(
                    manifest=manifest,
                    processed=processed,
                    paused=True,
                    pause_kind="daily_cap",
                    dry_run=False,
                )
            except Exception as exc:  # noqa: BLE001 — batch boundary
                if burst_pause and is_frequency_wall_error(exc):
                    job.status = "failed"
                    job.error = f"frequency_wall: {exc}"
                    manifest.state = "paused_freq_wall"
                    manifest.pause_reason = job.error
                    if manifest_path:
                        manifest.save(manifest_path)
                    return BatchRunResult(
                        manifest=manifest,
                        processed=processed,
                        paused=True,
                        pause_kind="freq_wall",
                        dry_run=False,
                    )
                job.status = "failed"
                job.error = str(exc)
                manifest.state = "failed"
                manifest.pause_reason = str(exc)
                if manifest_path:
                    manifest.save(manifest_path)
                return BatchRunResult(
                    manifest=manifest,
                    processed=processed,
                    paused=False,
                    pause_kind=None,
                    dry_run=False,
                )

            job.status = "done"
            job.error = None
            processed += 1
            if manifest_path:
                manifest.save(manifest_path)

        if not manifest.pending_jobs():
            manifest.state = "completed"
            manifest.pause_reason = None
        if manifest_path:
            manifest.save(manifest_path)

    return BatchRunResult(
        manifest=manifest,
        processed=processed,
        paused=False,
        pause_kind=None,
        dry_run=False,
    )


def resume_batch(
    manifest_or_path: BatchManifest | Path | str,
    executor: JobExecutor,
    *,
    limiter: TushareRateLimiter | None = None,
    manifest_path: Path | str | None = None,
    max_jobs: int | None = None,
) -> BatchRunResult:
    """Resume a paused/planned manifest from remaining pending jobs."""
    if isinstance(manifest_or_path, (str, Path)):
        path = Path(manifest_or_path)
        manifest = BatchManifest.load(path)
        save_path: Path | str | None = manifest_path or path
    else:
        manifest = manifest_or_path
        save_path = manifest_path

    if manifest.state == "completed" and not manifest.pending_jobs():
        return BatchRunResult(
            manifest=manifest,
            processed=0,
            paused=False,
            pause_kind=None,
            dry_run=False,
        )

    # Clear pause so run_batch can proceed; keep failed jobs as-is.
    if manifest.state.startswith("paused_"):
        manifest.state = "running"
        manifest.pause_reason = None

    return run_batch(
        manifest,
        executor,
        dry_run=False,
        limiter=limiter,
        manifest_path=save_path,
        max_jobs=max_jobs,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = [
    "BatchManifest",
    "BatchPolicyError",
    "BatchRunResult",
    "FetchJob",
    "FrequencyWallPause",
    "R4BatchPolicy",
    "R4_MAX_BATCH_SYMBOLS",
    "chunk_symbols",
    "dry_run_batch",
    "is_frequency_wall_error",
    "plan_batch",
    "resume_batch",
    "run_batch",
]
