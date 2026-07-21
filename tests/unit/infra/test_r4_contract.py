"""Unit tests for MS-R4 A1-bound DataLake factory."""

from __future__ import annotations

from pathlib import Path

from ashare_infra.lake.r4_contract import (
    R4_ADJUST_DEFAULT,
    R4_CACHE_ROOT,
    R4_PRIMARY_SOURCE,
    R4_STOCK_POOL_ID,
    R4_STOCK_POOL_VERSION,
    make_r4_datalake,
)


def test_make_r4_datalake_defaults(tmp_path: Path) -> None:
    lake = make_r4_datalake(cache_dir=tmp_path)
    assert lake.default_source == R4_PRIMARY_SOURCE == "tushare"
    assert lake.refresh is False
    assert lake.cache_dir == tmp_path
    assert R4_ADJUST_DEFAULT == "qfq"
    assert R4_STOCK_POOL_ID == "custom_research_liquidity_quality_v1"
    assert R4_STOCK_POOL_VERSION == "1"
    assert R4_CACHE_ROOT == Path("inputs/data/cache")


def test_make_r4_datalake_refresh_override(tmp_path: Path) -> None:
    lake = make_r4_datalake(cache_dir=tmp_path, refresh=True)
    assert lake.refresh is True
