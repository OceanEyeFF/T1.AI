---
title: "Worktrack Backlog"
artifact_type: "worktrack-backlog"
updated: "2026-06-22T13:20:00+08:00"
updated_by: "codex"
---

# Worktrack Backlog

> Closed and resolved worktracks are tracked here for Milestone progress and RepoScope refresh. Live per-worktrack execution details remain in `.servo/worktrack/*`.

## Done

### WT-EXPAND-001

- worktrack_id: WT-EXPAND-001
- milestone_id: MS-S2-001 (post-acceptance append)
- status: done
- node_type: fetch/compute/registry
- scope: Expand TuShare cache to sectors_70 (64 stocks), build 6-dimension composite scoring from 4-agent research, register custom_low_manipulation_v1 (14 stocks, score >= 60).
- branch: milestone/MS-S2-001-stock-pool-stratification
- merge_commit: none
- validation: 177/177 TuShare requests success; 64 stocks scored; registry load + export smoke pass; `git diff --check` pass.
- intake_route: programmer-requested post-milestone expansion
- gate_verdict: pass
- report_ref: .servo/worktrack/WT-EXPAND-001-closeout-report.md
- gate_evidence_ref: .servo/worktrack/WT-EXPAND-001-gate-evidence.md
- closeout_ref: .servo/worktrack/WT-EXPAND-001-closeout-report.md
- closed_at: 2026-06-22T13:20:00+08:00
- residual_risk: score thresholds uncalibrated; 64-stock universe may not represent full market.

### WT-S2-A4

- worktrack_id: WT-S2-A4
- milestone_id: MS-S2-001
- status: done
- node_type: research/report
- scope: downstream revalidation input contract, TuShare fetch budget estimate, and milestone closing report.
- branch: milestone/MS-S2-001-stock-pool-stratification
- merge_commit: none
- validation: `git diff --check` -> pass.
- intake_route: milestone-derived (final planned worktrack)
- gate_verdict: pass
- report_ref: docs/modules/downstream_revalidation_input_contract_MS_S2_001.md; .servo/worktrack/s2-a4-milestone-closing-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s2-a4-closeout-report.md
- closed_at: 2026-06-22T12:30:00+08:00
- residual_risk: milestone complete; requires programmer final acceptance.

### WT-S2-A3

- worktrack_id: WT-S2-A3
- milestone_id: MS-S2-001
- status: done
- node_type: feature/test
- scope: cache-only sample pool construction (liquid large-cap proxy + low-control-proxy candidate), registry registration, and export smoke.
- branch: milestone/MS-S2-001-stock-pool-stratification
- merge_commit: none
- validation: `python scripts/build_ms_s2_stratified_pools.py` -> generated 2 TOML + CSV + metadata; registry load + export smoke -> pass; `pytest -q tests/test_tushare_source.py` -> 14 passed; `git diff --check` -> pass.
- intake_route: milestone-derived; unblocked after mid-review passed 2026-06-22
- gate_verdict: pass
- report_ref: .servo/worktrack/s2-a3-closeout-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s2-a3-closeout-report.md
- closed_at: 2026-06-22T12:15:00+08:00
- residual_risk: cache coverage limited to 8 symbols; low-control turnover threshold not calibrated.

### WT-S2-A2-next

- worktrack_id: WT-S2-A2-next
- milestone_id: MS-S2-001
- status: done
- node_type: design/docs
- scope: compress A1 stock-pool taxonomy into the only A3 input contract and defer over-broad observation layers.
- branch: milestone/MS-S2-001-stock-pool-stratification
- merge_commit: none
- validation: scoped `git diff --check` -> pass.
- intake_route: milestone-derived and programmer-requested after A2
- gate_verdict: pass
- report_ref: docs/modules/stock_pool_a3_input_contract_MS_S2_001.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s2-a2-next-closeout-report.md
- closed_at: 2026-06-22T11:12:24+08:00
- residual_risk: A3 remains blocked until programmer review passes; A3 must use compressed contract, not full A1 taxonomy.

### WT-S2-A2

