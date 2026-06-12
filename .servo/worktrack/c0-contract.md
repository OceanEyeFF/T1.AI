---
title: "WT-C0-001 Worktrack Contract"
artifact_type: "worktrack-contract"
updated: "2026-06-11T21:01:55+08:00"
owner: "OceanEyeFF"
---

# WT-C0-001 Worktrack Contract

> This contract binds `WT-C0-001` to active milestone `MS-S0-001`. It authorizes a decision-model I/O draft only. It does not authorize trading logic implementation, model training, signal promotion, dependency changes, destructive cleanup, commit, push, release actions, or final milestone acceptance.

## Metadata

- worktrack_id: WT-C0-001
- title: 决策模型 I/O 草案
- branch: milestone/MS-S0-001-prediction-credibility
- baseline_branch: develop
- baseline_ref: b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- owner: OceanEyeFF
- updated: 2026-06-11T21:01:55+08:00
- contract_status: initialized

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-S0-001-prediction-credibility@b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- worktrack_branch: milestone/MS-S0-001-prediction-credibility
- integration_target_ref: milestone/MS-S0-001-prediction-credibility
- closeout_target_ref: milestone/MS-S0-001-prediction-credibility
- final_baseline_branch: develop
- checkpoint_base_ref: b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- branch_policy_note: This Worktrack reuses the active Milestone branch under the project-level one-development-branch-per-milestone policy.

## Milestone Binding

- milestone_id: MS-S0-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-S0-001.md
- milestone_backlog: .servo/repo/milestone-backlog.md
- worktrack_intake_review: .servo/worktrack/MS-S0-001-WT-C0-001-intake-review.md

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-S0-001-WT-C0-001-intake-review.md
- repo_fundamentals: pass; existing protocol, recommendation, portfolio, and backtest surfaces are available for I/O alignment.
- snapshot_freshness: pass; snapshot records WT-A2/WT-A3/WT-B0 closed and C0 planned.
- milestone_purpose_alignment: pass; C0 satisfies the milestone completion signal decision_io_draft_bounded.
- historical_conflict_risk: low; C0 is draft-only and preserves no-promotion rules.
- worktrack_adjustment_recommendations: execute as docs/research draft; no implementation.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 4
- latest_review_checkpoint: MS-S0-001-WT-C0-001-intake-2026-06-11T21:01:55+08:00
- effective_review_pass: true
- review_invalidated_by: none

## Node Type

- type: docs/research
- primary_type: docs
- source_from_goal_charter: .servo/goal-charter.md#Engineering-Node-Map
- baseline_form: report-or-experiment-artifact
- merge_required: no for draft evidence; source/docs/test edits still require programmer-approved commit before publishing.
- gate_criteria: docs match code reality + no false tradability + replayable I/O draft
- if_interrupted_strategy: preserve draft and stop

## Execution Policy

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes
- carrier_decision: current-carrier synthesis
- subagent_permission_state: permitted by programmer for this execution cycle

## Task Goal

### Control Signal

- goal_summary: Freeze a bounded decision-model I/O draft that downstream C1/C2/C3 work can consume later without treating unverified candidate signals as tradable.

### Supporting Detail

- Define input records, output records, replay requirements, maturity gates, and no-go defaults.
- Explicitly map to existing protocol/recommendation/strategy/backtest surfaces.

## Scope

### Control Signal

- scope_summary: C0 decision input/output draft and validation evidence only.

### Supporting Detail

- Produce `.servo/worktrack/evidence/decision_model_io_contract_draft_WT-C0-001.md`.
- Produce `.servo/worktrack/evidence/decision_model_io_contract_schema_WT-C0-001.json`.
- Validate JSON schema/draft and run focused local tests.

## Non-Goals

### Control Signal

- non_goal_summary: No code implementation, no trading logic changes, no signal promotion, no model training, no provider calls.

### Supporting Detail

- Do not modify `PortfolioManager`, `BacktestEngine`, recommendation engine, or configs.
- Do not implement rebalance threshold or cost coverage.
- Do not add production decision storage.
- Do not make `1d_signal` default.

## Impacted Modules

### Control Signal

- impacted_modules: Servo worktrack artifacts and C0 evidence files only.

### Supporting Detail

- .servo/worktrack/MS-S0-001-WT-C0-001-intake-review.md
- .servo/worktrack/c0-contract.md
- .servo/worktrack/c0-plan-task-queue.md
- .servo/worktrack/c0-gate-evidence.md
- .servo/worktrack/c0-closeout-report.md
- .servo/worktrack/evidence/decision_model_io_contract_draft_WT-C0-001.md
- .servo/worktrack/evidence/decision_model_io_contract_schema_WT-C0-001.json

## Acceptance Criteria

### Control Signal

- core_acceptance: C0 is accepted if input/output fields, replay requirements, signal maturity rules, and no-trade/blocking diagnostics are explicit and aligned with existing protocol surfaces.

### Supporting Detail

- Fixed CSV/Parquet input can replay the same decisions without model execution.
- Output explains buy/sell/hold/no-trade causes.
- Candidate `alpha_score` and `1d_signal` cannot silently become production inputs.
- C1/C2/C3 implementation remains out of scope.

## Constraints

### Control Signal

- key_constraints: docs/research-only, no external side effects, no dependency changes, no destructive cleanup, no commit/push, final acceptance remains programmer-owned.

## Verification Requirements

### Control Signal

- required_validation: JSON validation, field consistency review, and focused local strategy/backtest/recommendation tests.

### Supporting Detail

- `python -m json.tool .servo/worktrack/evidence/decision_model_io_contract_schema_WT-C0-001.json`
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_strategy_portfolio.py tests/test_engine_rules.py tests/test_recommendation_engine.py tests/test_trend_aggregation.py`

## Current Blockers

### Control Signal

- blockers: none before C0 evidence production.

### Supporting Detail

- Later C1/C2/C3 implementation requires new Worktracks and explicit acceptance of signal maturity state.
