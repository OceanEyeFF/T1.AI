---
title: "S1-A5 Final Three-Head Acceptance Report"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T18:15:00+08:00"
owner: "OceanEyeFF"
---

# S1-A5 Final Three-Head Acceptance Report

## Control Signal

- task_id: S1-A5-T1
- task_status: completed
- report_result: completed
- milestone_scope_result: continue-research
- model_promotion_allowed: no
- alpha_score_promotion_allowed: no
- recommended_next_action: S1-A5-T2 Validate final report references

## Executive Conclusion

MS-S1 evidence does not support promoting the current `pred_3d`, `pred_5d`, or `pred_10d` heads into decision research as trusted signals. The correct status is `continue-research / blocked-by-data`.

The strongest positive-looking baseline result is 5d IC / RankIC on the quick8 XGB OOS, but it fails the practical credibility bar because industry-neutral residual IC turns negative and same-window LSTM/XGB strict comparison is blocked by missing OOS artifacts.

## Per-Horizon Evidence Table

| horizon | baseline IC | baseline RankIC | random-label | industry-neutral IC | size-neutral | same-window status | conclusion |
|---:|---:|---:|---|---:|---|---|---|
| 3d | -0.035745 | -0.037201 | pass | -0.076948 | blocked_by_data | blocked_by_data | no-go for current evidence |
| 5d | 0.081738 | 0.081524 | pass | -0.168289 | blocked_by_data | blocked_by_data | continue-research; baseline positive but not robust |
| 10d | 0.045301 | 0.039199 | pass | -0.039870 | blocked_by_data | blocked_by_data | continue-research; weak baseline and not robust |

## Evidence Synthesis

### A1 Random-Label

- Evidence: `.servo/worktrack/evidence/random_label_xgb_nextopen_quick8_WT-S1-A1.json`
- Result: pass for 3d/5d/10d random-label collapse.
- Interpretation: the current quick8 OOS does not show obvious random-label leakage under this smoke. This is necessary but not sufficient for model usefulness.

### A2 Neutralization

- Evidence: `.servo/worktrack/evidence/neutralization_xgb_nextopen_quick8_WT-S1-A2.json`
- Result: overall `blocked_by_data`; promotion blocked.
- Industry-neutral residual IC:
  - 3d: `-0.076948`
  - 5d: `-0.168289`
  - 10d: `-0.039870`
- Size neutralization: blocked by missing size input.
- Interpretation: the apparent 5d baseline IC does not survive quick8 industry residualization. This blocks promotion.

### A3 XGBoost Report Contract

- Evidence: `.servo/worktrack/S1-A3-T4-validation-report.md`
- Result: pass for writer contract.
- Interpretation: future XGBoost reports can emit `evaluation_protocol` and `comparison_panel`, but historical fastpilot XGB report remains incomplete unless regenerated or adapted.

### A4 Same-Window Smoke

- Evidence: `.servo/worktrack/evidence/ic_report_oos_coverage_same_window_fastpilot_A4.json`
- Result: blocked_by_data.
- Strict daily-CS readiness:
  - OOS path ready: `0/2`
  - raw readiness: `0/2`
  - calibrated readiness: `0/2`
- Interpretation: current fastpilot LSTM/XGB reports cannot be fairly compared under strict same-window daily-CS because both lack OOS parquet paths, and historical XGB also lacks protocol fields.

## Model And Quant Interpretation

- `pred_3d`: no-go for current evidence. Baseline IC is already negative, random-label passes only anti-leakage smoke, and no same-window confirmation exists.
- `pred_5d`: continue-research. Baseline IC / RankIC are positive, but industry-neutral residual IC is strongly negative and size/same-window evidence is blocked.
- `pred_10d`: continue-research. Baseline IC is weakly positive, RankIC is modest, industry-neutral residual IC is negative, and same-window evidence is blocked.

## Smallest Safe Next Inputs

- Same-window OOS parquet for both LSTM and XGBoost fastpilot reports.
- Regenerated WT-S1-A3-compliant XGBoost report or a verified adapter report with protocol fields and explicit OOS path.
- Size column or stable size map for size neutralization.
- Only after those inputs exist should strict daily-CS compare and per-horizon acceptance be rerun.

## Final MS-S1 Recommendation

- milestone_model_verdict: continue-research
- proceed_to_training_optimization: no, not on current evidence
- proceed_to_model_promotion: no
- proceed_to_alpha_score_promotion: no
- recommended_next_milestone_theme: data/report completeness for same-window OOS, then rerun strict per-horizon credibility gates.

## Residual Risks

- Evidence is mostly quick8 smoke and historical reports.
- Same-window strict comparison is blocked by missing artifacts.
- Size neutralization is blocked by missing size input.
- No production trading conclusion is permitted.
