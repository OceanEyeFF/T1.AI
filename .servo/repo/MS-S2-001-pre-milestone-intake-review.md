---
title: "MS-S2-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-S2-001"
updated: "2026-06-22T10:18:40+08:00"
updated_by: "codex"
---

# MS-S2-001 Pre-Milestone Intake Review

## Intake Status

- intake_status: ready
- request_summary: Programmer requested making post-MS-S1 direction item 1, "stock-pool stratification definition", the next Milestone plan.
- update_summary: Programmer confirmed using a TuShare cache-first, quota-aware analysis method, then requested adding an A2 testing stage and explicitly planning around the known TuShare 1H frequency wall with suitable time-waiting / resume execution strategy.
- programmer_confirmed: true
- ready_for_init_milestone: true
- intake_skipped: false
- residual_risk_accepted: false
- accepted_residual_risk: N/A

## Observed Facts

- Current live milestone backlog has no active or planned milestone before this registration.
- `MS-S1-001` is completed and accepted with residual risk; no model or `alpha_score` signal was promoted.
- Post-MS-S1 direction note says stock-pool stratification definition and large-cap low-control-probability 3/5/10d revalidation should be split into separate future Milestones.
- Existing stock-pool module has S1 minimal registry/export support under `src/ashare_lab/stock_pool/` and `configs/stock_pools/`.
- Existing stock-pool development plan records Phase S2 as first pool-family support and says it remains incomplete.
- Existing TuShare source adapter exposes daily bars, `daily_basic`, `moneyflow`, and `adj_factor` loaders with partitioned cache and incremental fetch behavior in `src/ashare_lab/data/tushare_source.py`.
- Existing dataset config already records rate-related knobs such as `request_interval_seconds` and page sleep fields, so MS-S2 should preserve rate-limit configurability instead of hard-coding request pacing.
- Programmer judged the current TuShare database likely sufficient for this Milestone, with explicit caution that acquisition strategy and analysis strategy must account for hourly request limits.
- Programmer stated TuShare has a known 1H frequency wall, so A2 must plan time-waiting and related execution strategy before data acquisition.
- Programmer stated A2 should include a testing stage before execution.

## Inferred Assumptions

- This Milestone should define and register stock-pool stratification contracts before model revalidation.
- The Milestone should focus on reproducible pool definitions and sample registry entries, not on prediction retraining or signal promotion.
- The later "large-cap low-control-probability 3/5/10d revalidation" direction should depend on this Milestone output instead of being bundled into it.
- TuShare `daily_basic`, daily OHLCV, and optionally `moneyflow` should be enough for a first proxy-based stratification contract if used cache-first and with dry-run request estimates.
- "Low-control-probability" should be treated as a proxy candidate label, not as a proven behavioral truth.
- A2 should validate fetch scheduling behavior with no-network or quota-free tests before any quota-consuming request is considered.

## Unknowns

- Exact production-grade thresholds for "low-control-probability" are intentionally deferred; MS-S2 should freeze first-pass proxy windows and versioning rules rather than claim production-grade thresholds.
- Exact provider/source for any direct control-probability field is not confirmed; TuShare-derived proxy fields are allowed only as proxy evidence.
- Whether each stratified sample pool will have enough eligible symbols depends on existing or later data availability.
- Actual hourly TuShare request quota and token permission level are not recorded in repo truth; Worktrack execution must use configurable quota parameters and dry-run manifests.
- Exact wait duration and resume checkpoint format are implementation details for A2, but the strategy must explicitly model the 1H frequency wall.

## Programmer Decisions Required

- No additional blocking decision is required for backlog-only Milestone registration or this plan update.
- Before any Worktrack execution, each Worktrack still needs its own intake, contract, validation scope, and approval boundary.
- Any live TuShare call that may consume quota requires explicit Worktrack-level approval or a dry-run/cache-only contract; this review does not grant production/external side-effect authority.
- A2 test evidence is required before A3 sample-pool construction may rely on any quota-consuming TuShare fetch path.

## Risk Flags

- data_boundary: medium; stock-pool definitions may depend on provider-specific market-cap, turnover, liquidity, industry, and control-proxy fields.
- scope_creep: medium; model revalidation, retraining, and strategy promotion must remain out of scope.
- reproducibility: medium; pool definitions must be versioned and must not rely on hand-picked symbol lists.
- quota_boundary: medium; TuShare hourly request limits require cache coverage checks, dry-run request estimation, pacing parameters, and blocked-by-quota evidence.
- execution_timing_boundary: medium; known 1H frequency wall requires explicit time-waiting, resume checkpoint, and operator-visible progress behavior.

## Open Questions

- none blocking for planning registration.

## Recommended Answers

- recommended_scope: define stratified stock-pool families, TuShare proxy fields, cache-first acquisition rules, quota-aware dry-run manifests, A2 fetch-strategy tests, and minimal registry samples first.
- tradeoff: this delays direct model revalidation and avoids broad live data pulls, but creates stable comparable pools and a request-budget contract for later research.

## Scope Boundary

