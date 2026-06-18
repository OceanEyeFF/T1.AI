---
title: "WT-S1-A2 / S1-A2-T4 Validation Report"
artifact_type: "worktrack-task-evidence"
milestone_id: "MS-S1-001"
worktrack_id: "WT-S1-A2"
task_id: "S1-A2-T4"
updated: "2026-06-16T14:28:06+08:00"
owner: "OceanEyeFF"
---

# WT-S1-A2 / S1-A2-T4 Validation Report

## Control Signal

- task_id: S1-A2-T4
- task_status: completed
- validation_status: pass
- decisive_result: focused tests pass; neutralization smoke emits machine-readable evidence.
- recommended_next_task: S1-A2-T5
- can_continue: true

## Validation Commands

- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_sanity_checks.py`
  - result: `20 passed`
- `PYTHONPATH="src:." conda run -n "py311-private" python scripts/run_sanity_checks.py --oos-parquet "output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet" --neutralization-output ".servo/worktrack/evidence/neutralization_xgb_nextopen_quick8_WT-S1-A2.json" --group-map "data/symbol_sector_etf_map_quick8.csv" --group-col "sector_hint" --neutralization-horizons "3,5,10" --horizon 5 --method pearson`
  - result: neutralization JSON written successfully.
  - note: command also runs the existing h5 sanity check; that retained prior time-reverse fail behavior.
- `python -m json.tool ".servo/worktrack/evidence/neutralization_xgb_nextopen_quick8_WT-S1-A2.json"`
  - result: pass
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_sanity_checks.py`
  - result: `39 passed`

## Neutralization Smoke Result

- evidence_ref: .servo/worktrack/evidence/neutralization_xgb_nextopen_quick8_WT-S1-A2.json
- input_path: output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet
- group_map_path: data/symbol_sector_etf_map_quick8.csv
- overall_verdict: blocked_by_data
- promotion_blocked: true

| horizon | baseline IC | baseline RankIC | industry-neutral IC | industry-neutral RankIC | industry status | size status |
|---:|---:|---:|---:|---:|---|---|
| 3 | -0.035745 | -0.037201 | -0.076948 | -0.080516 | pass | blocked_by_data |
| 5 | 0.081738 | 0.081524 | -0.168289 | -0.165457 | pass | blocked_by_data |
| 10 | 0.045301 | 0.039199 | -0.039870 | -0.057512 | pass | blocked_by_data |

## Interpretation

- Industry lane is runnable and shows that the positive 5d/10d baseline IC does not survive this quick8 industry residual smoke.
- Size lane is blocked because the current XGB OOS parquet does not include a size column.
- This is not model promotion evidence. It is a blocking / continue-research anti-cheat result for the current smoke input.
