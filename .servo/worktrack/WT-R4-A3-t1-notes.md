---
title: "WT-R4-A3 T1 Notes — caps enforce on fetch"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
task_id: "R4-A3-T1"
updated: "2026-07-22T14:54:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# R4-A3-T1 — Caps enforce on TuShare fetch path

## Control Signal

- task_id: R4-A3-T1
- status: **completed**
- live_pull: none
- token_committed: false
- caps_source: inputs/configs/tushare_rate_limits.toml via r4_approved_*
- enforce_module: src/ashare_infra/data/tushare_rate_limit.py
- wired_into: fetch_tushare_daily_bars / daily_basic / moneyflow / adj_factor
- next: R4-A3-T2 (frequency-wall + resume; still zero live until T3 approve)

## Delivered

| Item | Path |
|------|------|
| Limiter | `src/ashare_infra/data/tushare_rate_limit.py` |
| Wire | `src/ashare_infra/data/tushare_source.py` (`acquire_tushare_call` before each pro.*) |
| Unit tests | `tests/unit/infra/test_tushare_rate_limit.py` |
| Contract | `tests/contract/infra/test_r4_caps_enforce_contract.py` |

## Behavior

- RPM spacing: `min_interval = 60 / r4_approved_rpm()` (180 → ~0.333s)
- Daily budget: per `api_name`, Asia/Shanghai calendar day, cap `r4_approved_daily_per_api()` (80000)
- Exceed daily → `TushareRateLimitExceeded` (stop; no tight-loop)
- `dry_run=True` checks budget without consuming / sleeping
- Process singleton + injectables for tests

## Evidence

```text
pytest tests/unit/infra/test_tushare_rate_limit.py \
       tests/contract/infra/test_r4_caps_enforce_contract.py \
       tests/unit/infra/test_r4_contract.py -q
→ 13 passed

(+ A2 regression subset including new tests → 38 passed)
```

## Non-actions

- No live TuShare calls
- No frequency-wall resume manifests (T2)
- No cache writes / lake fill (T3)
- No hygiene residuals (A3_Q3)