- worktrack_id: WT-S2-A2
- milestone_id: MS-S2-001
- status: done
- node_type: test/design
- scope: TuShare cache-first dry-run request manifest, quota-wall tests, resume, blocked-by-quota, and registry schema gap review.
- branch: milestone/MS-S2-001-stock-pool-stratification
- merge_commit: none
- validation: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_tushare_source.py` -> `14 passed`; `python -m py_compile src/ashare_lab/data/tushare_source.py` -> pass; scoped `git diff --check` -> pass.
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/s2-a2-closeout-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s2-a2-closeout-report.md
- closed_at: 2026-06-22T10:48:41+08:00
- residual_risk: A3 remains blocked until programmer mid-review passes; no quota-consuming TuShare call was approved or made.

### WT-S2-A1

- worktrack_id: WT-S2-A1
- milestone_id: MS-S2-001
- status: done
- node_type: research/docs
- scope: stock-pool stratification taxonomy and proxy boundary freeze for MS-S2.
- branch: milestone/MS-S2-001-stock-pool-stratification
- merge_commit: none
- validation: scoped `git diff --check` -> pass; new-file trailing whitespace scan -> pass; provider-call pattern scan -> no matches; policy-line scan -> required A2/A3 boundaries present.
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: docs/modules/stock_pool_stratification_contract_MS_S2_001.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s2-a1-closeout-report.md
- closed_at: 2026-06-22T10:48:41+08:00
- residual_risk: A2 must still implement or design no-network/quota-free tests for request budget dry-run, cache-hit behavior, 1H frequency-wall time-waiting, resume, and blocked-by-quota; A3 is blocked until programmer mid-review after A2.

### WT-S1-CLEANUP

- worktrack_id: WT-S1-CLEANUP
- milestone_id: MS-S1-001
- status: done
- node_type: docs/test/checkpoint
- scope: post-acceptance cleanup, validation, and local git checkpoint for accepted MS-S1 diff.
- branch: milestone/MS-S1-001-three-head-credibility
- merge_commit: none
- local_checkpoint: HEAD on `milestone/MS-S1-001-three-head-credibility`
- validation: `git diff --check` -> pass; focused pytest -> `41 passed`; patch/conflict residue check -> no matches after excluding command-text self references.
- intake_route: post-acceptance cleanup requested by programmer
- gate_verdict: pass
- report_ref: .servo/worktrack/s1-cleanup-closeout-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s1-cleanup-closeout-report.md
- closed_at: 2026-06-18T10:06:55+08:00
- residual_risk: push, merge to `develop`, branch deletion, and MS-S2 initialization remain outside this Worktrack and approval-gated.

### WT-S1-A5

- worktrack_id: WT-S1-A5
- milestone_id: MS-S1-001
- status: done
- node_type: research/report
- scope: final three-head credibility acceptance synthesis for MS-S1.
- branch: milestone/MS-S1-001-three-head-credibility
- merge_commit: none
- validation: JSON evidence parse checks -> pass; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py tests/test_sanity_checks.py` -> `41 passed`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/S1-A5-final-three-head-acceptance-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s1-a5-closeout-report.md
- closed_at: 2026-06-16T18:50:00+08:00
- residual_risk: final report concludes continue-research / blocked-by-data; final milestone acceptance remains programmer-gated.

### WT-S1-A4

- worktrack_id: WT-S1-A4
- milestone_id: MS-S1-001
- status: done
- node_type: test/evaluation
- scope: same-window three-head smoke feasibility for local LSTM/XGBoost reports under strict report/OOS protocol.
- branch: milestone/MS-S1-001-three-head-credibility
- merge_commit: none
- validation: `python -m json.tool .servo/worktrack/evidence/ic_report_oos_coverage_same_window_fastpilot_A4.json` -> pass; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py` -> `21 passed`; local OOS audit -> strict daily-CS readiness `0/2`; protocol check -> expected failure on historical XGB missing `evaluation_protocol`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/S1-A4-T3-smoke-evidence.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s1-a4-closeout-report.md
- closed_at: 2026-06-16T17:50:00+08:00
- residual_risk: same-window strict LSTM/XGB comparison remains blocked by missing OOS parquet paths; this evidence supports continue-research, not model promotion.

### WT-S1-A3

- worktrack_id: WT-S1-A3
- milestone_id: MS-S1-001
- status: done
- node_type: tooling/report-contract
- scope: local XGBoost report contract compliance for shared protocol checking and same-window model comparison.
- branch: milestone/MS-S1-001-three-head-credibility
- merge_commit: none
- validation: `python -m py_compile scripts/run_xgboost_rolling_retrain_regime.py tests/test_xgboost_report_contract.py` -> pass; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_xgboost_report_contract.py` -> `2 passed`; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py tests/test_trade_like_panel.py tests/test_sanity_checks.py` -> `43 passed`; protocol smoke -> pass
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/S1-A3-T3-implementation-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s1-a3-closeout-report.md
- closed_at: 2026-06-16T16:25:00+08:00
- residual_risk: no end-to-end XGBoost retraining was run; historical fastpilot XGB report still lacks OOS parquet path; protocol compliance is not model promotion evidence.

### WT-S1-A2

- worktrack_id: WT-S1-A2
- milestone_id: MS-S1-001
- status: done
- node_type: test/evaluation
- scope: local industry / market-cap neutralization gate for mainline `pred_3d` / `pred_5d` / `pred_10d` credibility evaluation.
- branch: milestone/MS-S1-001-three-head-credibility
- merge_commit: none
- validation: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_sanity_checks.py` -> `20 passed`; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_sanity_checks.py` -> `39 passed`; neutralization JSON evidence parse check -> pass
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/S1-A2-T3-implementation-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s1-a2-closeout-report.md
- closed_at: 2026-06-16T14:28:06+08:00
- residual_risk: industry-neutral quick8 result is cautionary and blocks promotion; size neutralization remains blocked for current XGB OOS because no size column is present; commit/push remain approval-gated.

### WT-S1-A1

- worktrack_id: WT-S1-A1
- milestone_id: MS-S1-001
- status: done
- node_type: test
- scope: local random-label anti-cheat gate for mainline `pred_3d` / `pred_5d` / `pred_10d` credibility evaluation.
- branch: milestone/MS-S1-001-three-head-credibility
- merge_commit: none
- validation: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_sanity_checks.py tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py` -> `36 passed`; random-label and sanity JSON evidence parse checks -> pass
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/S1-A1-T3-implementation-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/s1-a1-closeout-report.md
- closed_at: 2026-06-12T15:08:00+08:00
- residual_risk: quick8 random-label smoke is not model promotion evidence; h5 time-reverse sanity smoke still failed; commit/push remain approval-gated.

