---
title: "S1-A4-T1 Artifact Inspection"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T16:55:00+08:00"
owner: "OceanEyeFF"
---

# S1-A4-T1 Artifact Inspection

## Control Signal

- task_id: S1-A4-T1
- task_title: Inspect same-window report and OOS availability
- task_status: completed
- scope_result: read-only local inspection completed
- implementation_started: no
- recommended_next_action: S1-A4-T2 Define same-window smoke protocol or blocked-by-data criteria
- primary_finding: existing fastpilot LSTM/XGBoost reports share stock pool, dataset, evaluation window, and label mode metadata, but they do not both satisfy strict report/OOS requirements.
- strict_lstm_xgb_daily_cs_feasibility: blocked_by_data
- blocked_by_data_reason: fastpilot LSTM and XGB historical reports lack `oos_predictions_path`; XGB fastpilot also lacks top-level `evaluation_protocol` because it predates WT-S1-A3.

## Dispatch Result

- selected_executor: current-carrier runtime fallback
- selected_executor_type: generic-worker-compatible local execution
- dedicated_skill_matched: no
- runtime_dispatch_mode: auto
- delegation_attempted: no
- attempted_carrier: N/A
- carrier_decision: current-carrier synthesis
- fallback_reason: available multi-agent tool requires explicit user request to spawn sub-agents; task is a low-risk read-only inspection tied to current Servo artifacts.

## Candidate Report Findings

- `output/reports/mainline_3510d/xgb_fastpilot_20260323.json`
  - stock_pool_id: `custom_quick8`
  - stock_pool_version: `v1`
  - evaluation_window_id: `fixed_20230101_20250701`
  - dataset_id: `seq_quick8_53d_20230101_20260305`
  - label_mode: `close_to_close`
  - evaluation_protocol: missing
  - oos_predictions_path: missing
  - raw metrics include 3d/5d/10d IC and RankIC fields.
- `output/reports/mainline_3510d/lstm_fastpilot_20260323.json`
  - stock_pool_id: `custom_quick8`
  - stock_pool_version: `v1`
  - evaluation_window_id: `fixed_20230101_20250701`
  - dataset_id: `seq_quick8_53d_20230101_20260305`
  - label_mode: `close_to_close`
  - evaluation_protocol: present and compatible with shared checker keys.
  - comparison_panel: present
  - oos_predictions_path: missing
  - raw metrics include 3d/5d/10d IC and RankIC fields.
- `output/reports/xgb_nextopen_baseline_quick8_20260309.json`
  - evaluation_protocol: present, but uses `next_open_to_open`.
  - oos_predictions_path: present.
  - OOS parquet shape: 952 rows, 11 columns.
  - OOS date range: 2025-07-28 to 2026-01-20.
  - OOS symbols: 8.
  - OOS columns include required raw/calibrated 5d/10d columns and also 3d columns.

## Checker Feasibility

- `scripts/audit_ic_reports.py` requires each strict report to expose an OOS parquet path and required raw/calibrated OOS columns.
- `scripts/compare_ic_reports.py --daily-cs-mode required` fails when `oos_predictions_path` is absent.
- `scripts/compare_ic_reports.py --check-protocol` fails when top-level `evaluation_protocol` is absent or mismatched.
- Current fastpilot LSTM/XGB pair cannot enter strict daily-CS comparison without OOS parquet artifacts.
- Current fastpilot XGB historical report also needs either regeneration through the WT-S1-A3 writer path or a verified non-mutating adapter report for protocol fields.

## Minimal Next-Input Requirement

- Strict same-window LSTM/XGB smoke requires:
  - LSTM OOS parquet for the fastpilot window or a bounded regenerated smoke report with OOS path.
  - XGB OOS parquet for the same window.
  - top-level `evaluation_protocol` in both reports with matching strict keys.
  - matching stock pool, dataset/window identity, and label mode.
- Without those inputs, WT-S1-A4 should produce blocked-by-data evidence rather than force an incompatible comparison.

## Evidence Commands

- `python -c "... inspect selected report protocol/config/OOS keys ..."`
- `find output/reports -maxdepth 3 -type f | sort | rg "(xgb|lstm|oos|fastpilot|quick8)"`
- `PYTHONPATH="src:." conda run -n "py311-private" python -c "... inspect OOS parquet shape/columns/date range ..."`
- `sed -n '320,365p' scripts/compare_ic_reports.py`
- `sed -n '1,130p' scripts/audit_ic_reports.py`

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none
- commit_push_release: none
