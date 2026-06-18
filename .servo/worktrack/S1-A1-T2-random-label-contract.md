---
title: "S1-A1-T2 Random-Label Evidence Contract"
artifact_type: "worktrack-evidence"
worktrack_id: "WT-S1-A1"
milestone_id: "MS-S1-001"
task_id: "S1-A1-T2"
updated: "2026-06-12T14:55:00+08:00"
updated_by: "harness-skill"
---

# S1-A1-T2 Random-Label Evidence Contract

## Control Signal

- task_id: S1-A1-T2
- task_status: completed
- contract_status: ready_for_implementation
- implementation_target: `scripts/run_sanity_checks.py` plus `ashare_lab.evaluation.sanity_checks` if reusable library logic is needed.
- report_consumer_target: keep `scripts/compare_ic_reports.py` unchanged unless later validation requires cross-report consumption.
- required_horizons: 3, 5, 10
- verdict_values: pass, fail, continue_research, blocked_by_data
- promotion_block_rule: any fail or blocked_by_data with missing mandatory horizon blocks promotion.
- recommended_next_task: S1-A1-T3
- blocker: N/A

## Evidence Schema

Top-level fields:

- `check_name`: `random_label`
- `input_path`: source OOS parquet path.
- `horizons`: list of per-horizon records.
- `all_pass`: boolean.
- `overall_verdict`: pass / fail / continue_research / blocked_by_data.
- `promotion_blocked`: boolean.
- `seed`: integer.
- `random_trials`: integer.
- `created_at`: ISO-like timestamp or N/A when produced by tests.

Per-horizon fields:

- `horizon`: integer, e.g. 3, 5, 10.
- `prediction_col`: expected prediction column, e.g. `pred_3d`.
- `label_col`: expected label column, e.g. `label_3d`.
- `status`: pass / fail / continue_research / blocked_by_data.
- `baseline_mean_ic`: float or N/A.
- `baseline_mean_rank_ic`: float or N/A.
- `random_label_mean_ic`: float or N/A.
- `random_label_abs_mean_ic`: float or N/A.
- `random_label_max_abs_ic`: float or N/A.
- `random_trials`: integer.
- `threshold_abs_mean_ic`: float.
- `n_days`: integer or N/A.
- `n_rows`: integer or N/A.
- `reason`: concise explanation.

## Verdict Rules

- `pass`: required columns exist, sample is non-empty, randomized labels produce `random_label_abs_mean_ic <= threshold_abs_mean_ic`, and no trial-level statistic is suspicious enough to indicate leakage-like behavior.
- `fail`: required columns exist and sample is non-empty, but randomized labels still produce too-high absolute IC or otherwise suspicious anti-cheat statistics.
- `continue_research`: data exists but is too small, unstable, or ambiguous for a decisive anti-cheat conclusion.
- `blocked_by_data`: required prediction/label columns are missing, parquet is unreadable, or there are no usable rows after filtering.

Overall:

- `overall_verdict = fail` if any required horizon fails.
- `overall_verdict = blocked_by_data` if any mandatory horizon is blocked by data and no implementation-scope fallback is explicitly accepted.
- `overall_verdict = continue_research` if no horizon fails/blocks but at least one horizon is ambiguous.
- `overall_verdict = pass` only if all required horizons pass.
- `promotion_blocked = true` unless `overall_verdict == pass`.

## Implementation Boundary For S1-A1-T3

In scope:

- Add random-label calculation to existing anti-cheat surfaces.
- Support `--oos-parquet` with requested horizons.
- Emit JSON matching this contract.
- Add focused synthetic tests and, if local OOS columns permit, a quick8 smoke.

Out of scope:

- Full model training.
- Provider calls.
- Dependency changes.
- Report comparison redesign.
- `alpha_score` optimization or promotion.
- Final milestone acceptance.

## Validation Plan

- Unit tests should cover:
  - strong signal where randomized labels collapse IC.
  - missing horizon columns returning `blocked_by_data`.
  - fail behavior when randomized labels remain suspicious.
  - JSON schema shape for per-horizon records.
- Optional smoke:
  - run against existing quick8 OOS parquet only if required horizon columns are present.
  - if h3 is missing, produce `blocked_by_data` for h3 rather than hiding it.

## Policy Evidence

- no_code_edits: true
- no_training: true
- no_provider_calls: true
- no_dependency_changes: true
- no_commit_or_push: true
- no_alpha_score_promotion: true
