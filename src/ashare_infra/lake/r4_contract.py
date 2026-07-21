"""MS-R4 A1-bound DataLake factory (cache-first TuShare primary).

Consumers should prefer ``make_r4_datalake`` for R4 lake work so defaults stay
aligned with ``WT-R4-A1-lake-source-contract`` (frozen_for_A2):

- primary source: tushare
- adjust: qfq
- cache_root: inputs/data/cache
- universe: custom_research_liquidity_quality_v1 @ 1 (61)
- history_start: 2023-01-01
- refresh: False (R1 audit reuse; A3 owns limited-live)
"""

from __future__ import annotations

from pathlib import Path

from ashare_infra.lake import DataLake

# Locked from WT-R4-A1 (frozen_for_A2)
R4_CONTRACT_ID = "MS-R4-001-lake-source-v0"
R4_PRIMARY_SOURCE = "tushare"
R4_ADJUST_DEFAULT = "qfq"
R4_CACHE_ROOT = Path("inputs/data/cache")
R4_HISTORY_START = "2023-01-01"
R4_STOCK_POOL_ID = "custom_research_liquidity_quality_v1"
R4_STOCK_POOL_VERSION = "1"
R4_SYMBOLS_COUNT = 61
R4_POOL_REGISTRY = Path("inputs/pools/research_liquidity_quality/")


def make_r4_datalake(
    cache_dir: Path | str | None = None,
    *,
    refresh: bool = False,
    tushare_token: str | None = None,
) -> DataLake:
    """Build a cache-first DataLake with R4/A1 defaults (TuShare primary, qfq)."""
    root = Path(cache_dir) if cache_dir is not None else R4_CACHE_ROOT
    return DataLake(
        cache_dir=root,
        default_source=R4_PRIMARY_SOURCE,  # type: ignore[arg-type]
        refresh=refresh,
        tushare_token=tushare_token,
    )


__all__ = [
    "R4_ADJUST_DEFAULT",
    "R4_CACHE_ROOT",
    "R4_CONTRACT_ID",
    "R4_HISTORY_START",
    "R4_POOL_REGISTRY",
    "R4_PRIMARY_SOURCE",
    "R4_STOCK_POOL_ID",
    "R4_STOCK_POOL_VERSION",
    "R4_SYMBOLS_COUNT",
    "make_r4_datalake",
]
