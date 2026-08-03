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

# qfq/daily bars path acquires daily + adj_factor (see fetch_tushare_daily_bars).
R4_QFQ_COMPOSITE_APIS = frozenset({"daily", "qfq"})
R4_DEFAULT_ESTIMATED_CALLS: dict[str, int] = {
    "daily": 2,
    "qfq": 2,
    "daily_basic": 1,
    "moneyflow": 1,
    "adj_factor": 1,
}

# TuShare freq-wall / throttle heuristics (doc + field reports).
_FREQ_WALL_PATTERNS = (
    re.compile(r"\b2002\b"),
    re.compile(r"频率", re.I),
    re.compile(r"freq(?:uency)?\s*limit", re.I),
    re.compile(r"too\s+many\s+requests", re.I),
    re.compile(r"ip\s*次数", re.I),
)
_FREQ_WALL_ERROR_PREFIX = "frequency_wall:"


class FrequencyWallPause(RuntimeError):
    """Raised when a TuShare frequency wall should pause the batch (not fail the job)."""


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
        """Pending/in-flight call budget by *underlying* TuShare API name.

        qfq/daily jobs with ``estimated_calls>=2`` expand to daily+adj_factor so
        dry_run / can_afford match real ``acquire_tushare_call`` usage.
        """
        totals: dict[str, int] = {}
        for job in self.jobs:
            if job.status in ("done", "skipped"):
                continue
            for api, n in expand_job_api_calls(job).items():
                totals[api] = totals.get(api, 0) + n
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
        payload = json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(out)
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
    failed: bool = False


def _has_failed_jobs(manifest: BatchManifest) -> bool:
    return any(j.status == "failed" for j in manifest.jobs)


def _sync_manifest_when_no_pending(manifest: BatchManifest) -> None:
    """Terminal state when no pending jobs remain (F-05: do not mark completed if jobs failed)."""
    if manifest.pending_jobs():
        return
    if _has_failed_jobs(manifest):
        manifest.state = "failed"
    else:
        manifest.state = "completed"
        manifest.pause_reason = None


JobExecutor = Callable[[FetchJob], None]


def is_frequency_wall_error(exc: BaseException | str) -> bool:
    text = str(exc)
    if text.startswith(_FREQ_WALL_ERROR_PREFIX):
        return True
    return any(p.search(text) for p in _FREQ_WALL_PATTERNS)


def default_estimated_calls(api: str) -> int:
    """Default acquire count for one planned job (qfq daily path = 2)."""
    name = str(api or "").strip() or "unknown"
    return int(R4_DEFAULT_ESTIMATED_CALLS.get(name, 1))


def expand_job_api_calls(job: FetchJob) -> dict[str, int]:
    """Map a job to underlying API acquire counts for budget checks."""
    api = str(job.api or "").strip() or "unknown"
    n = max(1, int(job.estimated_calls))
    if api in R4_QFQ_COMPOSITE_APIS and n >= 2:
        # One composite qfq fetch: daily + adj_factor; extras stay on daily.
        return {"daily": 1 + max(0, n - 2), "adj_factor": 1}
    return {api: n}


def job_can_afford(job: FetchJob, limiter: TushareRateLimiter) -> tuple[bool, str | None]:
    """Return (ok, reason) for whether ``job`` fits remaining daily budgets."""
    for api, n in expand_job_api_calls(job).items():
        rem = limiter.remaining_daily(api)
        if rem < n:
            return (
                False,
                f"daily cap would be exceeded for api={api!r} "
                f"(need={n}, remaining={rem}; job_api={job.api!r})",
            )
    return True, None


def requeue_frequency_wall_jobs(manifest: BatchManifest) -> int:
    """Reset ``frequency_wall:`` failed jobs to pending so resume retries them.

    Also clears last pause note on jobs that stayed pending after a wall.
    Returns number of jobs requeued from failed → pending.
    """
    n = 0
    for job in manifest.jobs:
        err = job.error or ""
        if job.status == "failed" and (
            err.startswith(_FREQ_WALL_ERROR_PREFIX) or is_frequency_wall_error(err)
        ):
            job.status = "pending"
            n += 1
        if job.status == "pending" and err.startswith(_FREQ_WALL_ERROR_PREFIX):
            # Keep attempts; drop pause note so a clean retry is visible.
            job.error = None
    return n


