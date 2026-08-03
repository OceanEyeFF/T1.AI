---
title: "WT-R4-A2 T2 Notes — cache-first DataLake bound to A1"
artifact_type: "task-run-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
task_id: "R4-A2-T2"
updated: "2026-07-21T09:50:00+08:00"
owner: "OceanEyeFF"
status: "completed"
---

# R4-A2-T2 — Cache-first DataLake path bound to A1 contract

## Control Signal

- task: R4-A2-T2
- r4_factory: `ashare_infra.lake.r4_contract.make_r4_datalake`
- defaults: tushare / qfq / `inputs/data/cache` / refresh=False
- pool_binding_constants: custom_research_liquidity_quality_v1@1 (61)
- ashare_exec: **excluded**
- live_pull: none
- blind_merge_develop: no（path-limited checkout + local edits）

## Delivered

| Item | Detail |
|------|--------|
| A1 factory | `src/ashare_infra/lake/r4_contract.py` |
| Consumer cutover | `dataset/builder.py`, `recommendation/validator.py` (TuShare adapter → make_r4) |
| Scripts | `run_backtest.py`, `run_sim_replay.py`, `generate_daily_recommendations.py`, `build_sequence_dataset.py` |
| Lab companions | `symbols.py`; `ashare_lab.sim` shims → infra.sim |
| Contract test | `tests/contract/infra/test_no_direct_load_or_fetch.py` |
| Unit tests | `test_dataset_builder_lake.py`, `test_r4_contract.py` |
| Config note | `inputs/configs/data_source.toml` documents R4 primary via factory（global default 仍 akshare） |

## DatasetConfig

- Default `source` changed to **`tushare`** (R4/A1 primary).
- When `source=="tushare"`, builder uses `make_r4_datalake`.

## Verification

```text
74 passed — DataLake units + r4_contract + builder_lake + no-direct contract
         + sources integration + stock_pool
```

## Explicit non-actions

- No `ashare_exec`
- No lake fill / live
- No blind `merge develop`
- Caps → `inputs/configs` still optional (T4)

## Next

- T3: disk/schema contract tests vs A1 inventory (pool 61; 510300 unavailable)
