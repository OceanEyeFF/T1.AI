---
title: "WT-R4-A2 T4 Notes — cache-hit/as_of + caps promote"
artifact_type: "task-run-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
task_id: "R4-A2-T4"
updated: "2026-07-22T09:00:00+08:00"
owner: "OceanEyeFF"
status: "completed"
---

# R4-A2-T4 — Integration cache-hit/as_of + caps → configs

## Control Signal

- task: R4-A2-T4
- live_pull: none
- write_cache: none（仅 tmp_path 测用写入）
- caps_promoted: yes → `inputs/configs/tushare_rate_limits.toml`
- caps_values: rpm=180, daily_per_api=80000

## Delivered

| Item | Path |
|------|------|
| Caps config | `inputs/configs/tushare_rate_limits.toml` |
| Loader | `load_r4_rate_limits` / `r4_approved_rpm` / `r4_approved_daily_per_api` in `r4_contract.py` |
| Integration | `tests/integration/infra/test_r4_datalake_cache_as_of.py` |
| Unit | extended `tests/unit/infra/test_r4_contract.py` |

## Verification

```text
pytest integration/infra/test_r4_datalake_cache_as_of.py
     + unit/infra/test_r4_contract.py
     + contract/infra/test_r4_cache_schema_contract.py
     + contract/infra/test_no_direct_load_or_fetch.py
→ 23 passed
```

## Notes

- Caps apply to A3+ limited-live; A2 still zero-live.
- Cache-hit asserted by failing fetch monkeypatch under `make_r4_datalake(refresh=False)`.

## Next

- T5: Gate evidence + closeout
