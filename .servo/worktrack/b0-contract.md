---
title: "WT-B0-001 Worktrack Contract"
artifact_type: "worktrack-contract"
updated: "2026-06-11T21:01:55+08:00"
owner: "OceanEyeFF"
---

# WT-B0-001 Worktrack Contract

> This contract binds `WT-B0-001` to active milestone `MS-S0-001`. It authorizes a read-only intraday/minute data feasibility report for the independent `1d` line. It does not authorize live provider calls, credential checks, model training, code implementation, dependency changes, destructive cleanup, commit, push, release actions, or final milestone acceptance.

## Metadata

- worktrack_id: WT-B0-001
- title: 1d 日内数据源可用性验证
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
- worktrack_intake_review: .servo/worktrack/MS-S0-001-WT-B0-001-intake-review.md

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-S0-001-WT-B0-001-intake-review.md
- repo_fundamentals: pass; active milestone, three-track plan, 1d research docs, data source modules, and daily data contract exist.
- snapshot_freshness: pass; repo snapshot records WT-A2-001 and WT-A3-001 closed and 1d blocked on intraday/minute feasibility.
- milestone_purpose_alignment: pass; B0 satisfies the milestone completion signal one_day_data_feasibility_report_available.
- historical_conflict_risk: low; B0 is read-only and does not modify A2/A3 mainline prediction gates.
- worktrack_adjustment_recommendations: execute as read-only feasibility/reporting; defer live provider smoke and implementation.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 3
- latest_review_checkpoint: MS-S0-001-WT-B0-001-intake-2026-06-11T21:01:55+08:00
- effective_review_pass: true
- review_invalidated_by: none

## Node Type

- type: research
- primary_type: research
- source_from_goal_charter: .servo/goal-charter.md#Engineering-Node-Map
- baseline_form: report-or-experiment-artifact
- merge_required: no for feasibility/report-only evidence; source/docs/test edits still require programmer-approved commit before publishing.
- gate_criteria: source feasibility matrix + reproducibility note + data gate conclusion
- if_interrupted_strategy: preserve report and stop

## Execution Policy

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes
- carrier_decision: delegated-readonly-explorer plus current-carrier synthesis
- subagent_permission_state: permitted by programmer for this execution cycle

## Task Goal

### Control Signal

- goal_summary: Determine whether the independent `1d` line has at least one credible minute/intraday data source path for fixed-pool fixed-window replay before any modeling expansion.

### Supporting Detail

- Produce a provider/source feasibility report and matrix covering permissions, frequency, fields, history depth, replay suitability, cache strategy, and blockers.
- Keep `1d` independent and preserve the rule that day-K-only `1d` evidence cannot approve ultra-fast modeling.

## Scope

### Control Signal

- scope_summary: Read-only source feasibility, repo capability inventory, provider documentation synthesis, and data gate conclusion.

### Supporting Detail

- Inventory current repo adapters in `src/ashare_lab/data`.
- Inventory data contract status in `docs/interfaces/data_contract.md`.
- Consume public documentation for TuShare `stk_mins`, AkShare minute APIs, and local ODP interval support.
- Produce `.servo/worktrack/evidence/1d_intraday_data_feasibility_report_WT-B0-001.md`.
- Produce `.servo/worktrack/evidence/1d_intraday_data_feasibility_matrix_WT-B0-001.json`.

## Non-Goals

### Control Signal

- non_goal_summary: No live provider calls, no credentials, no minute loader implementation, no 1d training, no alpha_score or decision-model integration.

### Supporting Detail

- Do not call TuShare/AkShare/ODP APIs.
- Do not read or print provider tokens.
- Do not write generated market data caches.
- Do not create B1 labels/features or B2 models.
- Do not change mainline prediction reports or promotion rules.

## Impacted Modules

### Control Signal

- impacted_modules: Servo worktrack artifacts and feasibility evidence files only.

### Supporting Detail

- .servo/worktrack/MS-S0-001-WT-B0-001-intake-review.md
- .servo/worktrack/b0-contract.md
- .servo/worktrack/b0-plan-task-queue.md
- .servo/worktrack/b0-gate-evidence.md
- .servo/worktrack/b0-closeout-report.md
- .servo/worktrack/evidence/1d_intraday_data_feasibility_report_WT-B0-001.md
- .servo/worktrack/evidence/1d_intraday_data_feasibility_matrix_WT-B0-001.json

## Acceptance Criteria

### Control Signal

- core_acceptance: B0 is accepted if it produces a source feasibility report and matrix, distinguishes proven facts from conditional assumptions, and gives a clear data gate verdict for `1d` modeling readiness.

### Supporting Detail

- TuShare, AkShare, ODP/OpenBB, and other professional candidates are compared.
- Report states whether current code already supports minute replay.
- Matrix covers permission, coverage, history depth, `1min/5min/15min`, fields, replay suitability, cache strategy, and blockers.
- If no source is proven ready without external approval, `1d` modeling remains blocked.

## Constraints

### Control Signal

- key_constraints: read-only provider analysis, no external side effects, no dependency changes, no destructive cleanup, no commit/push, final acceptance remains programmer-owned.

### Supporting Detail

- Use local repo reads, public documentation, and existing tests only.
- Any live smoke must be split into a later explicitly approved Worktrack.

## Verification Requirements

### Control Signal

- required_validation: JSON matrix validation, focused local adapter/cache tests, and policy evidence that no provider calls or model training occurred.

### Supporting Detail

- `python -m json.tool .servo/worktrack/evidence/1d_intraday_data_feasibility_matrix_WT-B0-001.json`
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_odp_source.py tests/test_tushare_source.py tests/test_source_misc.py`

## Current Blockers

### Control Signal

- blockers: none before B0 evidence production.

### Supporting Detail

- Live provider permission and historical replay proof remain blockers for later `1d` modeling, not blockers for producing the B0 report.
