"""Smoke-ish registry contract checks for research_liquidity_quality pool."""

from __future__ import annotations

from pathlib import Path

from ashare_lab.stock_pool import (
    export_stock_pool_artifacts,
    get_stock_pool_record,
    resolve_stock_pool_symbols,
)


def test_research_liquidity_quality_export_roundtrip(tmp_path: Path) -> None:
    registry_root = Path("inputs/pools")
    record = get_stock_pool_record(
        registry_root,
        stock_pool_id="custom_research_liquidity_quality_v1",
        stock_pool_version="1",
    )
    symbols = resolve_stock_pool_symbols(record, registry_root=registry_root)
    assert 20 <= len(symbols) <= 100
    assert len(symbols) == record.symbols_count
    assert record.is_research_only is True

    artifacts = export_stock_pool_artifacts(
        record, output_dir=tmp_path, registry_root=registry_root
    )
    assert artifacts["symbols_csv"].exists()
    assert artifacts["metadata_json"].exists()
    exported = artifacts["symbols_csv"].read_text(encoding="utf-8").strip().splitlines()
    assert exported[0] == "symbol"
    assert len(exported) - 1 == len(symbols)


def test_strategy_pools_export_dir_present() -> None:
    base = Path(
        "src/ashare_lab/stock_pool/research_liquidity_quality/pools/"
        "custom_research_liquidity_quality_v1/1"
    )
    assert (base / "symbols.csv").exists()
    assert (base / "metadata.json").exists()
    assert (base / "config.toml").exists()