### WT-C0-001

- worktrack_id: WT-C0-001
- milestone_id: MS-S0-001
- status: done
- node_type: docs/research
- scope: decision-model input/output draft with signal maturity guards and replay requirements.
- branch: milestone/MS-S0-001-prediction-credibility
- merge_commit: none
- validation: `python -m json.tool .servo/worktrack/evidence/decision_model_io_contract_schema_WT-C0-001.json` -> pass; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_strategy_portfolio.py tests/test_engine_rules.py tests/test_recommendation_engine.py tests/test_trend_aggregation.py` -> `29 passed`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/evidence/decision_model_io_contract_draft_WT-C0-001.md
- schema_ref: .servo/worktrack/evidence/decision_model_io_contract_schema_WT-C0-001.json
- gate_evidence_ref: .servo/worktrack/c0-gate-evidence.md
- closeout_ref: .servo/worktrack/c0-closeout-report.md
- closed_at: 2026-06-11T21:01:55+08:00
- residual_risk: C0 is a draft-only evidence artifact; canonical docs promotion and C1/C2/C3 implementation require later approval.

### WT-B0-001

- worktrack_id: WT-B0-001
- milestone_id: MS-S0-001
- status: done
- node_type: research
- scope: read-only intraday/minute data source feasibility report for the independent `1d` line.
- branch: milestone/MS-S0-001-prediction-credibility
- merge_commit: none
- validation: `python -m json.tool .servo/worktrack/evidence/1d_intraday_data_feasibility_matrix_WT-B0-001.json` -> pass; `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_odp_source.py tests/test_tushare_source.py tests/test_source_misc.py` -> `23 passed`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/evidence/1d_intraday_data_feasibility_report_WT-B0-001.md
- matrix_ref: .servo/worktrack/evidence/1d_intraday_data_feasibility_matrix_WT-B0-001.json
- gate_evidence_ref: .servo/worktrack/b0-gate-evidence.md
- closeout_ref: .servo/worktrack/b0-closeout-report.md
- closed_at: 2026-06-11T21:01:55+08:00
- residual_risk: `1d` modeling remains blocked until a live provider smoke or equivalent source proof verifies minute permission, history depth, field quality, and fixed-pool fixed-window replay.

### WT-A3-001

- worktrack_id: WT-A3-001
- milestone_id: MS-S0-001
- status: done
- node_type: research
- scope: planning and dry-run manifest for prediction optimization experiment queue under A2 protocol.
- branch: milestone/MS-S0-001-prediction-credibility
- merge_commit: none
- validation: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_multilevel_tuning.py tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py` -> `28 passed`; dry-run manifest generated without `--execute`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/a3-optimization-queue.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/a3-closeout-report.md
- closed_at: 2026-06-11T20:50:23+08:00
- residual_risk: actual model training remains a later approved execution slice; XGB report contract writeout should be confirmed before execution.

### WT-A2-001

- worktrack_id: WT-A2-001
- milestone_id: MS-S0-001
- status: done
- node_type: research/test
- scope: evaluation protocol freeze, anti-false-signal gate mapping, historical OOS/report coverage audit, focused reproducibility docs/scripts/tests, and A2 gate evidence.
- branch: milestone/MS-S0-001-prediction-credibility
- merge_commit: none
- validation: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_sanity_checks.py tests/test_trade_like_panel.py tests/test_evaluation_metrics.py tests/test_labels.py tests/test_maturity_gate.py tests/test_one_day_hlc_label.py` -> `75 passed`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/a2-credibility-gate-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closeout_ref: .servo/worktrack/closeout-report.md
- closed_at: 2026-06-11T20:45:00+08:00
- residual_risk: no model is promoted; random-label and industry / market-cap neutralization remain explicit follow-up anti-cheat gaps.

### WT-ENV-001

- worktrack_id: WT-ENV-001
- milestone_id: MS-ENV-000
- status: done
- node_type: test/config
- scope: conda environment inventory, approved `py311-private` dependency repair, environment-contract migration, import smoke, env guard, ruff availability, and minimal pytest validation.
- merge_commit: none
- validation: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_env_guard.py tests/test_features_technical.py tests/test_sequence_builder.py tests/test_models.py` -> `36 passed`
- intake_route: milestone-derived
- gate_verdict: pass
- report_ref: .servo/worktrack/environment-validation-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- closed_at: 2026-06-11T16:40:59+08:00
- residual_risk: GPU training on local GTX 1080 Ti / `sm_61` is not validated with current PyTorch wheel; CPU lane accepted.
