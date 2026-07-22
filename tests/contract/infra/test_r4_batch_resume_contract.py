"""Contract: R4 batch runner enforces ≤50 symbols + freq-wall pause policy."""

from __future__ import annotations

from ashare_infra.data.tushare_batch import (
    R4_MAX_BATCH_SYMBOLS,
    R4BatchPolicy,
    chunk_symbols,
    is_frequency_wall_error,
    plan_batch,
)
from ashare_infra.lake.r4_contract import r4_approved_daily_per_api, r4_approved_rpm


def test_batch_policy_matches_approved_caps_and_a1_ops() -> None:
    pol = R4BatchPolicy.from_r4_config()
    assert pol.rpm == r4_approved_rpm() == 180
    assert pol.daily_api_calls_per_api == r4_approved_daily_per_api() == 80000
    assert pol.concurrency == 1
    assert pol.burst_pause_on_freq_wall is True
    assert pol.max_batch_symbols == R4_MAX_BATCH_SYMBOLS == 50


def test_chunk_boundary_is_fifty() -> None:
    syms = [f"{i:06d}.SH" for i in range(100)]
    chunks = chunk_symbols(syms)
    assert all(len(c) <= 50 for c in chunks)
    assert len(chunks[0]) == 50
    m = plan_batch(
        chunks[0],
        apis=("daily", "moneyflow"),
        start_date="20230101",
        end_date="20230105",
    )
    assert m.policy["max_batch_symbols"] == 50
    assert m.policy["concurrency"] == 1
    assert len(m.jobs) == 100  # 50 symbols × 2 apis


def test_freq_wall_detector_covers_code_2002() -> None:
    assert is_frequency_wall_error("抱歉，您每分钟最多访问该接口180次，code 2002")
