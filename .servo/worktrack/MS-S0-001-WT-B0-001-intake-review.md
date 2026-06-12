---
title: "MS-S0-001 / WT-B0-001 Pre-Worktrack Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-S0-001"
target_worktrack_id: "WT-B0-001"
updated: "2026-06-11T21:01:55+08:00"
owner: "OceanEyeFF"
---

# MS-S0-001 / WT-B0-001 Pre-Worktrack Intake Review

> This checkpoint prepares active milestone `MS-S0-001` for the read-only `WT-B0-001` intraday data feasibility worktrack. It does not initialize a live provider pull, train a model, commit, push, or approve final milestone acceptance.

## Intake Status

```yaml
intake_status: "ready"
programmer_confirmed: true
ready_for_init_milestone: true
ready_for_worktrack_init: true
confirmation_required: false
intake_skipped: false
skip_reason: null
residual_risk_accepted: true
accepted_residual_risk:
  - "WT-B0-001 is allowed as a read-only feasibility/reporting slice. It may conclude that 1d modeling remains blocked if no source is proven to support fixed-pool fixed-window minute replay."
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
```

## Request Summary

```yaml
request_summary: "Prepare and execute WT-B0-001 after WT-A2-001 and WT-A3-001 closed. The target is to verify whether the 1d independent line has a credible intraday/minute data source path before any 1d modeling expansion."
```

## Observed Facts

- `MS-S0-001` is active and has completed `WT-A2-001` and `WT-A3-001`.
- The milestone explicitly lists `WT-B0-001` as `1d 日内数据源可用性验证`.
- The milestone scope keeps `1d` independent and forbids feeding `1d` into default `alpha_score`.
- `docs/overview/three_track_development_plan_20260609.md#4.3` defines B0 as a data-source feasibility report, not a modeling task.
- B0 required fields are `open/high/low/close/volume/amount/time`, with frequencies `1min/5min/15min`.
- Existing code has AkShare and TuShare daily loaders, but no dedicated minute/intraday A-share loader.
- `src/ashare_lab/data/odp_source.py` has an interval-aware historical loader and parquet cache, but it is not a validated A-share minute replay contract.
- `docs/interfaces/data_contract.md` currently defines only Daily Bars, not an intraday/minute schema.
- Public TuShare documentation says `stk_mins` supports historical A-share minute data and requires separate minute permission.
- Public AkShare documentation and issue evidence indicate stock minute interfaces are suitable for recent-data smoke tests, not long-term OOS by default.
- SubAgent explorer `019eb6c0-add4-7a50-8fb7-f1e83db7713b` independently confirmed the repo lacks a minute replay implementation and did not modify files.

## Inferred Assumptions

- The safest B0 slice is evidence/report-only: source comparison, repo capability inventory, and a go/blocked/conditional data gate.
- Live provider smoke is useful later, but it is an external side effect and should remain approval-gated.
- A positive B0 data gate requires at least one source that can support fixed stock pool plus fixed historical window replay with minute-level bars.

## Unknowns