- In scope:
  - Stock-pool stratification taxonomy and naming contract.
  - TuShare cache-first acquisition strategy, request-budget manifest, and blocked-by-quota / blocked-by-data evidence rules.
  - A2 test evidence for request budget dry-run, cache hit behavior, 1H frequency-wall time-waiting, resume, and blocked-by-quota branches.
  - Proxy field mapping for large-cap / mid-small-cap, low-control-proxy candidates, and suspected-control / small-cap observation pools.
  - Minimal registry samples for required stratification families.
  - Validation of registry loading/export and metadata traceability.
  - Documentation of how later model revalidation should consume these pools.
- Out of scope:
  - 3/5/10d model retraining or promotion.
  - `alpha_score` optimization or default enabling.
  - Decision-model integration, trading logic, live provider calls, production scheduling, release, tag, push.
  - Full control-behavior modeling for small-cap or suspected-control pools.
  - Minute-level `stk_mins` acquisition or 1d intraday modeling.
  - Unapproved broad TuShare refreshes or quota-consuming calls outside a Worktrack contract.

## Acceptance Signals

- stratification_taxonomy_defined: stock-pool layers, pool families, stable IDs, versioning, and required fields are documented.
- proxy_method_defined: TuShare-derived proxy fields, windows, thresholds, and blocked-by-data conditions are documented without claiming true control probability.
- tushare_fetch_strategy_defined: cache-first, dry-run-first, gap-only fetch, configurable request pacing, and blocked-by-quota handling are documented.
- tushare_fetch_strategy_tested: A2 has no-network or quota-free test evidence for request budget dry-run, cache hit behavior, time-waiting, resume, and blocked-by-quota branches.
- registry_samples_available: at least one valid sample entry exists for each accepted first-pass family.
- export_smoke_passed: registry load/export smoke covers the new sample pools.
- downstream_contract_documented: later large-cap low-control-probability 3/5/10d revalidation has clear input pool contract and non-goals.
- no_model_promotion: no model, prediction head, or `alpha_score` is promoted by this Milestone.

## Suggested Milestone Brief

- milestone_id: MS-S2-001
- title: 股票池分层定义与注册契约
- purpose: 把后续研究所需的股票池分层从口头方向固化为可版本化、可导出、可被训练/评估链路引用的 registry contract，为后续大盘低控盘概率池 3/5/10d 复验提供稳定输入。
- milestone_kind: goal-driven
- depends_on_milestones: MS-S1-001
- priority: 3
- completion_threshold_pct: 100
- candidate_worktracks:
  - WT-S2-A1: 分层 taxonomy 与 proxy 边界冻结
  - WT-S2-A2: TuShare cache-first 获取策略、限流测试与 registry schema 差距检查
  - WT-S2-A3: 首批样例池构造、注册与导出 smoke
  - WT-S2-A4: 下游复验输入契约、请求预算与收尾报告

## Confirmation State

- confirmation_required: false
- confirmation_source: programmer messages on 2026-06-22, "先把1作为，我们的下一个MileStone规划。", "好，按照这个方法来改动我们的Worktrack规划", and "在开始之前，我觉得A2应该要有一个测试环节。另外已经知道了我们在TuShare上获取有1H的频率墙就要适当的合理安排我们的timewaiting等执行策略"
- milestone_review_gate_handoff:
  - review_status: effective_pass
  - milestone_review_count: 3
  - latest_review_checkpoint: MS-S2-001-intake-2026-06-22T10:18:40+08:00
  - effective_review_pass: true
  - review_invalidated_by: previous MS-S2-001-intake-2026-06-22T10:15:03+08:00 superseded by programmer-confirmed A2 testing and known TuShare 1H frequency-wall time-waiting strategy update.

## Handoff To Init Milestone

- handoff_to_init_milestone: ready
- template_contract_ref: pre-milestone-intake-review.template.md
- complex_project_entry_gate:
  - entry_verdict: not_applicable
  - reason: Backlog-only planning registration; later Worktracks may trigger data/provider safety review before execution.
- scanner_evidence_ref: N/A
- complexity_signals:
  - existing stock-pool module and docs available
  - data-source and provider assumptions deferred to Worktrack intake
- operator_safety_policy:
  - no_commit_or_push_without_programmer_approval: true
  - no_live_provider_call_without_programmer_approval: true
  - no_quota_consuming_tushare_call_without_worktrack_contract_or_explicit_approval: true
  - no_a3_quota_consuming_fetch_before_a2_fetch_strategy_tests: true
  - no_model_training_or_promotion_in_this_milestone: true
  - destructive_cleanup_forbidden_without_explicit_approval: true
- dialog_review_questions: []
- milestone_blocking_decision: []
- reinforcement_milestone_recommendation:
  - needed: false
  - recommendation_status: not_needed
  - recommendation_type: N/A
  - suggested_title: N/A
  - reason: Existing stock-pool module and registry baseline provide enough context for planning registration.
  - temporary_understanding_ref: .servo/repo/temporary-understanding.md
  - evidence_refs:
    - docs/modules/stock_pool_module_development_plan_20260311.md
    - docs/modules/stock_pool_registry_baseline_20260311.md
    - .servo/repo/post-ms-s1-direction-note.md
  - confirmation_required: false
  - blocks_implementation_until_resolved: false

## Skip Record

- skip_reason: N/A
- accepted_risk: N/A
