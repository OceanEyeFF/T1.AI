---
title: "WT-R3-A3 Execution / Closeout"
artifact_type: "worktrack-closeout"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A3"
updated: "2026-07-14T15:15:00+08:00"
status: "completed"
---

# WT-R3-A3 Closeout

## Fixes

| ID | Change |
|----|--------|
| F1 | `inputs/pools/low_manipulation/config.toml`：`symbols_csv` → `low_manipulation/symbols.csv` |
| F1 | `registry._resolve_symbols_csv_path`：registry 相对路径优先，仓库相对路径 fallback |
| F2 | `build_sequence_dataset_market_state.py` 默认 `--stock-pool-registry-dir=inputs/pools` |
| both | `build_sequence_dataset*.py` resolve/export 使用 `stock_pool_registry_dir` 而非 `Path.cwd()` |

## Validation

- `pytest tests/test_stock_pool_registry.py` → 7 passed
- full suite → **397 passed**, 0 failed

## Residual / R4

- Defer R4 count: 0（与 A1 T2 结论一致）
- MS-R3 acceptance path: A1+A2+A3 complete pending programmer final acceptance
