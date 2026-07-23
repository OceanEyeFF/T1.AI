"""WT-R4-A3-T4: soft80 / trial-exclude / index residual constants (zero live)."""

from __future__ import annotations

from ashare_infra.lake.r4_contract import (
    R4_HARD_CAP,
    R4_INDEX_ANCHOR,
    R4_INDEX_OPTIONAL_NAMESPACES,
    R4_INDEX_REQUIRED_NAMESPACES,
    R4_SOFT80_STATUS,
    R4_SOFT_TARGET,
    R4_SYMBOLS_COUNT,
    R4_TRIAL_EXCLUDE_SYMBOLS,
    filter_r4_trial_symbols,
    is_r4_trial_excluded,
)


def test_soft80_accepted_residual_locked() -> None:
    assert R4_SYMBOLS_COUNT == 61
    assert R4_SOFT_TARGET == 80
    assert R4_HARD_CAP == 100
    assert R4_SOFT80_STATUS == "accepted_residual"
    assert R4_SYMBOLS_COUNT < R4_SOFT_TARGET
    assert R4_SYMBOLS_COUNT <= R4_HARD_CAP


def test_index_anchor_qfq_only_policy() -> None:
    assert R4_INDEX_ANCHOR == "510300.SH"
    assert R4_INDEX_REQUIRED_NAMESPACES == frozenset({"tushare_qfq"})
    assert "tushare_daily_basic" in R4_INDEX_OPTIONAL_NAMESPACES
    assert "tushare_moneyflow" in R4_INDEX_OPTIONAL_NAMESPACES


def test_trial_excludes_601989_keeps_others() -> None:
    assert is_r4_trial_excluded("601989")
    assert is_r4_trial_excluded("601989.SH")
    assert not is_r4_trial_excluded("600519.SH")
    assert not is_r4_trial_excluded("000001.SZ")
    pool = ["600519.SH", "601989.SH", "000001.SZ", "601989"]
    assert filter_r4_trial_symbols(pool) == ["600519.SH", "000001.SZ"]
    assert "601989" in R4_TRIAL_EXCLUDE_SYMBOLS
