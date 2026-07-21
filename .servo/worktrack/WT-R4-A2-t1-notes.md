---
title: "WT-R4-A2 T1 Notes — scoped ashare_infra bring-up"
artifact_type: "task-run-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
task_id: "R4-A2-T1"
updated: "2026-07-20T22:30:00+08:00"
owner: "OceanEyeFF"
status: "completed"
---

# R4-A2-T1 — Scoped `ashare_infra` / DataLake bring-up

## Control Signal

- task: R4-A2-T1
- method: path-limited `git checkout develop -- <paths>`（**not** `merge develop`）
- ashare_exec: **excluded**（未引入；清理了 tip 上无追踪 ghost 目录）
- DataLake_importable: **yes**
- live_pull: none
- cache_writes: none（仅测用 tmp fixtures）

## Brought from `develop`

| Path | Role |
|------|------|
| `src/ashare_infra/**` (29 files) | lake + data + guard + sim + utils |
| `src/ashare_lab/data/**` | shim → `ashare_infra.data` |
| `tests/unit/infra/test_datalake*.py` (+ `.md`) | DataLake unit |
| `tests/support/infra_a.py` | fixture helpers |
| `tests/fixtures/infra_a/**` | stock_basic / bars fixtures |
| `tests/integration/sources/test_tushare_source.py` | align qfq full-span refetch expectation |
| `pyproject.toml` | `packages.find` include `ashare_lab*` + `ashare_infra*`（**不含** `ashare_exec*`） |

## Explicitly NOT brought

- `src/ashare_exec/**`
- Phase 2 consumer cutover（`builder.py` / `validator.py` / scripts → DataLake）→ T2
- `tests/contract/infra/test_no_direct_load_or_fetch.py` → T2/T4（tip 仍经 `ashare_lab.data` 引用 `load_or_fetch_*`）
- Blind `git merge develop`

## Verification

```text
from ashare_infra.lake import DataLake  # OK
ashare_lab.data.tushare_source → ashare_infra.data.tushare_source  # shim OK

pytest tests/unit/infra/test_datalake*.py  → 23 passed
pytest tests/integration/sources/          → 23 passed
pytest tests/unit/stock_pool/ + above      → 47 passed (combined earlier run)
```

## Residual / next

- T2: bind cache-first path to A1 contract + consumer cutover surfaces as needed
- Caps promote still optional T4
- soft80 / 510300 residuals unchanged
