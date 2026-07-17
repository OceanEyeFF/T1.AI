# WT-INFRA-001-TQA deferred TODOs

## U-L3 — stock_basic 加载 + merge 接入 DataLake

**Status:** done (WT-INFRA-001.5 / 2026-07-17)

**Delivered:**
- Canonical local path: `{cache_dir}/meta/stock_basic.{csv,parquet}`
- `ashare_infra.lake.meta` helpers + `DataLake.load_stock_basic` /
  `load_symbol_lifecycle_map` / `with_stock_basic_meta` (fill-missing)
- Unit: `tests/unit/infra/test_datalake_stock_basic.py` (tradable parity with U-G1)

**Still out of scope:** network TuShare `stock_basic` pull (optional follow-up / R4)
