---
title: "MS-S0-001 / WT-C0-001 Pre-Worktrack Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-S0-001"
target_worktrack_id: "WT-C0-001"
updated: "2026-06-11T21:01:55+08:00"
owner: "OceanEyeFF"
---

# MS-S0-001 / WT-C0-001 Pre-Worktrack Intake Review

> This checkpoint prepares active milestone `MS-S0-001` for `WT-C0-001`. It authorizes a docs/research I/O draft only. It does not implement decision logic, train models, call providers, commit, push, or approve final milestone acceptance.

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
  - "WT-C0-001 may freeze a decision-model I/O draft while explicitly preserving that unverified alpha_score and 1d signals cannot create a tradable closed loop."
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
```

## Request Summary

```yaml
request_summary: "Prepare and execute WT-C0-001 after WT-B0-001 closed. The target is to freeze a bounded decision-model input/output draft that downstream work can consume later, without implementing trading logic or pretending current predictions are decision-ready."
```

## Observed Facts

- `MS-S0-001` is active and has completed `WT-A2-001`, `WT-A3-001`, and `WT-B0-001`.
- The milestone lists `WT-C0-001` as `决策模型 I/O 草案`.
- `docs/overview/three_track_development_plan_20260609.md#5` defines C0 as input/output protocol freeze only.
- Current decision-model input must include `alpha_score`, three-head contributions, optional `1d_signal`, current positions, costs, risk state, A-share constraints, and tradability state.
- Required outputs include target positions, orders or no-trade decision, risk checks, action reason, blocked reason, and diagnostics.
- Existing `docs/interfaces/protocol.md` defines close-signal to next-open execution, T+1, limit-up/down, risk buy disablement, and diagnostics.
- Existing `src/ashare_lab/strategy/portfolio.py` can compute simple target weights and has TODOs for rebalance threshold and cost coverage.
- Existing `src/ashare_lab/backtest/engine.py` already records diagnostics such as `buy_blocked_limit_up`, `sell_blocked_limit_down`, `sell_blocked_tplus1`, and `risk_buy_disabled`.
- Existing `src/ashare_lab/recommendation/engine.py` can generate mainline trend recommendations and diagnostics from aggregated trend scores.
- `WT-A2-001` and `WT-A3-001` did not promote any model to default decision-ready `alpha_score`.
- `WT-B0-001` concluded `1d` modeling remains blocked until live minute source proof exists.

## Inferred Assumptions

- The safest C0 slice is a schema/protocol draft in `.servo` evidence rather than canonical code or docs mutation.
- Decision I/O should include signal maturity and promotion status so downstream logic cannot accidentally treat research signals as tradable.
- C0 should define replay inputs and outputs, not optimization algorithms.

## Unknowns

