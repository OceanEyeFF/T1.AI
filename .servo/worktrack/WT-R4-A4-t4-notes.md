---
title: "WT-R4-A4 T4 Notes"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
task_id: "R4-A4-T4"
updated: "2026-07-24T14:20:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# WT-R4-A4-T4 — AO-O hygiene (O1/O2 + O3 doc)

## Control Signal

```yaml
status: completed
live_pull: none
selected_next: R4-A4-T5
deliverable: A4-D4-hygiene
ao_o4: deferred_optional
```

## Done

| ID | Action | Path |
|----|--------|------|
| **AO-O1** | 收窄 no-direct allowlist：去掉 `ashare_infra.data`，仅保留 `ashare_infra.lake` | `tests/contract/infra/test_no_direct_load_or_fetch.py` |
| **AO-O2** | 修复 dataset_builder 旧测：akshare fixture 显式 `source="akshare"`；tushare/odp 改 monkeypatch `DataLake.load_daily_bars` | `tests/integration/dataset/test_dataset_builder.py` |
| **AO-O3** | 文档化 `data_source.toml` 双轨 vs `make_r4_datalake` / `DatasetConfig.source` | `inputs/configs/data_source.toml` |
| **AO-O4** | AST 合同补强 | **deferred**（optional；现有 no-direct + AO-R1 足够） |

## Test Evidence

```text
pytest tests/integration/dataset/test_dataset_builder.py \
       tests/contract/infra/test_no_direct_load_or_fetch.py \
       tests/unit/lab/test_dataset_builder_lake.py -q
→ 23 passed
```

## Non-Goals

- F1/F2/F4 不修代码（T1–T3 review residual）
- soft80 / 510300 / 601989 不重开
- 无 live / 无训 / 无 Phase4

## Next

- **R4-A4-T5**：QA report + consistency + Gate/Close packet
