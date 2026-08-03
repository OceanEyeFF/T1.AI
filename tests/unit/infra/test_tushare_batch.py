"""WT-R4-A3-T2/T3: frequency-wall pause + resume batch runner (no live)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ashare_infra.data.tushare_batch import (
    R4_MAX_BATCH_SYMBOLS,
    BatchManifest,
    BatchPolicyError,
    FrequencyWallPause,
    R4BatchPolicy,
    chunk_symbols,
    default_estimated_calls,
    dry_run_batch,
    expand_job_api_calls,
    is_frequency_wall_error,
    plan_batch,
    resume_batch,
    run_batch,
)
from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimiter,
    reset_tushare_rate_limiter,
    set_tushare_rate_limiter,
)


@pytest.fixture(autouse=True)
def _isolate_limiter() -> None:
    reset_tushare_rate_limiter()
    yield
    reset_tushare_rate_limiter()


def test_policy_from_r4_config() -> None:
    pol = R4BatchPolicy.from_r4_config()
    assert pol.concurrency == 1
    assert pol.burst_pause_on_freq_wall is True
    assert pol.max_batch_symbols == 50
    assert pol.rpm == 180
    assert pol.daily_api_calls_per_api == 80000


def test_chunk_and_plan_rejects_oversize() -> None:
    syms = [f"{i:06d}.SH" for i in range(51)]
    assert len(chunk_symbols(syms)) == 2
    with pytest.raises(BatchPolicyError, match="max_batch_symbols"):
        plan_batch(syms, start_date="20230101", end_date="20230131")
    m = plan_batch(
        syms, start_date="20230101", end_date="20230131", allow_truncate=True
    )
    assert len({j.symbol for j in m.jobs}) == R4_MAX_BATCH_SYMBOLS


def test_plan_estimates_and_dry_run(tmp_path: Path) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    set_tushare_rate_limiter(lim)
    m = plan_batch(
        ["600000.SH", "000001.SZ"],
        apis=("daily", "daily_basic"),
        start_date="20230101",
        end_date="20231231",
        estimated_calls_per_job={"daily": 2, "daily_basic": 1},
    )
    assert len(m.jobs) == 4
    # daily expands to daily+adj_factor; basic stays on daily_basic
    assert m.estimate_calls_by_api() == {
        "daily": 2,
        "adj_factor": 2,
        "daily_basic": 2,
    }
    assert m.estimate_total_calls() == 6  # 2*(1+1) + 2*1
    report = dry_run_batch(m, limiter=lim)
    assert report["dry_run"] is True
    assert report["blocking_apis"] == []
    assert m.state == "dry_run"
    path = m.save(tmp_path / "manifest.json")
    loaded = BatchManifest.load(path)
    assert loaded.manifest_id == m.manifest_id
    assert len(loaded.jobs) == 4


def test_ao_b3_default_qfq_estimated_calls_expand() -> None:
    assert default_estimated_calls("daily") == 2
    m = plan_batch(
        ["600000.SH"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )
    job = m.jobs[0]
    assert job.estimated_calls == 2
    assert expand_job_api_calls(job) == {"daily": 1, "adj_factor": 1}
    assert m.estimate_calls_by_api() == {"daily": 1, "adj_factor": 1}


def test_freq_wall_pauses_without_tight_loop(tmp_path: Path) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    m = plan_batch(
        ["600000.SH", "000001.SZ", "600519.SH"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )
    calls: list[str] = []

    def _exec(job) -> None:  # noqa: ANN001
        calls.append(job.symbol)
        if job.symbol == "000001.SZ":
            raise RuntimeError("code=2002 抱歉，您每分钟最多访问该接口180次")

    path = tmp_path / "m.json"
    result = run_batch(m, _exec, limiter=lim, manifest_path=path)
    assert result.paused is True
    assert result.pause_kind == "freq_wall"
    assert m.state == "paused_freq_wall"
    assert calls == ["600000.SH", "000001.SZ"]  # stopped; no tight retry of 000001
    # AO-B1: wall job stays pending (not failed); third still pending
    assert m.jobs[0].status == "done"
    assert m.jobs[1].status == "pending"
    assert m.jobs[1].error is not None and m.jobs[1].error.startswith(
        "frequency_wall:"
    )
    assert m.jobs[2].status == "pending"

    # Resume after wall clears: retry same wall job, then remaining
    calls.clear()

    def _exec2(job) -> None:  # noqa: ANN001
        calls.append(job.symbol)

    result2 = resume_batch(path, _exec2, limiter=lim)
    assert result2.paused is False
    assert result2.manifest.state == "completed"
    assert calls == ["000001.SZ", "600519.SH"]
    loaded = BatchManifest.load(path)
    assert loaded.jobs[0].status == "done"
    assert loaded.jobs[1].status == "done"
    assert loaded.jobs[1].attempts >= 2


def test_resume_requeues_legacy_failed_freq_wall(tmp_path: Path) -> None:
    """Legacy manifests that marked wall jobs failed must still retry on resume."""
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    m = plan_batch(
        ["000001.SZ"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )
    m.jobs[0].status = "failed"
    m.jobs[0].error = "frequency_wall: code 2002"
    m.jobs[0].attempts = 1
    m.state = "paused_freq_wall"
    path = m.save(tmp_path / "legacy.json")

    calls: list[str] = []

    def _exec(job) -> None:  # noqa: ANN001
        calls.append(job.symbol)

    result = resume_batch(path, _exec, limiter=lim)
    assert result.manifest.state == "completed"
    assert calls == ["000001.SZ"]
    assert BatchManifest.load(path).jobs[0].status == "done"


def test_daily_cap_pauses(tmp_path: Path) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=1,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    # Simulate one call already used on daily; qfq job needs daily+adj_factor.
    lim.acquire("daily")
    m = plan_batch(
        ["600000.SH", "000001.SZ"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )

    def _exec(job) -> None:  # noqa: ANN001
        raise AssertionError("executor must not run when unaffordable")

    result = run_batch(m, _exec, limiter=lim, manifest_path=tmp_path / "cap.json")
    assert result.paused is True
    assert result.pause_kind == "daily_cap"
    assert m.state == "paused_daily_cap"
    assert all(j.status == "pending" for j in m.jobs)


def test_is_frequency_wall_heuristics() -> None:
    assert is_frequency_wall_error("2002")
    assert is_frequency_wall_error(RuntimeError("频率过高"))
    assert not is_frequency_wall_error(RuntimeError("token invalid"))


def test_run_batch_dry_run_skips_executor() -> None:
    m = plan_batch(
        ["600000.SH"],
        start_date="20240101",
        end_date="20240102",
    )

    def _boom(job) -> None:  # noqa: ANN001
        raise AssertionError("no executor on dry_run")

    result = run_batch(m, _boom, dry_run=True)
    assert result.dry_run is True
    assert result.processed == 0
    assert result.failed is False
    assert m.jobs[0].status == "pending"


def test_non_wall_failure_sets_result_failed(tmp_path: Path) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    m = plan_batch(
        ["600000.SH", "000001.SZ"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )

    def _exec(job) -> None:  # noqa: ANN001
        if job.symbol == "000001.SZ":
            raise RuntimeError("token invalid")

    result = run_batch(m, _exec, limiter=lim, manifest_path=tmp_path / "fail.json")
    assert result.failed is True
    assert result.paused is False
    assert m.state == "failed"
    assert m.jobs[0].status == "done"
    assert m.jobs[1].status == "failed"


def test_terminal_state_failed_not_completed_when_failed_jobs_remain(
    tmp_path: Path,
) -> None:
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    m = plan_batch(
        ["600000.SH", "000001.SZ", "600519.SH"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )
    m.jobs[0].status = "done"
    m.jobs[1].status = "failed"
    m.jobs[1].error = "upstream error"
    m.state = "failed"

    def _exec(job) -> None:  # noqa: ANN001
        pass

    result = run_batch(m, _exec, limiter=lim, manifest_path=tmp_path / "partial.json")
    assert result.failed is True
    assert m.state == "failed"
    assert m.jobs[2].status == "done"


def test_manifest_save_no_tmp_leftover_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TG-07 (downgraded): success path uses *.tmp then replace; no leftover; reload ok.

    Does not claim crash-atomic / kill-9 safety — only happy-path tmp+replace.
    """
    replace_srcs: list[Path] = []
    orig_replace = Path.replace

    def _tracking_replace(self: Path, target: Path | str) -> Path:  # noqa: ANN001
        replace_srcs.append(Path(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _tracking_replace)

    m = plan_batch(
        ["600000.SH"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )
    path = tmp_path / "manifest.json"
    m.save(path)
    assert path.is_file()
    assert any(p.name.endswith(".tmp") for p in replace_srcs), replace_srcs
    assert list(tmp_path.glob("*.tmp")) == []
    loaded = BatchManifest.load(path)
    assert loaded.manifest_id == m.manifest_id
    assert len(loaded.jobs) == 1


def test_non_wall_mid_job_failure_leaves_later_pending(tmp_path: Path) -> None:
    """TG-15: mid-job RuntimeError → that job failed, later pending; resume finishes."""
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    m = plan_batch(
        ["600000.SH", "000001.SZ", "600519.SH"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )
    path = tmp_path / "mid_fail.json"

    def _exec(job) -> None:  # noqa: ANN001
        if job.symbol == "000001.SZ":
            raise RuntimeError("upstream boom")

    result = run_batch(m, _exec, limiter=lim, manifest_path=path)
    assert result.failed is True
    assert result.paused is False
    assert m.jobs[0].status == "done"
    assert m.jobs[1].status == "failed"
    assert m.jobs[2].status == "pending"

    def _ok(job) -> None:  # noqa: ANN001
        pass

    result2 = resume_batch(path, _ok, limiter=lim)
    loaded = BatchManifest.load(path)
    assert loaded.jobs[2].status == "done"
    # Failed mid-job remains failed; terminal state stays failed.
    assert loaded.jobs[1].status == "failed"
    assert result2.failed is True
    assert loaded.state == "failed"


def test_frequency_wall_pause_typed_exception(tmp_path: Path) -> None:
    """TG-16: executor raises FrequencyWallPause → paused freq_wall, job pending."""
    lim = TushareRateLimiter(
        rpm=180,
        daily_per_api=80000,
        sleep=lambda _: None,
        today=lambda: date(2026, 7, 22),
    )
    m = plan_batch(
        ["600000.SH", "000001.SZ"],
        apis=("daily",),
        start_date="20240101",
        end_date="20240131",
    )

    def _exec(job) -> None:  # noqa: ANN001
        if job.symbol == "600000.SH":
            raise FrequencyWallPause("typed wall")

    result = run_batch(m, _exec, limiter=lim, manifest_path=tmp_path / "typed_wall.json")
    assert result.paused is True
    assert result.pause_kind == "freq_wall"
    assert m.state == "paused_freq_wall"
    assert m.jobs[0].status == "pending"
    assert m.jobs[0].error is not None and m.jobs[0].error.startswith("frequency_wall:")
    assert m.jobs[1].status == "pending"
