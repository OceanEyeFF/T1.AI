---
title: "S1-A1-T3 Implementation Report"
artifact_type: "worktrack-evidence"
worktrack_id: "WT-S1-A1"
milestone_id: "MS-S1-001"
task_id: "S1-A1-T3"
updated: "2026-06-12T14:58:00+08:00"
updated_by: "harness-skill"
---

# S1-A1-T3 Implementation Report

## Control Signal

- task_id: S1-A1-T3
- task_status: completed
- implementation_status: completed
- code_changes:
  - `src/ashare_lab/evaluation/sanity_checks.py`: added `random_label_test`.
  - `scripts/run_sanity_checks.py`: added optional random-label report generation for OOS parquet horizons.
  - `tests/test_sanity_checks.py`: added random-label unit and blocked-by-data coverage.
- smoke_evidence:
  - `.servo/worktrack/evidence/random_label_xgb_nextopen_quick8_WT-S1-A1.json`
  - `.servo/worktrack/evidence/sanity_xgb_nextopen_quick8_h5_WT-S1-A1.json`
- validation_result: `36 passed` for focused sanity/compare/audit tests.
- promotion_status: no model promotion; quick8 smoke is anti-cheat smoke only.
- recommended_next_task: S1-A1-T4
- blocker: N/A

## Implementation Detail

- `random_label_test` randomizes labels within each date and computes repeated Daily-CS IC against unchanged predictions.
- The CLI can emit a separate random-label JSON via `--random-label-output`.
- Multi-horizon OOS parsing supports `pred_{horizon}d` / `label_{horizon}d` for configured horizons.
- Missing required columns produce `blocked_by_data`.
- Overall verdict prioritizes `blocked_by_data` before `fail`, matching the S1-A1-T2 contract for mandatory horizons.

## Smoke Result

- command_ref: `.servo/worktrack/evidence/sanity_xgb_nextopen_quick8_h5_WT-S1-A1.json`
- random_label_report_ref: `.servo/worktrack/evidence/random_label_xgb_nextopen_quick8_WT-S1-A1.json`
- random_label_overall_verdict: pass
- random_label_horizons: 3, 5, 10
- interpretation: quick8 random-label smoke did not show fake-label IC persistence under the configured threshold, but this does not prove model usability or authorize promotion.
- residual_risk: standard sanity h5 smoke still failed time-reverse; historical A2 evidence remains not credible for promotion.

## Validation Evidence

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_sanity_checks.py`
- result: `17 passed`
- command: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_sanity_checks.py tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py`
- result: `36 passed`

## Policy Evidence

- no_long_training: true
- no_provider_calls: true
- no_dependency_changes: true
- no_destructive_cleanup: true
- no_commit_or_push: true
- no_release_or_version_action: true
- no_alpha_score_promotion: true
