"""MS-R4 / WT-R4-A4-T1: derived layout contract (constants; parquet optional until T2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_infra.lake.r4_contract import (
    R4_DERIVED_CONTRACT_ID,
    R4_DERIVED_MINIMAL_FAMILIES,
    R4_DERIVED_MINIMAL_SET,
    R4_DERIVED_MOMENTUM_COLUMNS,
    R4_DERIVED_ROOT,
    R4_DERIVED_SOURCE_NAMESPACE,
    R4_DERIVED_TECHNICAL_COLUMNS,
    R4_HISTORY_START,
    R4_STOCK_POOL_ID,
    R4_STOCK_POOL_VERSION,
    r4_derived_part_path,
    r4_derived_required_columns,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DERIVED_ROOT = REPO_ROOT / R4_DERIVED_ROOT
DERIVED_README = DERIVED_ROOT / "README.md"


@pytest.mark.contract
def test_derived_contract_constants_bound_to_pool() -> None:
    assert R4_DERIVED_CONTRACT_ID == "MS-R4-001-derived-minimal-v0"
    assert R4_DERIVED_MINIMAL_SET == "M1_ret_rsi"
    assert R4_DERIVED_SOURCE_NAMESPACE == "tushare_qfq"
    assert R4_HISTORY_START == "2023-01-01"
    assert R4_STOCK_POOL_ID == "custom_research_liquidity_quality_v1"
    assert R4_STOCK_POOL_VERSION == "1"
    assert R4_DERIVED_MINIMAL_FAMILIES == frozenset({"momentum", "technical"})
    assert r4_derived_required_columns("momentum") == R4_DERIVED_MOMENTUM_COLUMNS
    assert r4_derived_required_columns("technical") == R4_DERIVED_TECHNICAL_COLUMNS


@pytest.mark.contract
def test_derived_root_readme_documents_layout() -> None:
    assert DERIVED_ROOT.is_dir(), f"missing derived root: {DERIVED_ROOT}"
    assert DERIVED_README.is_file(), f"missing derived README: {DERIVED_README}"
    text = DERIVED_README.read_text(encoding="utf-8")
    assert "year={YYYY}/part.parquet" in text or "year={YYYY}" in text
    assert "momentum" in text
    assert "rsi_14" in text
    assert "return_5d" in text
    assert "零 live" in text or "zero live" in text.lower() or "refresh=False" in text


@pytest.mark.contract
def test_derived_path_formula_stable() -> None:
    p = r4_derived_part_path("momentum", "600519.SH", 2024)
    assert str(p).replace("\\", "/") == (
        "inputs/data/derived/momentum/600519.SH/year=2024/part.parquet"
    )


@pytest.mark.contract
def test_derived_parquet_optional_until_t2() -> None:
    """T1 freezes layout only; empty derived tree (aside from README) is OK."""
    if not DERIVED_ROOT.is_dir():
        pytest.skip("derived root missing")
    parts = list(DERIVED_ROOT.glob("*/*/year=*/part.parquet"))
    # No assertion that parts exist — T2 builds them.
    assert isinstance(parts, list)
