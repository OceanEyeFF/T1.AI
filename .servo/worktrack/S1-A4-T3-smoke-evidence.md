---
title: "S1-A4-T3 Smoke / Blocked Evidence"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T17:15:00+08:00"
owner: "OceanEyeFF"
---

# S1-A4-T3 Smoke / Blocked Evidence

## Control Signal

- task_id: S1-A4-T3
- task_title: Run bounded smoke or produce blocked-by-data evidence
- task_status: completed
- result: blocked_by_data
- strict_lstm_xgb_daily_cs_smoke: not_runnable_with_current_artifacts
- recommended_next_action: S1-A4-T4 Validate and interpret per-horizon smoke result
- minimum_safe_next_input: same-window LSTM and XGBoost OOS parquet paths plus regenerated or adapted XGBoost report with top-level `evaluation_protocol`.

## Audit Evidence

- command: `PYTHONPATH="src:." conda run -n "py311-private" python scripts/audit_ic_reports.py --reports output/reports/mainline_3510d/xgb_fastpilot_20260323.json output/reports/mainline_3510d/lstm_fastpilot_20260323.json --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4`
- result: pass as audit command; audit verdict blocks strict daily-CS readiness.
- output_refs:
  - `.servo/worktrack/evidence/ic_report_oos_coverage_same_window_fastpilot_A4.json`
  - `.servo/worktrack/evidence/ic_report_oos_coverage_same_window_fastpilot_A4.md`
- summary:
  - total_reports: 2
  - oos_path_ready: 0
  - strict_daily_cs_raw_ready: 0
  - strict_daily_cs_calibrated_ready: 0
  - XGB issues: `missing_oos_path`
  - LSTM issues: `missing_oos_path`

## Protocol Failure Evidence

- command: `PYTHONPATH="src:." conda run -n "py311-private" python scripts/compare_ic_reports.py --reports output/reports/mainline_3510d/xgb_fastpilot_20260323.json output/reports/mainline_3510d/lstm_fastpilot_20260323.json --metric-source raw --monthly-source raw --daily-cs-mode off --check-protocol --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4_protocol`
- result: expected failure
- decisive_error: `ValueError: 协议一致性检查失败: 报告缺少 evaluation_protocol: xgb_fastpilot_20260323.json`
- interpretation: strict checker correctly blocks the historical fastpilot XGB report because it predates WT-S1-A3 contract output.

## Why Smoke Was Not Forced

- Running `compare_ic_reports.py --daily-cs-mode required` would fail for both reports because OOS parquet paths are absent.
- Disabling daily-CS and protocol checks would violate the A4 contract and could create misleading same-window claims.
- Using the `xgb_nextopen_baseline_quick8` OOS parquet would not provide an LSTM/XGBoost same-window pair and uses a different label protocol from the fastpilot reports.

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none
- checker_relaxation: none
- commit_push_release: none
