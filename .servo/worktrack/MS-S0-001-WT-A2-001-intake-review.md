---
title: "MS-S0-001 / WT-A2-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-S0-001"
target_worktrack_id: "WT-A2-001"
updated: "2026-06-11T19:53:25+08:00"
owner: "OceanEyeFF"
---

# MS-S0-001 / WT-A2-001 Pre-Milestone Intake Review

> This checkpoint prepares the active `MS-S0-001` milestone for its first planned Worktrack, `WT-A2-001`. It does not initialize a Worktrack, create a branch, modify code, run experiments, commit, push, or approve production/external side effects.

## Intake Status

```yaml
intake_status: "ready"
programmer_confirmed: true
ready_for_init_milestone: true
ready_for_worktrack_init: true
confirmation_required: false
intake_skipped: false
skip_reason: null
accepted_risk: []
residual_risk_accepted: true
accepted_residual_risk:
  - "No new model-performance numbers will be produced by WT-A2-001; it will first make evaluation evidence trustworthy."
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
```

## Request Summary

```yaml
request_summary: "Prepare intake for active milestone MS-S0-001 before starting the next milestone work. The immediate target is WT-A2-001: mainline 3d/5d/10d evaluation paradigm and false-signal gate. The programmer confirmed WT-A2-001 should first freeze evaluation/anti-cheat gates and audit historical report/OOS coverage, without model retraining."
```

## Observed Facts

- Programmer accepted `MS-ENV-000` completion and explicitly chose CPU-first continuation.
- `py311-private` is the canonical conda environment for CPU development/testing.
- `MS-S0-001` is active and has four planned Worktracks: `WT-A2-001`, `WT-A3-001`, `WT-B0-001`, and `WT-C0-001`.
- `WT-A2-001` is the first planned Worktrack and is titled `可信评估范式与伪信号排查`.
- `MS-S0-001` states that `alpha_score` must remain a candidate research signal until A2/A3 credibility gates pass.
- Existing repo code already contains:
  - `ashare_lab.evaluation.metrics` for Daily-CS IC / RankIC and monthly aggregation.
  - `ashare_lab.evaluation.sanity_checks` for shuffle labels, time reverse, and lag-1 sanity checks.
  - `ashare_lab.evaluation.trade_like_panel` for top-N equal-weight excess return style panels.
  - `scripts/audit_ic_reports.py` for OOS parquet coverage audit.
  - `scripts/compare_ic_reports.py` for same-window IC/monthly comparison and protocol consistency checks.
  - `scripts/run_sanity_checks.py` for aligned/OOS sanity-check reports.
- Existing tests cover evaluation metrics, sanity checks, trade-like panel, compare/audit scripts, maturity gate, and dynamic model heads.
- Current branch is still `milestone/MS-ENV-000-conda-env-validation`; control-state marks mutating `MS-S0-001` work as blocked until the configured next milestone branch is created or checked out.
- No Worktrack Contract exists for `WT-A2-001`.
- No commit or push has been approved.
- Programmer answered Q1 on 2026-06-11: do not retrain models; first solidify evaluation and false-signal gates.

## Inferred Assumptions

- The first `MS-S0-001` slice is confirmed as evaluation/anti-cheat protocol work before any CPU-bound reruns.
- Existing evaluation utilities are useful but may need a unifying protocol artifact/report contract before A3 optimization experiments are interpretable.
- Running full LSTM/XGBoost baseline refreshes on CPU is out of scope for `WT-A2-001`.

## Unknowns

