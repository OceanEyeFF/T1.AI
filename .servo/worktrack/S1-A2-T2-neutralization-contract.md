---
title: "WT-S1-A2 / S1-A2-T2 Neutralization Evidence Contract"
artifact_type: "worktrack-task-evidence"
milestone_id: "MS-S1-001"
worktrack_id: "WT-S1-A2"
task_id: "S1-A2-T2"
updated: "2026-06-16T09:16:47+08:00"
owner: "OceanEyeFF"
---

# WT-S1-A2 / S1-A2-T2 Neutralization Evidence Contract

## Control Signal

- task_id: S1-A2-T2
- task_status: completed
- contract_status: ready_for_minimal_implementation
- recommended_next_task: S1-A2-T3
- can_continue: true
- blocker: none for industry smoke; market-cap / size lane must support `blocked_by_data`.

## Goal

Define a minimal, local, reproducible neutralization gate for `pred_3d`, `pred_5d`, and `pred_10d` that answers whether observed IC / RankIC survives basic industry and size controls.

## Inputs

- `oos_parquet`: parquet with `date`, `symbol`, `pred_{h}d`, and `label_{h}d`.
- `horizons`: default `3,5,10`.
- `group_map`: optional CSV with `symbol` and one group column, default group column `sector_hint`.
- `size_column`: optional numeric column already present in `oos_parquet`.
- `size_join`: out of scope for this WT unless explicitly added as local-only follow-up; provider calls are forbidden.
- `method`: `pearson` or `spearman`; both baseline IC and RankIC should be reported.

## Output Schema

Top-level fields:

- `check_name`: `neutralization`
- `input_path`
- `group_map_path`
- `group_col`
- `size_col`
- `horizons`: list of per-horizon records
- `overall_verdict`: `pass` / `fail` / `continue_research` / `blocked_by_data`
- `promotion_blocked`: boolean
- `created_at`

Per-horizon record fields:

- `horizon`
- `prediction_col`
- `label_col`
- `baseline_mean_ic`
- `baseline_mean_rank_ic`
- `industry_neutral_mean_ic`
- `industry_neutral_mean_rank_ic`
- `size_neutral_mean_ic`
- `size_neutral_mean_rank_ic`
- `industry_status`: `pass` / `fail` / `continue_research` / `blocked_by_data`
- `size_status`: `pass` / `fail` / `continue_research` / `blocked_by_data`
- `status`: aggregate horizon status
- `n_days`
- `n_rows`
- `reason`

## Neutralization Semantics

### Industry Lane

- Join OOS rows to `group_map` by normalized 6-digit `symbol`.
- For each date and group, demean prediction and label values when the date/group has at least two usable rows.
- Compute daily-CS IC / RankIC from the residualized prediction and label series.
- If required columns are missing, join coverage is zero, or no date/group has enough rows, status is `blocked_by_data`.
- If industry-neutral metrics remain meaningfully non-degraded versus baseline, status can be `pass`; otherwise status is `fail` or `continue_research`.

### Size Lane

- Use a numeric `size_column` already present in OOS rows.
- For each date, regress prediction and label separately on `[1, size_column]`, then compute IC / RankIC on residuals.
- If `size_column` is missing, non-numeric, or insufficient per-date observations exist, status is `blocked_by_data`.
- The current known XGB OOS smoke target does not contain size columns, so `blocked_by_data` is an acceptable result for this lane.

## Minimal Verdict Rules

- `blocked_by_data` dominates if any mandatory horizon cannot be assessed for the relevant lane.
- `fail` dominates if a neutralized lane shows the signal no longer survives the control.
- `continue_research` is allowed for borderline or small-sample outcomes that are runnable but inconclusive.
- `pass` means all requested horizons are assessed and no lane fails or blocks.
- `promotion_blocked` is `true` unless `overall_verdict == "pass"`.
- Smoke evidence must not be interpreted as model promotion evidence.

## First Runnable Target

- `oos_parquet`: `output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet`
- `group_map`: `data/symbol_sector_etf_map_quick8.csv`
- `group_col`: `sector_hint`
- `horizons`: `3,5,10`
- expected industry lane: runnable
- expected size lane: `blocked_by_data` unless a size column is explicitly supplied.

## Scope Control

- No provider calls.
- No long training.
- No dependency changes.
- No production risk engine or Barra-style risk model.
- No alpha_score promotion or model selection.
- No commit, push, release, or tag action.
