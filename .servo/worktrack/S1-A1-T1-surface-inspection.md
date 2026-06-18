---
title: "S1-A1-T1 Surface Inspection"
artifact_type: "worktrack-evidence"
worktrack_id: "WT-S1-A1"
milestone_id: "MS-S1-001"
task_id: "S1-A1-T1"
updated: "2026-06-12T14:52:00+08:00"
updated_by: "harness-skill"
---

# S1-A1-T1 Surface Inspection

## Control Signal

- task_id: S1-A1-T1
- task_status: completed
- inspection_mode: readonly
- code_edits_performed: false
- provider_calls_performed: false
- model_training_performed: false
- dependency_changes_performed: false
- local_input_availability: available_for_quick8_smoke
- recommended_next_task: S1-A1-T2
- recommended_next_boundary: design a minimal random-label evidence contract before implementation.
- blocker: N/A

## Candidate Integration Points

- `scripts/run_sanity_checks.py`
  - Supports `--oos-parquet` with `pred_{horizon}d` and `label_{horizon}d`.
  - Already bridges OOS parquet rows into `ashare_lab.evaluation.sanity_checks.run_all_checks`.
  - Current checks include shuffle labels, time reverse, and lag-1.
  - Best candidate for adding an explicit random-label mode or adjacent CLI because it already handles anti-cheat semantics.
- `src/ashare_lab/evaluation/sanity_checks.py`
  - Existing test coverage proves shuffle/time-reverse/lag-1 behavior.
  - Likely reusable for random-label implementation if random-label is defined as independently randomized label trials rather than date/order perturbation only.
- `scripts/compare_ic_reports.py`
  - Handles strict report protocol, OOS parquet resolution, Daily-CS IC/RankIC, common-month alignment, and gate thresholds.
  - Better as a report comparison consumer than as the random-label generator itself.
- `tests/test_compare_ic_reports.py`
  - Has local parquet fixture patterns for reports and OOS paths.
  - Useful for report-contract tests if random-label evidence is added to comparison output later.
- `tests/test_sanity_checks.py`
  - Has synthetic strong/noise signal fixtures.
  - Best first test surface for random-label behavior.

## Local Input Availability

- quick8 reports exist:
  - `output/reports/xgb_d1_close_candidate_quick8_20260309.json`
  - `output/reports/xgb_nextopen_baseline_quick8_20260309.json`
- quick8 OOS parquet exists:
  - `output/reports/xgb_d1_close_candidate_quick8_20260309_oos.parquet`
  - `output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet`
- Existing A2 evidence used `xgb_nextopen_baseline_quick8_20260309_oos.parquet` for h5 and h10 sanity checks.
- No new provider call or training is needed for a bounded smoke on existing local files.

## Gap Analysis

- The protocol explicitly says independent random-label CLI is not implemented.
- Current shuffle check is only a proxy, not the requested random-label gate.
- Existing OOS parquet loader supports one horizon at a time and only `pred_{horizon}d` / `label_{horizon}d` pairs.
- MS-S1 requires `pred_3d`, `pred_5d`, and `pred_10d`; current available local quick8 OOS evidence visibly supports h5/h10 in prior A2 commands, while h3 availability must be checked before implementation.
- A random-label gate should output pass/fail/continue-research rather than only raw sanity-check subfields.

## Recommended S1-A1-T2 Boundary

- Define the random-label evidence contract before editing code:
  - input path fields
  - supported horizons
  - per-horizon baseline IC/RankIC
  - random-label trial count and seed
  - randomized mean/std/max absolute IC or equivalent anti-cheat statistic
  - verdict: pass / fail / continue-research / blocked_by_data
  - promotion_blocked boolean
  - blocked_by_data reason when a horizon or parquet field is missing
- Keep implementation path local to `scripts/run_sanity_checks.py` and/or `ashare_lab.evaluation.sanity_checks`.
- Avoid modifying `compare_ic_reports.py` unless report comparison must consume the new random-label evidence in this Worktrack.

## Policy Evidence

- no_training: true
- no_provider_calls: true
- no_dependency_changes: true
- no_code_edits: true
- no_commit_or_push: true
- no_alpha_score_promotion: true
