---
title: "WT-R4-A3 T2 Notes — frequency-wall + resume"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
task_id: "R4-A3-T2"
updated: "2026-07-22T17:45:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# R4-A3-T2 — Frequency-wall pause + resume

## Control Signal

- task_id: R4-A3-T2
- status: **completed**
- live_pull: none
- token_committed: false
- module: src/ashare_infra/data/tushare_batch.py
- policy: concurrency=1; burst_pause_on_freq_wall=true; max_batch_symbols=50
- next: R4-A3-T3 limited-live (**requires explicit batch approve**)

## Delivered

| Item | Path |
|------|------|
| Batch runner | `src/ashare_infra/data/tushare_batch.py` |
| Unit tests | `tests/unit/infra/test_tushare_batch.py` |
| Contract | `tests/contract/infra/test_r4_batch_resume_contract.py` |

## Behavior

- `plan_batch` / `chunk_symbols`: ≤50 symbols per manifest (A1)
- `dry_run_batch` / `run_batch(dry_run=True)`: estimate + affordability; **no network**
- `run_batch`: serial executor (concurrency=1); on code/2002/频率 → `paused_freq_wall` + persist; no tight-loop
- Daily cap unaffordable / `TushareRateLimitExceeded` → `paused_daily_cap`
- `resume_batch`: continues pending jobs; leaves done jobs untouched
- Policy loaded from `tushare_rate_limits.toml` `[policy]` + approved caps

## Evidence

```text
pytest tests/unit/infra/test_tushare_batch.py \
       tests/contract/infra/test_r4_batch_resume_contract.py \
       tests/unit/infra/test_tushare_rate_limit.py \
       tests/contract/infra/test_r4_caps_enforce_contract.py -q
→ 19 passed
```

## Non-actions

- No live TuShare calls / no lake fill (T3)
- No soft80 expand (T4)
- No hygiene residuals (A3_Q3)
