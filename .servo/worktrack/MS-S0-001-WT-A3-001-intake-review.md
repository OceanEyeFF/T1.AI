---
title: "MS-S0-001 / WT-A3-001 Pre-Worktrack Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-S0-001"
target_worktrack_id: "WT-A3-001"
updated: "2026-06-11T20:50:00+08:00"
owner: "OceanEyeFF"
---

# MS-S0-001 / WT-A3-001 Pre-Worktrack Intake Review

> This checkpoint prepares active milestone `MS-S0-001` for `WT-A3-001`. It does not initialize the Worktrack, execute model training, call data providers, commit, push, or approve final milestone acceptance.

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
  - "WT-A3-001 should first freeze and prioritize the optimization experiment queue under the A2 protocol; actual long-running retraining requires a later explicit execution slice."
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
```

## Request Summary

```yaml
request_summary: "Prepare intake for WT-A3-001 after WT-A2-001 closed. The target is to turn the A2 credibility protocol into a bounded prediction optimization experiment queue for LSTM, XGBoost, and possible lightweight fusion, without immediately running long model retraining."
```

## Observed Facts

- `MS-S0-001` is active and has completed `WT-A2-001`.
- `WT-A2-001` froze the A2 evaluation protocol in `docs/research/mainline_3510d_evaluation_gate_protocol.md`.
- `WT-A2-001` made `scripts/compare_ic_reports.py --check-protocol` block reports missing `evaluation_protocol`.
- Focused A2 validation passed: `75 passed`.
- Historical quick8 reports have complete OOS coverage but fail raw/calibrated strict credibility gates and sanity checks.
- `docs/research/multilevel_tuning_plan_20260307.md` already defines L1/L2/L3 tuning levels, dry-run mode, execution examples, and output artifacts.
- `docs/research/mainline_3510d_model_development_plan_20260310.md` says LSTM and XGBoost baselines are required before deeper aggregation or execution-layer reliance.
- Existing scripts include tuning/auto-tuning entry points, but actual execution can be CPU-expensive and should be scoped separately.

## Inferred Assumptions

- The safest first A3 slice is queue/protocol planning, not full training execution.
- A3 should prioritize same-window reproducibility, report contract compliance, and no-go/continue-research interpretation before compute-heavy reruns.
- LSTM/XGBoost/fusion candidates should be compared only after their reports satisfy the A2 protocol.

## Unknowns

- Which full-size mainline dataset path should become the authoritative A3 execution input.
- Whether A3 should run any training in this Worktrack or only produce the queue and dry-run manifests.
- Runtime budget for CPU-only reruns.

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: "D1"
    decision: "Whether WT-A3-001 may execute any actual model training, or should stay as queue/protocol/dry-run planning only."
    why_required: "Actual training changes runtime, generated artifacts, and approval risk. Planning-only can proceed safely and still prepares the optimization loop."
    recommended_resolution: "planning_queue_only_first"
    resolution: "planning_queue_only_first_by_conservative_default"
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: "R1"
    kind: "compute_scope"
    severity: "medium"
    description: "Full LSTM/XGBoost reruns may be long on CPU and should not be hidden inside intake or initial planning."
  - id: "R2"
    kind: "evidence_contamination"
    severity: "medium"
    description: "A3 must not compare reports that fail A2 protocol fields, windows, or anti-cheat prerequisites."
  - id: "R3"
    kind: "false_promotion"
    severity: "high"
    description: "A3 must not promote alpha_score based on quick8 samples, calibrated tricks, or missing anti-cheat surfaces."
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  gate_id: "MS-S0-001-WT-A3-001-entry"
  target_repo: "T1.AI"
  target_milestone_id: "MS-S0-001"
  trigger_source: "pre-worktrack-intake"
  entry_verdict: "clear"
  scanner_evidence_ref: ".servo/worktrack/a2-credibility-gate-report.md#A3-Handoff"
  complexity_signals:
    - signal: "compute_heavy_execution"
      threshold: "planning-only first unless runtime budget is explicitly approved"
      observed_value: "WT-A3-001 can start by freezing queue and dry-run commands"
      confidence: "high"
      rationale: "A2 protocol and existing tuning docs are enough to define queue without training."
    - signal: "strict_protocol_dependency"
      threshold: "all A3 candidates must satisfy A2 protocol before comparison"
      observed_value: "A2 gate protocol exists and strict protocol check is implemented"
      confidence: "high"
      rationale: "WT-A2-001 produced verified protocol and tests."
  operator_safety_policy:
    docker_compose_permission: "blocked"
    database_migration_permission: "blocked"
    deploy_network_permission: "blocked"
    destructive_cleanup_permission: "blocked"
    secrets_policy: "do not read, print, create, or transmit secrets"
    protected_paths:
      - "data/raw"
      - "output/checkpoints"
      - "production credentials"
    protected_branches:
      - "develop"
      - "main"
    allowed_high_risk_command_modes: "none for intake; model training requires explicit execution slice"
  dialog_review_questions: []
  milestone_blocking_decision:
    - "allow_derive_worktrack"
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: "not_needed"
    recommendation_type: "N/A"
    suggested_title: "N/A"
    suggested_purpose: "N/A"
    recommendation_reason: "WT-A2-001 produced enough protocol and evidence to scope A3 without a separate understanding milestone."
    temporary_understanding_ref: null
    evidence_refs:
      - ".servo/worktrack/a2-credibility-gate-report.md"
      - "docs/research/mainline_3510d_evaluation_gate_protocol.md"
      - "docs/research/multilevel_tuning_plan_20260307.md"
      - "docs/research/mainline_3510d_model_development_plan_20260310.md"
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs:
    - ".servo/milestone/MS-S0-001.md"
    - ".servo/worktrack/a2-credibility-gate-report.md"
    - ".servo/repo/snapshot-status.md"
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - "Freeze and prioritize the A3 optimization experiment queue under the A2 protocol."
    - "Define LSTM, XGBoost, and lightweight fusion candidate families."
    - "Map each candidate to report contract, OOS window, validation command, and gate interpretation."
    - "Produce dry-run or command-manifest evidence where safe."
    - "Keep alpha_score as candidate research signal unless later evidence passes A2/A3 gates."
  out_of_scope:
    - "Long-running model retraining unless a later explicit execution slice approves it."
    - "External data/provider calls."
    - "Dependency changes, environment repair, destructive cleanup, commit, push, release, or tags."
    - "1d data feasibility or decision-model implementation."
    - "Promoting any current quick8 result to decision-ready alpha."
```

