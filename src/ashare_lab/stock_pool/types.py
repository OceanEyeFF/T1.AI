"""Types for stock-pool registry records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockPoolRecord:
    stock_pool_id: str
    stock_pool_version: str
    pool_family: str
    pool_label: str
    construction_method: str
    base_universe: str
    symbols_source: str
    symbols_count: int
    rebalance_frequency: str
    effective_start: str
    effective_end: str
    is_default: bool
    is_research_only: bool
    owner: str
    notes: str
    symbols_csv: str = ""
    registry_path: str = ""