- Whether the current TuShare account has `stk_mins` minute permission.
- Whether provider-side rate limits, fees, and call latency are acceptable for the target stock pool and history window.
- Whether AkShare's current live behavior in this environment matches the public documentation for the desired symbols.
- Whether ODP/OpenBB can provide reliable A-share minute data for the target pool.

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: "D1"
    decision: "Whether to approve a later live provider smoke test using TuShare/AkShare/ODP credentials or network calls."
    why_required: "B0 in this execution cycle is read-only and must not consume credentials, provider quotas, paid calls, or external API side effects."
    recommended_resolution: "defer_live_smoke_until_after_report"
    resolution: "deferred"
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: "R1"
    kind: "provider_permission"
    severity: "high"
    description: "TuShare stk_mins is the most credible long-history candidate but requires separate minute permission."
  - id: "R2"
    kind: "history_depth"
    severity: "high"
    description: "AkShare minute APIs are documented/observed as recent-data interfaces and cannot be assumed to support long OOS replay."
  - id: "R3"
    kind: "schema_gap"
    severity: "medium"
    description: "The repo has no formal minute data contract or replay validator yet."
  - id: "R4"
    kind: "scope_contamination"
    severity: "medium"
    description: "1d must remain independent and must not enter mainline alpha_score until data feasibility and later model gates pass."
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  gate_id: "MS-S0-001-WT-B0-001-entry"
  target_repo: "T1.AI"
  target_milestone_id: "MS-S0-001"
  trigger_source: "pre-worktrack-intake"
  entry_verdict: "clear"
  scanner_evidence_ref: "docs/overview/three_track_development_plan_20260609.md#B0"
  complexity_signals:
    - signal: "external_provider_side_effect"
      threshold: "no live provider calls without explicit approval"
      observed_value: "B0 can complete by reading docs, code, and public provider documentation"
      confidence: "high"
      rationale: "The milestone asks for feasibility first; live smoke can be separated."
    - signal: "data_contract_gap"
      threshold: "do not start modeling until a minute replay source and schema are proven"
      observed_value: "Current repo has Daily Bars contract only"
      confidence: "high"
      rationale: "docs/interfaces/data_contract.md has no intraday schema."
  operator_safety_policy:
    docker_compose_permission: "blocked"
    database_migration_permission: "blocked"
    deploy_network_permission: "blocked"
    destructive_cleanup_permission: "blocked"
    secrets_policy: "do not read, print, create, or transmit provider tokens"
    protected_paths:
      - "data/raw"
      - "data/cache"
      - "output/checkpoints"
      - "provider credentials"
    protected_branches:
      - "develop"
      - "main"
    allowed_high_risk_command_modes: "none for B0"
  dialog_review_questions: []
  milestone_blocking_decision:
    - "allow_derive_worktrack"
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: "not_needed"
    recommendation_type: "N/A"
    suggested_title: "N/A"
    suggested_purpose: "N/A"
    recommendation_reason: "Existing milestone and planning documents are sufficient to scope a read-only data feasibility worktrack."
    temporary_understanding_ref: null
    evidence_refs:
      - "docs/overview/three_track_development_plan_20260609.md"
      - "docs/research/1d_independent_model_research_plan.md"
      - "docs/research/1d_independent_model_execution_strategy_20260309.md"
      - "docs/interfaces/data_contract.md"
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs:
    - ".servo/milestone/MS-S0-001.md"
    - ".servo/repo/snapshot-status.md"
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - "Inventory existing repo adapters, contracts, configs, tests, and docs related to minute/intraday data."
    - "Compare TuShare stk_mins, AkShare minute APIs, ODP/OpenBB, and other professional data candidates from public/provider documentation."
    - "Produce a human-readable feasibility report and a machine-readable matrix."
    - "Decide whether the 1d line is data-ready, conditionally ready, or blocked for modeling."
  out_of_scope:
    - "Live provider API calls, credential checks, paid quota consumption, or production/network side effects."
    - "Implementing a minute loader, cache migration, or replay engine."
    - "Training or evaluating any 1d model."
    - "Changing mainline alpha_score, decision-model behavior, dependency versions, commits, pushes, releases, or tags."
```

## Non Goals

```yaml
non_goals:
  - "Do not use day-K-only evidence to approve 1d ultra-fast modeling."
  - "Do not claim AkShare is sufficient for long OOS replay without live and historical coverage proof."
  - "Do not treat ODP interval support as A-share minute replay proof."
  - "Do not implement B1 labels/features or B2 models in this worktrack."
```

## Acceptance Signals

```yaml
acceptance_signals:
  - "B0 feasibility report exists and covers TuShare, AkShare, ODP/OpenBB, and other candidates."
  - "Machine-readable matrix records permissions, coverage, history depth, frequency, fields, replay suitability, and blockers."
  - "Repo capability inventory states whether current code already supports minute replay."
  - "The data gate conclusion explicitly says data_ready / conditional / blocked and preserves 1d independence."
```

## Worktrack Readiness Review

```yaml
worktrack_intake_review:
  worktrack_id: "WT-B0-001"
  milestone_id: "MS-S0-001"
  repo_fundamentals: "pass: active milestone, three-track plan, 1d research docs, data source modules, and daily data contract exist."
  snapshot_freshness: "pass: snapshot records WT-A2-001 and WT-A3-001 closed and 1d blocked on intraday/minute feasibility."
  milestone_purpose_alignment: "pass: B0 satisfies the milestone completion signal one_day_data_feasibility_report_available."
  historical_conflict_risk: "low: B0 is read-only and does not modify A2/A3 mainline prediction gates."
  worktrack_adjustment_recommendations: "execute as read-only feasibility/reporting; defer live provider smoke and implementation."
  add_remove_worktrack_recommendations: "none."
  intake_review_verdict: "ready_for_worktrack_init"
  ready_for_worktrack_init: true
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  milestone_id: "MS-S0-001"
  target_worktrack_id: "WT-B0-001"
  review_status: "effective_pass"
  milestone_review_gate_ready: true
  latest_review_status: "effective_pass"
  milestone_review_count_increment: 1
  latest_review_checkpoint: "MS-S0-001-WT-B0-001-intake-2026-06-11T21:01:55+08:00"
  effective_review_pass: true
  review_invalidated_by: []
  allowed_next_route: "WorktrackScope.Init for WT-B0-001 on the active MS-S0-001 milestone branch"
```

## Handoff To Init Worktrack

```yaml
handoff_to_init_worktrack:
  allowed: true
  handoff_reason: "WT-B0-001 can start as a read-only source feasibility Worktrack under the active MS-S0-001 milestone branch."
  next_route: "WorktrackScope.Init for WT-B0-001"
```
