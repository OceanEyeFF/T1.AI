---
title: "WT-R4-A4 T2 Notes"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
task_id: "R4-A4-T2"
updated: "2026-07-23T20:55:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# WT-R4-A4-T2 — Minimal derived builder (cache → derived)

## Control Signal

```yaml
status: completed
live_pull: none
selected_next: R4-A4-T3
deliverable: A4-D2
local_materialization: pool_61_built
```

## Done

| Item | Path / note |
|------|-------------|
| IO helpers | `src/ashare_infra/lake/r4_derived_io.py` |
| Builder | `src/ashare_lab/derived/builder.py`（复用 `Return5/10/20D` + `RSI(14)`） |
| Unit tests | `tests/unit/lab/test_r4_derived_builder.py` |
| Integration | `tests/integration/lab/test_r4_derived_builder_integration.py` |
| gitignore | `inputs/data/derived/**/year=*/`（parquet 可重建） |

## Semantics

- **Cache-only：** `read_r4_qfq_cache` → 无 `fetch_tushare_*`；缺 cache 则 `skipped_empty_cache`
- **No second truth：** `compute_r4_minimal_families` 直接调用 lab features
- **Layout：** T1 冻结路径；`write_r4_derived_parts` 按 year 落盘

## Local evidence (optional materialization)

```text
build_r4_derived_batch(pool_61) → n_built=61, n_skipped=0, parts≈486
(zero live; from inputs/data/cache/tushare_qfq)
```

## Test Evidence

```text
pytest tests/unit/lab/test_r4_derived_builder.py \
       tests/integration/lab/test_r4_derived_builder_integration.py \
       tests/unit/infra/test_r4_derived_schema.py -q
→ 11 passed
```

## Next

- **R4-A4-T3**：reproducible load API + Arch-v1 tests
