---
title: "WT-S1-A2 / S1-A2-T1 Surface Inspection"
artifact_type: "worktrack-task-evidence"
milestone_id: "MS-S1-001"
worktrack_id: "WT-S1-A2"
task_id: "S1-A2-T1"
updated: "2026-06-16T09:16:47+08:00"
owner: "OceanEyeFF"
---

# WT-S1-A2 / S1-A2-T1 Surface Inspection

## Control Signal

- task_id: S1-A2-T1
- task_status: completed
- task_scope: read-only local inspection of neutralization inputs and reusable IC / report surfaces.
- implementation_started: false
- recommended_next_task: S1-A2-T2
- recommended_next_task_title: Define minimal neutralization evidence contract
- can_continue: true
- blocker: none for contract design; market-cap neutralization may require blocked-by-data handling if using current XGB OOS reports.

## Dispatch Execution

- selected_executor: generic-worker current-carrier runtime fallback
- selected_executor_type: current-carrier
- dedicated_skill_matched: no
- runtime_dispatch_mode: auto
- dispatch_policy_ref: docs/harness/foundations/dispatch-decision-policy.md
- fallback_reason: no stable SubAgent dispatch shell is exposed in this runtime; task is read-only, low-risk, and tightly scoped.
- delegation_attempted: no
- attempted_carrier: generic-worker task instruction via current carrier
- carrier_decision: current-carrier runtime fallback

## Inspected Surfaces

### IC / RankIC And Report Evaluation

- `src/ashare_lab/evaluation/metrics.py`
  - `calculate_daily_cs_ic(predictions, labels, method)` already computes daily cross-sectional Pearson/Spearman IC on `(date, symbol)` MultiIndex.
  - `summarize_daily_cs(daily_ic)` is already used by sanity checks.
- `src/ashare_lab/evaluation/sanity_checks.py`
  - Existing anti-cheat helpers are compatible with a neutralization helper if it outputs aligned prediction/label Series.
- `scripts/run_sanity_checks.py`
  - Existing `--oos-parquet` loading path expects `date`, `symbol`, `pred_{h}d`, `label_{h}d`.
  - Random-label output already introduced a per-horizon machine-readable contract that can be mirrored by neutralization.
- `scripts/compare_ic_reports.py`
  - `_resolve_oos_path` recognizes `oos_predictions_path`, `oos_parquet_path`, and `oos_parquet`.
  - `_daily_cs_from_oos` currently computes 5d/10d daily-CS metrics from OOS parquet; it does not neutralize by group or size.
- `scripts/audit_ic_reports.py`
  - Strict OOS audit checks required OOS parquet columns but has no neutralization lane.

### Local OOS Prediction / Label Inputs

- `output/reports/xgb_nextopen_baseline_quick8_20260309.json`
  - Contains `oos_predictions_path` pointing to `output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet`.
  - Contains `evaluation_protocol` with `label_mode: next_open_to_open` and `primary_horizons: [5, 10]`.
- `output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet`
  - Columns include `date`, `symbol`, `label_3d`, `label_5d`, `label_10d`, `pred_3d`, `pred_3d_cal`, `pred_5d`, `pred_5d_cal`, `pred_10d`, `pred_10d_cal`.
  - Row count observed: 952.
  - Does not include industry, sector, `total_mv`, `circ_mv`, `total_mv_log`, `circ_mv_log`, or `float_share_ratio`.
- `output/reports/xgb_d1_close_candidate_quick8_20260309_oos.parquet`
  - Contains the same 3d/5d/10d prediction and label columns plus 1d columns.
  - Does not include industry or market-cap fields.
- `output/reports/mainline_3510d/xgb_fastpilot_20260323.json`
  - Has metric blocks but no `evaluation_protocol` and no OOS parquet path.
- `output/reports/mainline_3510d/lstm_fastpilot_20260323.json`
  - Has `evaluation_protocol` and `daily_cs`, but no OOS parquet path.

### Industry / Sector Inputs

- `data/symbol_sector_etf_map_quick8.csv`
  - Columns: `symbol`, `etf_ts_code`, `sector_hint`.
  - Covers the 8-symbol quick8 universe.
  - Can be joined to quick8 OOS parquet by normalized 6-digit `symbol`.
  - Suitable for a minimal industry-group neutralization smoke on quick8 OOS reports.
- `src/ashare_lab/stock_pool/registry.py`
  - Supports stock pool families `sector_single_*`, `sector_corr_*`, and `sector_anti_corr_*`.
  - This is stock-pool metadata, not a per-symbol industry classification surface by itself.
- `docs/modules/stock_pool_registry_baseline_20260311.md`
  - Documents `theme_or_sector` and sector pool concepts, but not a canonical neutralization input file.

### Market-Cap / Size Inputs

- `data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts/test.parquet`
  - Contains `total_mv_log_t*`, `circ_mv_log_t*`, and `float_share_ratio_t*` columns.
  - Metadata lists `total_mv_log`, `circ_mv_log`, and `float_share_ratio` in feature names.
- `data/datasets/lstm_quick8_57d_compact44_normhl_20230101_20260120_ts/test.parquet`
  - Contains the same size-related feature family.
- `data/datasets/sequence_xgb_nextopen_baseline_quick8_20230101_20260120/test.parquet`
  - Contains label columns but no market-cap / size columns.
- `docs/modules/data_sources.md`
  - Documents TuShare `daily_basic` fields such as `total_mv` and `circ_mv`.
  - This is source capability documentation, not approval for live provider calls.

## Findings

- Industry neutralization is runnable for historical quick8 XGB OOS reports if the implementation joins `output/reports/*_oos.parquet` with `data/symbol_sector_etf_map_quick8.csv`.
- Market-cap neutralization is not directly runnable on the current historical XGB OOS parquet because the OOS prediction rows do not carry `total_mv`, `circ_mv`, `total_mv_log`, `circ_mv_log`, or `float_share_ratio`.
- Size inputs do exist in some LSTM dataset parquet files, but those files do not by themselves provide OOS prediction columns. A later runnable path would need either:
  - OOS predictions emitted with size columns, or
  - a safe local join between OOS rows and a matching feature dataset by `(date, symbol)`.
- Existing daily-CS metric helpers are enough for a minimal residual/neutralized metric implementation; no new metric dependency is required.
- Existing report audit/compare scripts can be extended later, but S1-A2 should first define a neutralization evidence contract rather than changing compare behavior directly.

## Recommended Minimal Contract For S1-A2-T2

- Inputs:
  - OOS parquet with `date`, `symbol`, `pred_{3,5,10}d`, `label_{3,5,10}d`.
  - Optional calibrated prediction columns `pred_{3,5,10}d_cal`.
  - Industry map with `symbol` and one group column such as `sector_hint`.
  - Optional size column in the OOS parquet or an explicitly declared local join source.
- Outputs:
  - Per horizon baseline IC / RankIC.
  - Per horizon industry-neutral IC / RankIC, using within-date group demeaning where groups have enough rows.
  - Per horizon size-neutral IC / RankIC when a size column exists.
  - `blocked_by_data` lane for missing group or size inputs.
  - `promotion_blocked: true` when neutralized evidence fails or is blocked.
- First runnable target:
  - `output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet` + `data/symbol_sector_etf_map_quick8.csv` for industry-group smoke.
  - Treat market-cap / size as `blocked_by_data` unless a local size join is explicitly added in a later task.

## Scope Control

- No code was changed in this task.
- No provider calls were made.
- No long training was run.
- No dependency changes were made.
- No generated model, recommendation, production trading, commit, push, release, or tag operation was performed.