def make_r4_refresh_executor(
    *,
    lake: Any | None = None,
    cache_dir: Path | str | None = None,
    token: str | None = None,
    adjust: str = "qfq",
) -> JobExecutor:
    """AO-B2 single live path: DataLake / ``load_or_fetch_*(refresh=True)``.

    Never call ``fetch_tushare_*`` from scripts or this executor. Composite qfq
    still goes through ``load_or_fetch_daily_bars`` → ``fetch_tushare_daily_bars``
    (daily + adj_factor) under the T1 limiter.
    """
    from dataclasses import replace

    from ashare_infra.lake.r4_contract import R4_ADJUST_DEFAULT, make_r4_datalake

    adj = adjust or R4_ADJUST_DEFAULT
    if lake is None:
        lake_obj = make_r4_datalake(
            cache_dir=cache_dir, refresh=True, tushare_token=token
        )
    else:
        lake_obj = replace(lake, refresh=True)
        if token is not None:
            lake_obj = replace(lake_obj, tushare_token=token)

    def _execute(job: FetchJob) -> None:
        api = str(job.api or "").strip()
        if api in R4_QFQ_COMPOSITE_APIS:
            lake_obj.load_daily_bars(
                job.symbol, job.start_date, job.end_date, adjust=adj
            )
            return
        if api == "daily_basic":
            from ashare_infra.data.tushare_source import (
                TushareDailyBasicRequest,
                load_or_fetch_daily_basic,
            )

            load_or_fetch_daily_basic(
                TushareDailyBasicRequest(
                    symbol=job.symbol,
                    start_date=job.start_date,
                    end_date=job.end_date,
                    token=lake_obj.tushare_token,
                ),
                cache_dir=lake_obj.cache_dir,
                refresh=True,
            )
            return
        if api == "moneyflow":
            from ashare_infra.data.tushare_source import (
                TushareMoneyflowRequest,
                load_or_fetch_moneyflow,
            )

            load_or_fetch_moneyflow(
                TushareMoneyflowRequest(
                    symbol=job.symbol,
                    start_date=job.start_date,
                    end_date=job.end_date,
                    token=lake_obj.tushare_token,
                ),
                cache_dir=lake_obj.cache_dir,
                refresh=True,
            )
            return
        raise BatchPolicyError(
            f"unsupported batch api={api!r}; use daily|qfq|daily_basic|moneyflow"
        )

    return _execute


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
            if api in estimated_calls_per_job:
                return int(estimated_calls_per_job[api])
            return default_estimated_calls(api)
        # Explicit int overrides all APIs; otherwise use api-aware defaults (qfq=2).
        if estimated_calls_per_job != 1:
            return int(estimated_calls_per_job)
        return default_estimated_calls(api)

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
            failed=False,
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
            ok, reason = job_can_afford(job, lim)
            if not ok:
                # Leave pending so resume can retry after day roll / budget free.
                job.error = reason
                manifest.state = "paused_daily_cap"
                manifest.pause_reason = reason
                if manifest_path:
                    manifest.save(manifest_path)
                return BatchRunResult(
                    manifest=manifest,
                    processed=processed,
                    paused=True,
                    pause_kind="daily_cap",
                    dry_run=False,
                    failed=False,
                )

            job.attempts += 1
            try:
                executor(job)
            except TushareRateLimitExceeded as exc:
                job.status = "pending"
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
                    failed=False,
                )
            except FrequencyWallPause as exc:
                # AO-B1: stay pending; resume retries the same job.
                job.status = "pending"
                job.error = f"{_FREQ_WALL_ERROR_PREFIX} {exc}"
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
                    failed=False,
                )
            except Exception as exc:  # noqa: BLE001 — batch boundary
                if burst_pause and is_frequency_wall_error(exc):
                    job.status = "pending"
                    job.error = f"{_FREQ_WALL_ERROR_PREFIX} {exc}"
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
                        failed=False,
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
                    failed=True,
                )

            job.status = "done"
            job.error = None
            processed += 1
            if manifest_path:
                manifest.save(manifest_path)

        _sync_manifest_when_no_pending(manifest)
        if manifest_path:
            manifest.save(manifest_path)

    return BatchRunResult(
        manifest=manifest,
        processed=processed,
        paused=False,
        pause_kind=None,
        dry_run=False,
        failed=manifest.state == "failed",
    )


def resume_batch(
    manifest_or_path: BatchManifest | Path | str,
    executor: JobExecutor,
    *,
    limiter: TushareRateLimiter | None = None,
    manifest_path: Path | str | None = None,
    max_jobs: int | None = None,
) -> BatchRunResult:
    """Resume a paused/planned manifest from remaining pending jobs.

    AO-B1: requeues legacy ``frequency_wall:`` *failed* jobs to pending so the
    same job is retried after a wall clears.
    """
    if isinstance(manifest_or_path, (str, Path)):
        path = Path(manifest_or_path)
        manifest = BatchManifest.load(path)
        save_path: Path | str | None = manifest_path or path
    else:
        manifest = manifest_or_path
        save_path = manifest_path

    requeue_frequency_wall_jobs(manifest)

    if (
        manifest.state == "completed"
        and not manifest.pending_jobs()
        and not _has_failed_jobs(manifest)
    ):
        return BatchRunResult(
            manifest=manifest,
            processed=0,
            paused=False,
            pause_kind=None,
            dry_run=False,
            failed=False,
        )

    # Clear pause so run_batch can proceed; non-freq-wall failed jobs stay failed.
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
    "R4_DEFAULT_ESTIMATED_CALLS",
    "R4_MAX_BATCH_SYMBOLS",
    "R4_QFQ_COMPOSITE_APIS",
    "chunk_symbols",
    "default_estimated_calls",
    "dry_run_batch",
    "expand_job_api_calls",
    "is_frequency_wall_error",
    "job_can_afford",
    "make_r4_refresh_executor",
    "plan_batch",
    "requeue_frequency_wall_jobs",
    "resume_batch",
    "run_batch",
]
