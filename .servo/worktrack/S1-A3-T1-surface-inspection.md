---
title: "S1-A3-T1 Surface Inspection"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T15:20:00+08:00"
owner: "OceanEyeFF"
---

# S1-A3-T1 Surface Inspection

## Control Signal

- task_id: S1-A3-T1
- task_title: Inspect XGBoost report and checker surfaces
- task_status: completed
- scope_result: read-only local inspection completed
- implementation_started: no
- recommended_next_action: S1-A3-T2 Define minimal XGBoost report contract patch
- primary_finding: current XGBoost writer already has enough local metadata to emit protocol fields, but the live writer omits top-level `evaluation_protocol` and `comparison_panel`.
- blocked_by_data: no for writer patch; existing fastpilot XGB historical report lacks OOS parquet path, so retroactive daily-CS checking for that specific file remains blocked unless an OOS parquet is supplied.

## Dispatch Result

- selected_executor: current-carrier runtime fallback
- selected_executor_type: generic-worker-compatible local execution
- dedicated_skill_matched: no
- runtime_dispatch_mode: auto
- dispatch_policy_ref: docs/harness/foundations/dispatch-decision-policy.md
- delegation_attempted: no
- attempted_carrier: N/A
- carrier_decision: current-carrier synthesis
- fallback_reason: available multi-agent tool requires explicit user request to spawn sub-agents; task is tightly coupled to current dirty `.servo` artifacts and is a low-risk read-only inspection.
- dispatch_package_status: valid
- package_scope_judgment: bounded single inspection slice

## Writer Surfaces

- `scripts/run_xgboost_rolling_retrain_regime.py`
  - writes report at the final `out = {...}` block.
  - current output includes `experiment_metadata`, `config`, `raw_oos_metrics`, `calibrated_oos_metrics`, `delta_cal_minus_raw`, `weekly_logs`, and `monthly_logs`.
  - writes `oos_predictions_path` only when `--save-oos-parquet` is provided.
  - current parser already exposes `--stock-pool-id`, `--stock-pool-version`, `--evaluation-window-id`, `--dataset-id`, `--save-oos-parquet`, and report/config identifiers.
  - label mode is loaded from dataset metadata via `_load_label_mode(dataset_dir)`.
  - current OOS frame has `date`, `symbol`, `label_3d`, `label_5d`, `label_10d`, `pred_3d`, `pred_5d`, `pred_10d`, and calibrated `*_cal` prediction columns.
- `scripts/run_lstm_rolling_retrain_dim19_regime.py`
  - provides the nearest compatible pattern.
  - emits top-level `evaluation_protocol` with `signal_time_mode`, `execution_time_mode`, `label_mode`, `return_mode`, `cost_model`, and `daily_cs_mode`.
  - builds `comparison_panel` through `build_primary_trade_like_comparison_panel(oos, top_n=args.comparison_top_n)`.
  - writes `oos_predictions_path` when `--save-oos-parquet` is provided.

## Checker Surfaces

- `scripts/compare_ic_reports.py`
  - `--check-protocol` calls `check_protocol_consistency`.
  - strict protocol requires top-level `evaluation_protocol` as a dict.
  - required keys are `signal_time_mode`, `execution_time_mode`, `label_mode`, and `return_mode`.
  - single-report protocol check passes when these keys are present; multi-report check also requires identical values across reports.
  - daily-CS mode resolves OOS paths from top-level or `config` keys: `oos_predictions_path`, `oos_parquet_path`, or `oos_parquet`.
- `scripts/audit_ic_reports.py`
  - accepts the same OOS path aliases for audit surface discovery.
- `tests/test_compare_ic_reports.py`
  - already tests missing protocol, missing protocol keys, mismatch, and CLI `--check-protocol` failure cases.
- `tests/test_audit_ic_reports.py`
  - already tests OOS path discovery at top level.

## Existing Report Examples

- `output/reports/xgb_nextopen_baseline_quick8_20260309.json`
  - has top-level `evaluation_protocol`.
  - has `oos_predictions_path`.
  - does not have `comparison_panel`.
  - protocol uses `label_mode = next_open_to_open` and `return_mode = next_open_to_open`.
- `output/reports/mainline_3510d/xgb_fastpilot_20260323.json`
  - lacks top-level `evaluation_protocol`.
  - lacks `oos_predictions_path`.
  - lacks `comparison_panel`.
  - config already carries stock pool, dataset, evaluation window, and label mode metadata.
- `output/reports/mainline_3510d/lstm_fastpilot_20260323.json`
  - has top-level `evaluation_protocol`.
  - has `comparison_panel`.
  - lacks `oos_predictions_path` in the historical report, so daily-CS strict mode would still require a supplied OOS artifact.

## Missing Fields

- XGBoost live writer missing top-level `evaluation_protocol`.
- XGBoost live writer missing `comparison_panel`.
- XGBoost CLI missing `--comparison-top-n`, unlike LSTM.
- Historical XGB fastpilot report cannot be made daily-CS strict-compatible without its OOS parquet; this is a data artifact gap, not a writer-code blocker.

## Minimal Patch Recommendation

- Patch `scripts/run_xgboost_rolling_retrain_regime.py`, not `compare_ic_reports.py`.
- Add import and helper usage for `build_primary_trade_like_comparison_panel`.
- Add `--comparison-top-n` with the same default as LSTM.
- Emit top-level `evaluation_protocol` using:
  - `signal_time_mode = close`
  - `execution_time_mode = next_open`
  - `label_mode = label_mode`
  - `return_mode = label_mode`
  - `cost_model = none`
  - `daily_cs_mode = required`
- Emit top-level `comparison_panel` from the already assembled OOS frame.
- Keep `oos_predictions_path` behavior unchanged: explicit only when `--save-oos-parquet` is passed.
- Add focused tests that exercise a minimal report builder path or a small helper without running XGBoost training.

## Evidence Commands

- `rg -n "evaluation_protocol|comparison_panel|oos_predictions_path|save-oos|report|label_mode|execution_time|stock_pool|universe|metrics" scripts/run_xgboost_rolling_retrain_regime.py`
- `rg -n "evaluation_protocol|comparison_panel|oos_predictions_path|check-protocol|protocol|stock_pool|metrics" scripts/compare_ic_reports.py scripts/audit_ic_reports.py tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py`
- `rg -n "evaluation_protocol|comparison_panel|oos_predictions_path|trade_like|report" scripts/run_lstm_rolling_retrain_dim19_regime.py src/ashare_lab/evaluation`
- `python -c "... inspect selected report keys ..."`
- `find output -maxdepth 4 -type f \( -name "*.parquet" -o -name "*.json" \) | sort | rg "(oos|xgb|lstm|fastpilot|quick8|report)"`

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none
- commit_push_release: none