- Which existing historical OOS reports are authoritative enough to audit without regeneration.
- Whether `WT-A2-001` should produce only documents/report contracts, or also add/adjust scripts/tests for a reproducible gate command.
- Whether branch creation for `MS-S0-001` should happen immediately after intake pass or wait for explicit Worktrack Init approval.

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: "D1"
    decision: "Choose the first WT-A2-001 scope mode: protocol/audit-only first, or include a limited baseline rerun."
    why_required: "This changes runtime cost, acceptance evidence, and whether the Worktrack is mainly docs/test/report-contract work or also experiment execution."
    resolution: "protocol_audit_only_first; no model retraining"
    answered_at: "2026-06-11T19:53:25+08:00"
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: "R1"
    kind: "scope_creep"
    severity: "low"
    description: "A2 is now explicitly bounded to evaluation-gate definition, historical report/OOS coverage audit, and anti-cheat protocol; model optimization and reruns remain out of scope."
  - id: "R2"
    kind: "data"
    severity: "medium"
    description: "Historical reports and OOS parquet availability may be incomplete or inconsistent; missing OOS evidence must not be treated as model failure."
  - id: "R3"
    kind: "compatibility"
    severity: "low"
    description: "CPU-first path is accepted; long model reruns may be slow and should be scoped intentionally."
  - id: "R4"
    kind: "governance_gap"
    severity: "low"
    description: "Current checked-out branch is the previous milestone branch; mutating next-milestone work needs the configured MS-S0-001 branch context."
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  gate_id: "MS-S0-001-WT-A2-001-entry"
  target_repo: "T1.AI"
  target_milestone_id: "MS-S0-001"
  trigger_source: "pre-milestone-intake"
  entry_verdict: "clear"
  scanner_evidence_ref: ".servo/repo/snapshot-status.md#Architecture-And-Module-Map"
  complexity_signals:
    - signal: "multi_track_research_boundary"
      threshold: "must keep 3d/5d/10d, 1d, and decision-model scopes separated"
      observed_value: "MS-S0-001 explicitly separates A2/A3/B0/C0"
      confidence: "high"
      rationale: "Scope separation is already recorded in the milestone artifact and goal charter."
    - signal: "external_side_effect_risk"
      threshold: "no production/external API calls in A2 intake"
      observed_value: "A2 can proceed from local reports/tests/protocol artifacts"
      confidence: "medium"
      rationale: "Existing evaluation scripts can consume local OOS artifacts; fresh data/provider calls are out of scope unless later approved."
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
    allowed_high_risk_command_modes: "none for this intake"
  dialog_review_questions: []
  milestone_blocking_decision:
    - "allow_derive_worktrack"
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: "not_needed"
    recommendation_type: "N/A"
    suggested_title: "N/A"
    suggested_purpose: "N/A"
    recommendation_reason: "Repo has enough evaluation code, tests, and planning artifacts to scope WT-A2-001 without a separate understanding milestone."
    temporary_understanding_ref: null
    evidence_refs:
      - ".servo/milestone/MS-S0-001.md"
      - "docs/research/research_checklist.md"
      - "docs/research/警惕伪信号.md"
      - "src/ashare_lab/evaluation"
      - "scripts/compare_ic_reports.py"
      - "scripts/run_sanity_checks.py"
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs:
    - ".servo/milestone/MS-S0-001.md"
    - ".servo/repo/analysis.md"
    - ".servo/repo/snapshot-status.md"
```

## Open Questions

```yaml
open_questions:
  - none
```

## Continuous Intake State

```yaml
continuation_state:
  continuation_required: false
  continuation_round: 2
  continuation_reason: "Q1 answered by programmer; intake can pass."
  answered_questions:
    - id: "Q1"
      answer_summary: "Use protocol/audit-only first: solidify evaluation and false-signal gates; do not retrain models."
      answered_at: "2026-06-11T19:53:25+08:00"
      source: "programmer"
  unresolved_questions: []
  next_required_question: null
  next_question_blocks_ready: false
  residual_risk_accepted: true
  accepted_residual_risk:
    - "No new model-performance numbers will be produced by WT-A2-001; it will first make evaluation evidence trustworthy."
```

## Recommended Answers

```yaml
recommended_answers:
  Q1:
    answer: "protocol_audit_only_first"
    impact_if_accepted: "WT-A2-001 becomes a focused research/test/docs Worktrack: freeze evaluation protocol, audit OOS/report readiness, define anti-cheat gate commands, and produce go/no-go inputs for A3."
    impact_if_rejected: "If limited rerun is included, Worktrack must explicitly cap dataset/window/model count and runtime budget, and acceptance must distinguish environment/runtime failure from prediction credibility."
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - "Freeze A2 evaluation protocol for 3d/5d/10d Daily-CS IC / RankIC, monthly stability, and trade-like panel."
    - "Audit existing reports/OOS parquet readiness for strict same-window comparison."
    - "Define or verify anti-false-signal checks: shuffle labels, time reverse, lag-1, label maturity, transaction timing, and protocol consistency."
    - "Produce WT-A2 acceptance report with go/no-go/continue-research interpretation rules for alpha_score."
    - "Add or adjust focused tests/docs/scripts only if needed to make the gate reproducible."
  out_of_scope:
    - "A3 model optimization, hyperparameter search, feature expansion, or ensemble work."
    - "1d intraday data feasibility beyond noting B0 dependency."
    - "Decision-model implementation beyond respecting C0 boundary."
    - "Production API calls, data-provider spend, real trading, release, tag, commit, or push."
    - "Model retraining, including limited baseline rerun, because programmer confirmed WT-A2-001 should first solidify evaluation and false-signal gates."
```

## Non Goals

```yaml
non_goals:
  - "Do not promote alpha_score to decision-ready status during A2."
  - "Do not merge 1d signal into mainline scoring."
  - "Do not use high IC or monthly win rate as credible unless anti-false-signal checks pass."
  - "Do not treat missing historical OOS files as prediction failure without separating artifact availability from model quality."
  - "Do not create or switch branches until Worktrack Init or explicit branch instruction."
