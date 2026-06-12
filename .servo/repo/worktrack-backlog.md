---
title: "Worktrack Backlog"
artifact_type: "worktrack-backlog"
updated: "2026-06-11T21:01:55+08:00"
updated_by: "harness-skill"
---

# Worktrack Backlog

> Closed and resolved worktracks are tracked here for Milestone progress and RepoScope refresh. Live per-worktrack execution details remain in `.servo/worktrack/*`.

## Done

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
