---
title: "WT-R4-A4 T1 Notes"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
task_id: "R4-A4-T1"
updated: "2026-07-23T20:45:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# WT-R4-A4-T1 — Derived layout + schema contract

## Control Signal

```yaml
status: completed
live_pull: none
selected_next: R4-A4-T2
deliverable: A4-D1
schema_id: MS-R4-001-derived-minimal-v0
freeze_state: frozen_for_T2
```

## Done

| Item | Path / note |
|------|-------------|
| Constants + path helpers | `src/ashare_infra/lake/r4_contract.py` (`R4_DERIVED_*`) |
| README | `inputs/data/derived/README.md` |
| Schema draft | `.servo/worktrack/WT-R4-A4-derived-schema.md` |
| Unit tests | `tests/unit/infra/test_r4_derived_schema.py` |
| Contract tests | `tests/contract/infra/test_r4_derived_schema_contract.py` |

## Locked (from Init A4_Q*)

- **A4_Q1** M1: `momentum` = return_5d/10d/20d；`technical` = rsi_14；atr optional；MACD/Bollinger/market_state deferred
- **A4_Q2** `inputs/data/derived/{family}/{ts_code}/year=YYYY/part.parquet`
- **A4_Q5** zero live — T1 无 TuShare 调用、无 parquet 写入

## Explicit non-goals (this task)

- Builder / parquet materialization → **T2**
- Load API on DataLake → **T3**
- AO-O hygiene → **T4**
- QA report → **T5**

## Test Evidence

```text
pytest tests/unit/infra/test_r4_derived_schema.py \
       tests/contract/infra/test_r4_derived_schema_contract.py -q
```

## Next

- **R4-A4-T2**：cache-only builder → write derived parts（仍零 live）