- Exact future storage format for production decision logs.
- Final risk model and portfolio constraints beyond existing A-share protocol.
- Whether `alpha_score` will eventually pass A2/A3 gates in this milestone or stay candidate-only.

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: "D1"
    decision: "Final acceptance of MS-S0-001 after C0 and milestone composite gate."
    why_required: "The programmer explicitly reserved final milestone acceptance."
    recommended_resolution: "defer_to_milestone_gate"
    resolution: "deferred"
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: "R1"
    kind: "false_tradability"
    severity: "high"
    description: "A decision I/O draft must not make current candidate signals look production-ready."
  - id: "R2"
    kind: "scope_creep"
    severity: "medium"
    description: "C0 must stop before C1/C2 rebalance/cost/risk implementation."
  - id: "R3"
    kind: "interface_drift"
    severity: "medium"
    description: "Draft fields should align with existing protocol, recommendation, strategy, and backtest surfaces."
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  gate_id: "MS-S0-001-WT-C0-001-entry"
  target_repo: "T1.AI"
  target_milestone_id: "MS-S0-001"
  trigger_source: "pre-worktrack-intake"
  entry_verdict: "clear"
  scanner_evidence_ref: "docs/overview/three_track_development_plan_20260609.md#C0"
  complexity_signals:
    - signal: "decision_model_surface"
      threshold: "draft-only unless upstream prediction gates pass"
      observed_value: "C0 can freeze I/O without changing trading logic"
      confidence: "high"
      rationale: "Existing plan explicitly limits C0 to input/output protocol."
    - signal: "unverified_signal_risk"
      threshold: "candidate signals must carry maturity/status fields"
      observed_value: "A2/A3/B0 evidence keeps alpha_score and 1d as non-production"
      confidence: "high"
      rationale: "No model has been promoted by previous worktracks."
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
    allowed_high_risk_command_modes: "none for C0"
  dialog_review_questions: []
  milestone_blocking_decision:
    - "allow_derive_worktrack"
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: "not_needed"
    recommendation_type: "N/A"
    suggested_title: "N/A"
    suggested_purpose: "N/A"
    recommendation_reason: "Existing interface/protocol docs and strategy/backtest modules are enough to scope a C0 I/O draft."
    temporary_understanding_ref: null
    evidence_refs:
      - "docs/overview/three_track_development_plan_20260609.md"
      - "docs/interfaces/protocol.md"
      - "docs/modules/system_io_and_architecture_spec.md"
      - "src/ashare_lab/strategy/portfolio.py"
      - "src/ashare_lab/backtest/engine.py"
      - "src/ashare_lab/recommendation/engine.py"
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs:
    - ".servo/milestone/MS-S0-001.md"
    - ".servo/worktrack/b0-closeout-report.md"
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - "Draft decision-model input schema."
    - "Draft decision-model output schema."
    - "Define signal maturity and promotion status fields."
    - "Define replay determinism requirements for fixed CSV/Parquet input."
    - "Map C0 fields to existing protocol/recommendation/strategy/backtest surfaces."
  out_of_scope:
    - "Implementing decision model code."
    - "Changing PortfolioManager, BacktestEngine, recommendation engine, configs, or production behavior."
    - "Adding C1/C2/C3 logic such as rebalance threshold, cost coverage, risk buy disablement, or portfolio learning."
    - "Promoting alpha_score or 1d_signal."
    - "Model training, external provider calls, commit, push, release, or tags."
```

## Acceptance Signals

```yaml
acceptance_signals:
  - "Decision input and output fields are explicitly listed."
  - "Draft states that alpha_score may be candidate-only and must carry maturity status."
  - "1d_signal is optional and disabled by default after B0."
  - "Outputs include target_positions, orders/no-trade, risk_checks, action_reason, blocked_reason, and diagnostics."
  - "Draft can be replayed from fixed CSV/Parquet inputs without hidden model execution."
```

## Worktrack Readiness Review

```yaml
worktrack_intake_review:
  worktrack_id: "WT-C0-001"
  milestone_id: "MS-S0-001"
  repo_fundamentals: "pass: existing protocol, recommendation, portfolio, and backtest surfaces are available for I/O alignment."
  snapshot_freshness: "pass: snapshot records WT-A2/WT-A3/WT-B0 closed and C0 planned."
  milestone_purpose_alignment: "pass: C0 satisfies the milestone completion signal decision_io_draft_bounded."
  historical_conflict_risk: "low: C0 is draft-only and preserves no-promotion rules."
  worktrack_adjustment_recommendations: "execute as docs/research draft; no implementation."
  add_remove_worktrack_recommendations: "none."
  intake_review_verdict: "ready_for_worktrack_init"
  ready_for_worktrack_init: true
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  milestone_id: "MS-S0-001"
  target_worktrack_id: "WT-C0-001"
  review_status: "effective_pass"
  milestone_review_gate_ready: true
  latest_review_status: "effective_pass"
  milestone_review_count_increment: 1
  latest_review_checkpoint: "MS-S0-001-WT-C0-001-intake-2026-06-11T21:01:55+08:00"
  effective_review_pass: true
  review_invalidated_by: []
  allowed_next_route: "WorktrackScope.Init for WT-C0-001 on the active MS-S0-001 milestone branch"
```

## Handoff To Init Worktrack

```yaml
handoff_to_init_worktrack:
  allowed: true
  handoff_reason: "WT-C0-001 can start as a docs/research I/O draft Worktrack."
  next_route: "WorktrackScope.Init for WT-C0-001"
```
