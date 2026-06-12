# Pre-Milestone Intake Review Template

> Use this template when `pre-milestone-intake-skill` needs to organize a before-start question review before `init-milestone-skill` may create, update, or activate a milestone. This template is an output scaffold, not a long-term truth source.

## Intake Status

```yaml
intake_status: "questions_required | ready | blocked | skipped"
programmer_confirmed: false
ready_for_init_milestone: false
confirmation_required: true
intake_skipped: false
skip_reason: null
accepted_risk: []
residual_risk_accepted: false
accepted_residual_risk: []
template_contract_ref: "product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
```

## Request Summary

```yaml
request_summary: ""
```

## Observed Facts

`observed_facts`:

Facts must be directly supported by programmer input, repo artifacts, or explicitly cited checks.

- N/A

## Inferred Assumptions

`inferred_assumptions`:

Assumptions are model inferences. Do not write them as programmer-confirmed truth.

- N/A

## Unknowns

`unknowns`:

Unknowns are unresolved facts that could affect scope, risk, acceptance, or ownership.

- N/A

## Programmer Decisions Required

`programmer_decisions_required`:

Decisions in this section cannot be inferred by the agent. They must be confirmed by the programmer or represented as a blocked/skipped intake.

```yaml
programmer_decisions_required:
  - id: "D1"
    decision: ""
    why_required: ""
    blocks_ready: true
```

## Risk Flags

```yaml
risk_flags:
  - id: ""
    kind: "scope_creep | release_boundary | migration | compatibility | security | data | weak_docs | multi_repo | governance_gap | complex_project | other"
    severity: "low | medium | high"
    description: ""
```

## Complex Project Entry Gate

Use this section when complex-project, weak-doc, multi-system, migration, deploy, security, data, destructive, or authority-sensitive signals affect Milestone entry. This is a Milestone-side blocking gate, not fixed heavy mode. Scanner output is evidence, not verdict. Canonical guard term: scanner output is evidence.

Candidate high-risk command mode values are `normal`, `autoreview`, and `yolo`, but they are programmer-owned answers and not generated defaults.

```yaml
complex_project_entry_gate:
  gate_id: ""
  target_repo: ""
  target_milestone_id: ""
  trigger_source: "pre-milestone-intake"
  entry_verdict: "clear | needs_reinforcement_milestone | blocked | not_applicable"
  scanner_evidence_ref: null
  complexity_signals:
    - signal: ""
      threshold: ""
      observed_value: ""
      confidence: ""
      rationale: ""
  operator_safety_policy:
    docker_compose_permission: "unknown | allowed | blocked | requires_approval"
    database_migration_permission: "unknown | allowed | blocked | requires_approval"
    deploy_network_permission: "unknown | allowed | blocked | requires_approval"
    destructive_cleanup_permission: "unknown | allowed | blocked | requires_approval"
    secrets_policy: "unknown"
    protected_paths: []
    protected_branches: []
    allowed_high_risk_command_modes: "pending_programmer_confirmation"
  dialog_review_questions:
    - id: "CG1"
      question: ""
      why_it_matters: ""
      recommended_answer: ""
      tradeoff: ""
      blocks_ready: true
  milestone_blocking_decision:
    - "block_create | block_upsert | block_activate | block_derive_worktrack | allow_create | allow_upsert | allow_activate | allow_derive_worktrack"
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: "not_needed | recommended | required | pending_operator_review"
    recommendation_type: "reinforcement_documentation | project_understanding | N/A"
    suggested_title: ""
    suggested_purpose: ""
    recommendation_reason: ""
    temporary_understanding_ref: null
    evidence_refs: []
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs: []
```

unresolved gate blocking default: missing, blank, placeholder, `pending_programmer_confirmation`, or incomplete `complex_project_entry_gate` fields must not be treated as clear or `not_applicable`. Consumers should default unresolved gate handoff to `entry_verdict: blocked` and `milestone_blocking_decision: block_create, block_upsert, block_activate, block_derive_worktrack` until programmer confirmation or verified evidence exists.

When weak docs or insufficient project understanding are the blocking factor, set `entry_verdict: needs_reinforcement_milestone`, keep implementation-oriented Worktrack derivation blocked, and populate `reinforcement_milestone_recommendation` as a structured handoff for a reinforcement documentation / project-understanding Milestone. The recommendation may reference `.servo/repo/temporary-understanding.md`, but temporary understanding remains runtime evidence only and not Goal Charter truth until programmer confirmation or verified evidence exists.

Use `recommendation_status: not_needed` only when `needed: false` and `blocks_implementation_until_resolved: false`; use `recommended`, `required`, or `pending_operator_review` for blocking or unresolved weak-doc routes.

