---
title: "WT-R4-A4 T3 Notes"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
task_id: "R4-A4-T3"
updated: "2026-07-24T09:40:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# WT-R4-A4-T3 — Reproducible load API + Arch-v1 tests

## Control Signal

```yaml
status: completed
live_pull: none
selected_next: R4-A4-T4
deliverable: A4-D3
```

## Done

| Item | Path / note |
|------|-------------|
| DataLake load API | `load_derived` / `load_derived_minimal` / `load_scope_derived` + `derived_root` |
| Factory | `make_r4_datalake(..., derived_root=R4_DERIVED_ROOT)` |
| Unit | `tests/unit/infra/test_r4_derived_load.py` |
| Contract | `tests/contract/infra/test_r4_derived_load_contract.py` |
| Integration | `tests/integration/infra/test_r4_derived_load_integration.py` |
| README | `inputs/data/derived/README.md` documents load surface |

## Semantics

- **Filesystem only：** reads `inputs/data/derived/{family}/{ts_code}/year=*/part.parquet`
- **Zero live：** never calls `fetch_tushare_*`; missing parts → empty schema frame
- **Reproducible：** identical path → identical frame; columns = `r4_derived_required_columns` (sans date index)
- **as_of / start-end：** same temporal semantics as `load_daily_bars`

## Test Evidence

```text
pytest tests/unit/infra/test_r4_derived_load.py \
       tests/contract/infra/test_r4_derived_load_contract.py \
       tests/integration/infra/test_r4_derived_load_integration.py -q
→ 12 passed
```

## Next

- **R4-A4-T4**：AO-O1 allowlist + AO-O2 dataset_builder tests (+ AO-O3 doc)
