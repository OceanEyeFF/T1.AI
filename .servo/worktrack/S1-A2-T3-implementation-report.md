---
title: "WT-S1-A2 / S1-A2-T3 Implementation Report"
artifact_type: "worktrack-task-evidence"
milestone_id: "MS-S1-001"
worktrack_id: "WT-S1-A2"
task_id: "S1-A2-T3"
updated: "2026-06-16T14:28:06+08:00"
owner: "OceanEyeFF"
---

# WT-S1-A2 / S1-A2-T3 Implementation Report

## Control Signal

- task_id: S1-A2-T3
- task_status: completed
- implementation_status: completed
- runnable_path: yes for industry neutralization; size lane returns `blocked_by_data` when no size column is supplied.
- recommended_next_task: S1-A2-T4
- can_continue: true

## Implemented Surface

- `src/ashare_lab/evaluation/sanity_checks.py`
  - Added `neutralization_test`.
  - Added industry/group residualization by date and group.
  - Added size residualization by date using a one-factor least-squares residual on `[1, size]`.
  - Preserves existing shuffle/time-reverse/lag/random-label behavior.
- `scripts/run_sanity_checks.py`
  - Added `--neutralization-output`.
  - Added `--neutralization-horizons`.
  - Added `--group-map` / `--group-col`.
  - Added `--size-col`.
  - Emits a standalone `neutralization` JSON report from local OOS parquet.
- `tests/test_sanity_checks.py`
  - Added focused tests for industry residualization, size residualization, and OOS report blocked-by-data behavior.

## Scope Control

- No provider calls.
- No long training.
- No dependency changes.
- No production risk engine.
- No alpha_score promotion or model selection.
- No commit, push, release, or tag operation.

## Known Behavior

- Current quick8 XGB OOS reports contain prediction/label columns but no size column.
- With `data/symbol_sector_etf_map_quick8.csv`, industry neutralization can run locally.
- Without `--size-col`, the size lane is explicitly `blocked_by_data` and blocks promotion.