## Open Questions

Ask only the highest-leverage questions needed before initialization. In continuous intake mode, ask exactly one blocking question in this section and mirror it in `next_required_question`. Each question must include why it matters, a recommended answer, and the tradeoff if the recommendation is wrong.

```yaml
open_questions:
  - id: "Q1"
    question: ""
    why_it_matters: ""
    recommended_answer: ""
    tradeoff: ""
    blocks_ready: true
```

## Continuous Intake State

Use this section when `intake_status: questions_required`. A questions-required checkpoint is a continuation handoff, not a pass. Continue one-question-at-a-time until the review reaches `effective_pass`, `blocked`, `skipped`, or residual risk is explicitly accepted without changing scope, non-goals, acceptance, or risk boundary.

```yaml
continuation_state:
  continuation_required: true
  continuation_round: 1
  continuation_reason: ""
  answered_questions:
    - id: ""
      answer_summary: ""
      answered_at: null
      source: "programmer | repo_evidence"
  unresolved_questions:
    - id: "Q1"
      question: ""
      blocks_ready: true
  next_required_question:
    id: "Q1"
    question: ""
    why_it_matters: ""
    recommended_answer: ""
    tradeoff: ""
  next_question_blocks_ready: true
  residual_risk_accepted: false
  accepted_residual_risk: []
```

If `questions_required`, `open_questions` must contain exactly one blocking question and `milestone_review_gate_handoff.review_status` must be `questions_required` with `effective_review_pass: false` and `milestone_review_count_increment: 0`.

## Recommended Answers

```yaml
recommended_answers:
  Q1:
    answer: ""
    impact_if_accepted: ""
    impact_if_rejected: ""
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - ""
  out_of_scope:
    - ""
```

## Non Goals

```yaml
non_goals:
  - ""
```

## Acceptance Signals

```yaml
acceptance_signals:
  - ""
```

## Suggested Milestone Brief

This brief is a draft. It is not a milestone artifact until `init-milestone-skill` consumes a confirmed intake review.

```yaml
suggested_milestone_brief:
  title: ""
  purpose: ""
  milestone_kind: "goal-driven"
  candidate_worktracks:
    - worktrack_id: ""
      title: ""
      purpose: ""
  completion_signals:
    - ""
  acceptance_criteria:
    - ""
  completion_threshold_pct: 100
```

## Confirmation State

```yaml
confirmation_state:
  confirmation_required: true
  programmer_confirmed: false
  confirmed_answers: []
  residual_risk: []
  residual_risk_accepted: false
  accepted_residual_risk: []
```

## Skip Record

Use this section only when the programmer explicitly asks to skip intake and accepts the risk. A skipped intake must not be represented as ready.

```yaml
skip_record:
  intake_skipped: false
  skip_reason: null
  accepted_risk: []
  ready_for_init_milestone: false
```

## Handoff To Init Milestone

```yaml
handoff_to_init_milestone:
  allowed: false
  handoff_reason: ""
  required_inputs:
    - "programmer_confirmed = true"
    - "ready_for_init_milestone = true"
  blocked_by: []
```

## Milestone Review Gate Handoff

Use this section when the intake review is intended to satisfy the Milestone execution-entry review gate. A skipped, questions-required, blocked, missing, stale, invalidated, or incomplete intake is not a review pass.
Changing `worktrack_list`, `completion_signals`, `acceptance_criteria`, scope/non-goals, or risk boundary invalidates the previous review checkpoint.

```yaml
milestone_review_gate_handoff:
  target_milestone_id: ""
  review_status: "effective_pass | questions_required | blocked | skipped | missing | stale | invalidated"
  milestone_review_count_increment: 0
  latest_review_status: "missing"
  latest_review_checkpoint: null
  latest_review_ref: null
  effective_review_pass: false
  review_invalidated_by:
    worktrack_list_changed: false
    completion_signals_changed: false
    acceptance_criteria_changed: false
    scope_or_non_goals_changed: false
    risk_boundary_changed: false
  blockers:
    - "programmer_confirmed = true"
    - "ready_for_init_milestone = true"
    - "intake_skipped = false"
    - "questions_required must continue one-question-at-a-time before pass"
```

Only `review_status: effective_pass` with `effective_review_pass: true`, a non-empty `latest_review_checkpoint`, `programmer_confirmed: true`, `ready_for_init_milestone: true`, and `intake_skipped: false` may increment `milestone_review_count`. All other statuses must block Worktrack Init/Dispatch until a fresh pre-milestone-intake review exists.
