---
title: "WT-S2-A2-next Worktrack Contract"
artifact_type: "worktrack-contract"
updated: "2026-06-22T11:12:24+08:00"
owner: "OceanEyeFF"
---

# WT-S2-A2-next Worktrack Contract

> This contract binds the narrowing step between A2 and A3. It compresses A1 output into the only A3 input contract.

## Metadata

- worktrack_id: WT-S2-A2-next
- title: A1 产出压缩与 A3 输入窄化
- branch: milestone/MS-S2-001-stock-pool-stratification
- baseline_branch: develop
- baseline_ref: 1204de8e7a685c0624c2d8a13aa1e7a0c9890bed
- owner: OceanEyeFF
- updated: 2026-06-22T11:12:24+08:00
- contract_status: initialized

## Branch Policy

- baseline_branch: develop
- branch_source_ref: develop@1204de8e7a685c0624c2d8a13aa1e7a0c9890bed
- worktrack_branch: milestone/MS-S2-001-stock-pool-stratification
- integration_target_ref: milestone/MS-S2-001-stock-pool-stratification
- closeout_target_ref: milestone/MS-S2-001-stock-pool-stratification
- final_baseline_branch: develop
- checkpoint_base_ref: 1204de8e7a685c0624c2d8a13aa1e7a0c9890bed
- branch_policy_note: This Worktrack runs on the single active MS-S2 milestone branch. It does not authorize push, merge to `develop`, branch deletion, release, provider calls, model retraining, or A2/A3 execution.

## Milestone Binding

- milestone_id: MS-S2-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-S2-001.md
- milestone_history: .servo/repo/milestone-history.md
- worktrack_intake_review: .servo/worktrack/MS-S2-001-WT-S2-A2-next-intake-review.md
- programmer_authorization: User requested an A2-next step before A3 to compress A1 output because A1 had over-expansion risk.

## Node Type

- type: design/docs
- primary_type: docs
- source_from_goal_charter: .servo/goal-charter.md#Engineering-Node-Map
- baseline_form: report-or-doc-artifact-on-confirmed-milestone-branch
- merge_required: no direct merge in this Worktrack; milestone branch closeout remains separately gated.
- gate_criteria: compression contract review + no A3 execution + no provider-call policy evidence
- if_interrupted_strategy: preserve compression artifact and stop with handback notes

## Task Goal

- goal_summary: Compress A1 taxonomy into a narrow A3 input contract.
- full_goal: Preserve A1 as broad research background, but define the only layers, fields, names, and non-goals that A3 may consume so sample-pool construction cannot expand into small-cap, suspected-control, threshold tuning, or model-revalidation work.

## Scope

- scope_summary: A3 input contract compression only.
- in_scope:
  - create a compressed A3 input contract.
  - mark full A1 taxonomy as background evidence only.
  - defer mid/small-cap observation and suspected-control observation out of A3.
  - preserve quota, cache-first, dry-run-first, and no-signal-promotion boundaries.
- out_of_scope:
  - code implementation, live TuShare provider calls, quota-consuming fetches, sample-pool registration, export smoke, model revalidation, model retraining, signal promotion, push, merge, branch deletion, release/version action, or final milestone acceptance.

## Acceptance Criteria

- A3 input contract explicitly narrows A1 to base universe, liquid large-cap proxy, and at most one low-control-proxy candidate path.
- Mid/small-cap observation and suspected-control observation are deferred out of A3.
- A3 is instructed to consume the compressed contract, not the full A1 taxonomy.
- No quota-consuming provider call, model revalidation, or A3 sample construction occurs.

## Verification Requirements

- `git diff --check -- .servo docs src tests`
- `git diff --check -- .servo docs`
- Review compressed A3 input contract against A1/A2 evidence.
- Policy evidence that no quota-consuming TuShare call was made.

## Execution Policy

> Execution Policy canonical semantics are not repeated here. Runtime defaults are embedded below so installed skill packages do not need source-repo docs. Source-side authoring trace: `docs/harness/artifact/worktrack/contract.md#execution-policy`.

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes
