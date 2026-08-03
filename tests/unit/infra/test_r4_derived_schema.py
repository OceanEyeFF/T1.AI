"""WT-R4-A4-T1: derived layout/schema constants (zero live; no parquet build)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_infra.lake.r4_contract import (
    R4_CACHE_ROOT,
    R4_DERIVED_CONTRACT_ID,
    R4_DERIVED_DEFERRED_FAMILIES,
    R4_DERIVED_FAMILY_MOMENTUM,
    R4_DERIVED_FAMILY_TECHNICAL,
    R4_DERIVED_MINIMAL_FAMILIES,
    R4_DERIVED_MINIMAL_SET,
    R4_DERIVED_MOMENTUM_COLUMNS,
    R4_DERIVED_OPTIONAL_COLUMNS,
    R4_DERIVED_PART_FILENAME,
    R4_DERIVED_ROOT,
    R4_DERIVED_SOURCE_NAMESPACE,
    R4_DERIVED_TECHNICAL_COLUMNS,
    R4_HISTORY_START,
    r4_derived_part_path,
    r4_derived_required_columns,
    r4_derived_symbol_dir,
)


def test_derived_minimal_set_locked() -> None:
    assert R4_DERIVED_CONTRACT_ID == "MS-R4-001-derived-minimal-v0"
    assert R4_DERIVED_MINIMAL_SET == "M1_ret_rsi"
    assert R4_DERIVED_ROOT == Path("inputs/data/derived")
    assert R4_DERIVED_SOURCE_NAMESPACE == "tushare_qfq"
    assert R4_DERIVED_SOURCE_NAMESPACE.startswith("tushare_")
    assert R4_CACHE_ROOT == Path("inputs/data/cache")
    assert R4_HISTORY_START == "2023-01-01"


def test_derived_families_and_columns() -> None:
    assert R4_DERIVED_MINIMAL_FAMILIES == frozenset(
        {R4_DERIVED_FAMILY_MOMENTUM, R4_DERIVED_FAMILY_TECHNICAL}
    )
    assert R4_DERIVED_MOMENTUM_COLUMNS == (
        "date",
        "return_5d",
        "return_10d",
        "return_20d",
    )
    assert R4_DERIVED_TECHNICAL_COLUMNS == ("date", "rsi_14")
    assert "atr_14" in R4_DERIVED_OPTIONAL_COLUMNS
    assert "macd" in R4_DERIVED_DEFERRED_FAMILIES
    assert "market_state" in R4_DERIVED_DEFERRED_FAMILIES


def test_required_columns_helper() -> None:
    assert r4_derived_required_columns("momentum") == R4_DERIVED_MOMENTUM_COLUMNS
    assert r4_derived_required_columns("technical") == R4_DERIVED_TECHNICAL_COLUMNS
    with pytest.raises(ValueError, match="unknown derived family"):
        r4_derived_required_columns("macd")


def test_derived_path_helpers_mirror_cache_layout() -> None:
    root = Path("/tmp/r4-derived-test")
    sym = r4_derived_symbol_dir("momentum", "600519.SH", root=root)
    assert sym == root / "momentum" / "600519.SH"
    part = r4_derived_part_path("technical", "000001.SZ", 2024, root=root)
    assert part == root / "technical" / "000001.SZ" / "year=2024" / R4_DERIVED_PART_FILENAME
    # Default root uses contract constant (relative).
    default_part = r4_derived_part_path("momentum", "600519.SH", "2023")
    assert default_part == (
        R4_DERIVED_ROOT / "momentum" / "600519.SH" / "year=2023" / "part.parquet"
    )


def test_path_helpers_reject_empty() -> None:
    with pytest.raises(ValueError):
        r4_derived_symbol_dir("", "600519.SH")
    with pytest.raises(ValueError):
        r4_derived_part_path("momentum", "", 2024)
