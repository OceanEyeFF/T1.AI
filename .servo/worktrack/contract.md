---
title: "WT-A3-001 Worktrack Contract"
artifact_type: "worktrack-contract"
updated: "2026-06-11T20:45:12+08:00"
owner: "OceanEyeFF"
---

# WT-A3-001 Worktrack Contract

> This contract binds `WT-A3-001` to active milestone `MS-S0-001`. It authorizes planning and dry-run manifest work for the prediction optimization experiment queue under the A2 protocol. It does not authorize long-running model retraining, external data/provider calls, dependency changes, destructive cleanup, commit, push, release actions, or final milestone acceptance.

## Metadata

- worktrack_id: WT-A3-001
- title: 预测优化实验队列
- branch: milestone/MS-S0-001-prediction-credibility
- baseline_branch: develop
- baseline_ref: b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- owner: OceanEyeFF
- updated: 2026-06-11T20:45:12+08:00
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
- worktrack_intake_review: .servo/worktrack/MS-S0-001-WT-A3-001-intake-review.md

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-S0-001-WT-A3-001-intake-review.md
- repo_fundamentals: pass; A2 protocol, tuning docs, training scripts, and validation scripts exist.
- snapshot_freshness: pass; repo snapshot refreshed after `WT-A2-001` closeout.
- milestone_purpose_alignment: pass; `WT-A3-001` implements the optimization queue after the credibility gate.
- historical_conflict_risk: medium; historical quick8 reports fail gates and cannot be used as promotion evidence.
- worktrack_adjustment_recommendations: start with planning/dry-run queue; defer actual training to explicit execution tasks.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 2
- latest_review_checkpoint: MS-S0-001-WT-A3-001-intake-2026-06-11T20:50:00+08:00
- effective_review_pass: true
- review_invalidated_by: none

## Node Type

- type: research
- primary_type: research
- source_from_goal_charter: .servo/goal-charter.md#Engineering-Node-Map
- baseline_form: report-or-experiment-artifact
- merge_required: no for planning/report-only evidence; source/docs/test edits still require programmer-approved commit before publishing.
- gate_criteria: reproducible config + stable window comparison + go/no-go statement
- if_interrupted_strategy: preserve report and stop

## Execution Policy

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes
- carrier_decision: pending scheduler/dispatch decision
- subagent_permission_state: permitted by programmer for this execution cycle

## Task Goal

### Control Signal

- goal_summary: Convert the A2 protocol into a prioritized, bounded mainline optimization experiment queue without running long model retraining in this Worktrack.

### Supporting Detail

- full_goal: Define candidate experiment families for LSTM, XGBoost, and lightweight fusion; map each to A2 protocol prerequisites, required report fields, OOS/window assumptions, validation commands, cost/risk level, and go/no-go/continue-research interpretation. Produce dry-run or command manifest evidence where safe so later execution slices can be approved deliberately.

## Scope

### Control Signal

- scope_summary: A3 optimization queue, dry-run manifests, candidate ranking, validation command templates, and A2-based promotion rules.

### Supporting Detail

- Rank LSTM baseline closure tasks.
- Rank XGBoost baseline closure tasks.
- Define lightweight fusion only as a later candidate after LSTM/XGB protocol readiness.
- Map each candidate to `docs/research/mainline_3510d_evaluation_gate_protocol.md`.
- Use existing dry-run/planning commands where possible.
- Produce `.servo/worktrack/a3-optimization-queue.md` or equivalent evidence artifact.

## Non-Goals

### Control Signal

- non_goal_summary: No full training execution, no generated model output refresh, no external provider calls, no dependency/environment changes, no commit/push, no alpha_score promotion.

### Supporting Detail

- Do not run `--execute` tuning commands.
- Do not run LSTM/XGBoost rolling retrain scripts for full OOS outputs.
- Do not call TuShare/AkShare or external providers.
- Do not write generated model checkpoints.
- Do not promote quick8 or planned candidates to decision-ready status.

## Impacted Modules

### Control Signal

- impacted_modules: research docs, Servo worktrack artifacts, possible dry-run manifest files; no training code changes expected unless a narrow bug is found.

### Supporting Detail

- .servo/worktrack/contract.md
- .servo/worktrack/plan-task-queue.md
- .servo/worktrack/gate-evidence.md
- .servo/worktrack/MS-S0-001-WT-A3-001-intake-review.md
- docs/research/mainline_3510d_evaluation_gate_protocol.md
- docs/research/multilevel_tuning_plan_20260307.md
- docs/research/mainline_3510d_model_development_plan_20260310.md
- scripts/run_multilevel_tuning.py
- scripts/auto_tune_xgb.py

## Planned Next State

### Control Signal

- next_state: WorktrackScope.Dispatch for `A3-T1`.

### Supporting Detail

- First task should inventory candidate experiment sources and produce a queue skeleton before any command execution.

## Acceptance Criteria

### Control Signal

- core_acceptance: A3 is accepted only if the optimization queue is prioritized, A2-gated, dry-run safe, and explicit about what still requires later training approval.

### Supporting Detail

- Candidate queue includes LSTM, XGBoost, and optional lightweight fusion families.
- Each candidate has prerequisites, A2 report contract, validation commands, expected artifacts, risk/cost level, and interpretation rule.
- Runtime-heavy items are split into later execution slices.
- No model is promoted by planning evidence alone.
- If dry-run commands are run, they must not train models or refresh generated prediction artifacts.

## Constraints

### Control Signal

- key_constraints: CPU-local planning, no retraining, no external side effects, no dependency changes, no commit/push, final acceptance remains programmer-owned.

### Supporting Detail

- Use `conda run -n py311-private` for safe Python checks.
- Prefer `--show-current`, no-`--execute`, or parser tests over training execution.
- Stop before any command that trains models, writes checkpoints, fetches data, or performs long-running runs.

## Verification Requirements

### Control Signal

- required_validation: focused documentation/artifact review plus safe dry-run/parser tests if relevant.

### Supporting Detail

- Verify queue entries trace to A2 protocol.
- Verify no training command was executed.
- Run focused tests or dry-run commands only if they are non-training and local.

## Current Blockers

### Control Signal

- blockers: none before A3-T1.

### Supporting Detail

- Actual model training remains blocked until a later explicit execution slice and runtime budget decision.
