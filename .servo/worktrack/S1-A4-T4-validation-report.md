---
title: "S1-A4-T4 Validation Report"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T17:25:00+08:00"
owner: "OceanEyeFF"
---

# S1-A4-T4 Validation Report

## Control Signal

- task_id: S1-A4-T4
- task_title: Validate and interpret per-horizon smoke result
- task_status: completed
- validation_result: blocked_by_data_confirmed
- recommended_next_action: S1-A4-T5 Produce gate evidence
- model_promotion_allowed: no

## Validation Commands

- `python -m json.tool .servo/worktrack/evidence/ic_report_oos_coverage_same_window_fastpilot_A4.json`
  - result: pass
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py`
  - result: `21 passed`
- `PYTHONPATH="src:." conda run -n "py311-private" python scripts/audit_ic_reports.py --reports output/reports/mainline_3510d/xgb_fastpilot_20260323.json output/reports/mainline_3510d/lstm_fastpilot_20260323.json --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4`
  - result: command pass; strict daily-CS readiness 0/2.
- `PYTHONPATH="src:." conda run -n "py311-private" python scripts/compare_ic_reports.py --reports output/reports/mainline_3510d/xgb_fastpilot_20260323.json output/reports/mainline_3510d/lstm_fastpilot_20260323.json --metric-source raw --monthly-source raw --daily-cs-mode off --check-protocol --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4_protocol`
  - result: expected failure; `xgb_fastpilot_20260323.json` lacks `evaluation_protocol`.

## Interpretation

- Same-window metadata is partially available: fastpilot XGB/LSTM reports share stock pool, dataset, evaluation window, and label mode.
- Strict same-window daily-CS smoke is not runnable from current artifacts because both reports lack OOS parquet paths.
- The historical XGB fastpilot report also lacks top-level `evaluation_protocol`, so strict protocol checking blocks before any model comparison.
- Per-horizon IC/RankIC metric fields exist in both fastpilot report JSON files, but without OOS parquet and protocol parity they are insufficient for accepted same-window smoke.
- The correct conclusion is `continue-research / blocked_by_data`, not `go` or `no-go`.

## Minimum Safe Next Step

- Produce or locate same-window OOS parquet for both fastpilot LSTM and XGB reports.
- Regenerate the XGB report through the WT-S1-A3-compliant writer, or create a verified adapter report with matching protocol fields and explicit OOS path.
- Re-run audit and strict compare commands only after both report/OOS preconditions are satisfied.

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none
- checker_relaxation: none
- commit_push_release: none

## Residual Risk

- A4 could not produce model comparison metrics because required OOS artifacts are absent.
- This Worktrack still provides useful gate evidence by preventing an unfair same-window comparison.