```

## Acceptance Signals

```yaml
acceptance_signals:
  - "A2 protocol states canonical metrics, windows, gates, and report inputs."
  - "Existing report/OOS coverage is audited, or concrete missing-artifact blockers are listed."
  - "Anti-false-signal checks are mapped to runnable commands or documented gaps."
  - "Label maturity and trade timing checks are included in the gate criteria."
  - "alpha_score promotion/no-go/continue-research interpretation is explicit."
  - "A3 receives a bounded input list instead of unstructured optimization ideas."
```

## Suggested Milestone Brief

```yaml
suggested_milestone_brief:
  title: "MS-S0-001 主线预测可信评估与优化闭环"
  purpose: "Prove or reject whether current 3d/5d/10d prediction evidence is credible enough to guide alpha_score optimization and later decision-model work."
  milestone_kind: "goal-driven"
  candidate_worktracks:
    - worktrack_id: "WT-A2-001"
      title: "可信评估范式与伪信号排查"
      purpose: "Freeze the mainline evaluation/anti-cheat protocol and audit existing evidence before optimization."
    - worktrack_id: "WT-A3-001"
      title: "预测优化实验队列"
      purpose: "Run prioritized optimization candidates only under the A2 protocol."
    - worktrack_id: "WT-B0-001"
      title: "1d 日内数据源可用性验证"
      purpose: "Keep 1d separate and validate intraday data feasibility."
    - worktrack_id: "WT-C0-001"
      title: "决策模型 I/O 草案"
      purpose: "Bound downstream decision inputs/outputs without implementing trading logic."
  completion_signals:
    - "evaluation_paradigm_frozen"
    - "false_signal_checks_defined_and_runnable"
    - "same_window_baseline_comparison_available"
    - "optimization_queue_prioritized"
    - "alpha_score_promotion_rules_defined"
    - "one_day_data_feasibility_report_available"
    - "decision_io_draft_bounded"
  acceptance_criteria:
    - "High IC or high monthly win rate must pass anti-false-signal gates before being treated as credible."
    - "A2/A3 must distinguish ranking skill from timing mismatch, sample selection, calibration tricks, and aggregation tricks."
    - "alpha_score remains a research candidate until credibility gates pass."
  completion_threshold_pct: 100
```

## Confirmation State

```yaml
confirmation_state:
  confirmation_required: false
  programmer_confirmed: true
  confirmed_answers:
    - "MS-ENV-000 accepted; CPU-first continuation accepted."
    - "MS-S0-001 is active and should begin with intake."
    - "WT-A2-001 should not retrain models; first solidify evaluation and false-signal gates."
  residual_risk:
    - "GPU training remains unavailable on local GTX 1080 Ti with current torch wheel."
    - "Historical OOS/report artifact coverage may be incomplete."
  residual_risk_accepted: true
  accepted_residual_risk:
    - "No new model-performance numbers will be produced by WT-A2-001; it will first make evaluation evidence trustworthy."
```

## Worktrack Readiness Review

```yaml
worktrack_intake_review:
  worktrack_id: "WT-A2-001"
  milestone_id: "MS-S0-001"
  repo_fundamentals: "pass: repo has evaluation metrics, sanity checks, trade-like panel code, audit/compare scripts, and tests."
  snapshot_freshness: "pass: repo snapshot was refreshed after MS-ENV-000 final acceptance."
  milestone_purpose_alignment: "pass: WT-A2-001 directly implements the first MS-S0-001 credibility gate."
  historical_conflict_risk: "medium: historical reports may use mixed metrics/protocols; A2 must audit before comparing."
  worktrack_adjustment_recommendations: "confirmed protocol/audit-only first; no model retraining in WT-A2-001."
  add_remove_worktrack_recommendations: "none."
  intake_review_verdict: "ready_for_worktrack_init"
  ready_for_worktrack_init: true
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  milestone_id: "MS-S0-001"
  target_worktrack_id: "WT-A2-001"
  review_status: "effective_pass"
  milestone_review_gate_ready: true
  latest_review_status: "effective_pass"
  milestone_review_count_increment: 1
  latest_review_checkpoint: "MS-S0-001-WT-A2-001-intake-2026-06-11T19:53:25+08:00"
  effective_review_pass: true
  review_invalidated_by: []
  allowed_next_route: "WorktrackScope.Init for WT-A2-001 after branch context is legal"
```

## Skip Record

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
  allowed: true
  handoff_reason: "Q1 answered; WT-A2-001 scope is confirmed as evaluation/anti-cheat protocol and historical report/OOS coverage audit, with no model retraining."
  next_route: "WorktrackScope.Init for WT-A2-001 after creating or switching to the configured MS-S0-001 milestone branch."
```
