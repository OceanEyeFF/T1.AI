# WT-INFRA-001-TQA deferred TODOs

## U-L3 — stock_basic 加载 + merge 接入 DataLake

**Status:** deferred (not implemented in Phase 1 DataLake)

**Current state:**
- Canonical lifecycle merge lives in `ashare_infra.guard.scope` / FetchGate override path
- Fixture helper: `tests.support.infra_a.load_stock_basic` / `symbol_lifecycle_map`
- `DataLake` has **no** `load_stock_basic` / meta API yet

**Follow-up:**
- Add `DataLake.load_stock_basic(cache_dir/meta/...)` thin wrapper
- Wire optional auto-merge into `DataScope` factory when meta missing
- Unit test: fixture CSV → lifecycle map → tradable matrix parity with U-G1

**Out of scope for TQA:** network TuShare `stock_basic` pull
