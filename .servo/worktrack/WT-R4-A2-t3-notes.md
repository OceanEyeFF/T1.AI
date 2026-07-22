---
title: "WT-R4-A2 T3 Notes — disk/schema contract tests"
artifact_type: "task-run-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
task_id: "R4-A2-T3"
updated: "2026-07-21T09:55:00+08:00"
owner: "OceanEyeFF"
status: "completed"
---

# R4-A2-T3 — Disk/schema contract tests vs A1 inventory/schema

## Control Signal

- task: R4-A2-T3
- test_module: `tests/contract/infra/test_r4_cache_schema_contract.py`
- policy: read-only cache + pool; skip if cache root absent
- live_pull: none
- write_cache: none
- ashare_exec: excluded

## Assertions covered

| Check | Result |
|-------|--------|
| Pool binding constants (v1 / 61 / history_start) | pass |
| Soft80 residual (61 < 80) | pass (documented) |
| Pool ∩ qfq / daily_basic / moneyflow = 61/61 | pass |
| `510300.SH` zero parts | pass |
| On-disk required columns (qfq / basic / moneyflow) | pass |
| `year=` partition matches row `date` year | pass |
| Sample date_min ≥ 2023-01-01 | pass |
| bare ↔ ts_code join keys | pass |

## Verification

```text
pytest tests/contract/infra/test_r4_cache_schema_contract.py -q  → 11 passed
```

## Next

- T4: cache-hit / as_of integration polish + optional caps→configs promote
