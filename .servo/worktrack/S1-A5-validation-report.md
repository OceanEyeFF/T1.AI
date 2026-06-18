---
title: "S1-A5 Validation Report"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T18:25:00+08:00"
owner: "OceanEyeFF"
---

# S1-A5 Validation Report

## Control Signal

- task_id: S1-A5-T2
- task_status: completed
- validation_result: pass
- recommended_next_action: S1-A5-T3 Produce gate evidence
- model_promotion_allowed: no

## Validation Commands

- `python -m json.tool .servo/worktrack/evidence/random_label_xgb_nextopen_quick8_WT-S1-A1.json`
  - result: pass
- `python -m json.tool .servo/worktrack/evidence/neutralization_xgb_nextopen_quick8_WT-S1-A2.json`
  - result: pass
- `python -m json.tool .servo/worktrack/evidence/ic_report_oos_coverage_same_window_fastpilot_A4.json`
  - result: pass
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py tests/test_sanity_checks.py`
  - result: `41 passed`

## Interpretation

- Referenced machine-readable evidence is parseable.
- Focused checker/report/sanity tests remain green.
- Final report conclusion remains `continue-research`; no model or `alpha_score` promotion is supported.

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none
- commit_push_release: none
