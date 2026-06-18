---
title: "S1-A4-T2 Smoke Contract"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T17:05:00+08:00"
owner: "OceanEyeFF"
---

# S1-A4-T2 Smoke Contract

## Control Signal

- task_id: S1-A4-T2
- task_title: Define same-window smoke protocol or blocked-by-data criteria
- task_status: completed
- scope_result: bounded smoke/blocked contract defined
- recommended_next_action: S1-A4-T3 Run bounded smoke or produce blocked-by-data evidence
- strict_lstm_xgb_smoke_route: blocked_by_data unless same-window OOS parquet paths are supplied
- checker_relaxation_allowed: no

## Strict Smoke Requirements

- Reports must share:
  - `evaluation_protocol.signal_time_mode`
  - `evaluation_protocol.execution_time_mode`
  - `evaluation_protocol.label_mode`
  - `evaluation_protocol.return_mode`
  - stock pool identity
  - dataset/window identity
- Reports must expose valid OOS parquet paths through `oos_predictions_path`, `oos_parquet_path`, or `oos_parquet`.
- OOS parquet must contain raw required columns:
  - `date`, `symbol`, `label_5d`, `label_10d`, `pred_5d`, `pred_10d`
- For calibrated strict smoke, OOS parquet must additionally contain:
  - `pred_5d_cal`, `pred_10d_cal`
- Per-horizon 3d evidence must remain separately visible in the report metrics or a supplemental evidence table; aggregate `alpha_score` cannot replace horizon-level interpretation.

## Bounded Commands

- OOS coverage audit:
  - `PYTHONPATH="src:." conda run -n "py311-private" python scripts/audit_ic_reports.py --reports <xgb_report> <lstm_report> --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4`
- Strict raw daily-CS comparison, only if audit passes:
  - `PYTHONPATH="src:." conda run -n "py311-private" python scripts/compare_ic_reports.py --reports <xgb_report> <lstm_report> --metric-source raw --monthly-source raw --daily-cs-mode required --check-protocol --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4_raw`
- Strict calibrated daily-CS comparison, only if audit passes:
  - `PYTHONPATH="src:." conda run -n "py311-private" python scripts/compare_ic_reports.py --reports <xgb_report> <lstm_report> --metric-source calibrated --monthly-source calibrated --daily-cs-mode required --check-protocol --output-dir .servo/worktrack/evidence --tag same_window_fastpilot_A4_calibrated`

## Blocked-By-Data Criteria

- Return `blocked_by_data` instead of forcing comparison when:
  - either report lacks an OOS parquet path;
  - either OOS parquet file is missing or empty;
  - either OOS parquet lacks required daily-CS columns;
  - reports lack required top-level protocol fields;
  - protocol fields mismatch;
  - stock pool or evaluation window metadata mismatch;
  - only one model has suitable OOS evidence.

## Minimum Safe Next Input

- A same-window LSTM OOS parquet and XGBoost OOS parquet for the fastpilot window.
- Matching top-level `evaluation_protocol` fields in both reports.
- Matching stock pool, dataset/window identity, and label mode.
- No long training or provider calls inside this Worktrack unless separately approved.

## Interpretation Rules

- `pass`: bounded commands run locally and produce parseable audit/compare evidence, or blocked-by-data evidence precisely names missing inputs and preserves protocol integrity.
- `blocked`: required local evidence cannot be produced and the missing input cannot be named precisely.
- `fail`: comparison is runnable and produces evidence that contradicts the smoke acceptance criteria.

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none
- checker_relaxation: none
- commit_push_release: none