## Non Goals

```yaml
non_goals:
  - "Do not rerun full LSTM/XGBoost training in the intake step."
  - "Do not compare reports that fail A2 protocol readiness."
  - "Do not treat calibrated improvement as sufficient without raw and anti-cheat support."
  - "Do not change the default alpha_score promotion state."
```

## Acceptance Signals

```yaml
acceptance_signals:
  - "A3 queue ranks experiments by risk, cost, and expected information value."
  - "Each candidate has A2 protocol prerequisites, report contract, validation commands, and go/no-go/continue-research interpretation."
  - "Dry-run manifests or command templates are available without training."
  - "Runtime-heavy execution is split into explicit later tasks with approval boundaries."
```

## Worktrack Readiness Review

```yaml
worktrack_intake_review:
  worktrack_id: "WT-A3-001"
  milestone_id: "MS-S0-001"
  repo_fundamentals: "pass: A2 protocol, tuning docs, training scripts, and validation scripts exist."
  snapshot_freshness: "pass: repo snapshot refreshed after WT-A2-001 closeout."
  milestone_purpose_alignment: "pass: WT-A3-001 implements the optimization queue after the credibility gate."
  historical_conflict_risk: "medium: historical quick8 reports fail gates and cannot be used as promotion evidence."
  worktrack_adjustment_recommendations: "start with planning/dry-run queue; defer actual training to explicit execution tasks."
  add_remove_worktrack_recommendations: "none."
  intake_review_verdict: "ready_for_worktrack_init"
  ready_for_worktrack_init: true
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  milestone_id: "MS-S0-001"
  target_worktrack_id: "WT-A3-001"
  review_status: "effective_pass"
  milestone_review_gate_ready: true
  latest_review_status: "effective_pass"
  milestone_review_count_increment: 1
  latest_review_checkpoint: "MS-S0-001-WT-A3-001-intake-2026-06-11T20:50:00+08:00"
  effective_review_pass: true
  review_invalidated_by: []
  allowed_next_route: "WorktrackScope.Init for WT-A3-001 on the active MS-S0-001 milestone branch"
```

## Handoff To Init Worktrack

```yaml
handoff_to_init_worktrack:
  allowed: true
  handoff_reason: "WT-A3-001 can start as a planning/dry-run queue Worktrack under the frozen A2 protocol."
  next_route: "WorktrackScope.Init for WT-A3-001"
```
