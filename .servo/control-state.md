---
title: "Harness Control State"
artifact_type: "control-state"
generated_from: "servo-set-harness-goal-skill/assets/control-state.md"
updated: "2026-06-11"
owner: "OceanEyeFF"
---

# Harness Control State

> 这是 `.servo/control-state.md` 的运行状态，用来维护当前 Harness supervisor 的控制面状态，不承载业务真相。
> 每轮 Harness 启动必须先读取本文件，恢复 linked artifact、审批边界、自动性、交接守卫、基线追溯和预算配置。

## Metadata

- updated: 2026-07-22T14:16:00+08:00
- owner: OceanEyeFF
- refresh_note: WT-R4-A3 Init done; next Dispatch R4-A3-T1 (caps enforce; zero live)

## Current Control Level

- repo_scope: active
- worktrack_scope: active

## Active Worktrack

- active_worktrack: WT-R4-A3
- worktrack_status: initialized_awaiting_dispatch
- last_closed_worktrack: WT-R4-A2
- worktrack_contract: worktrack/WT-R4-A3-contract.md
- plan_task_queue: worktrack/WT-R4-A3-plan-task-queue.md
- worktrack_intake_review: worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- worktrack_init_result: worktrack/WT-R4-A3-init-result.md
- gate_evidence: N/A
- closeout_ref: N/A
- active_task_window: R4-A3-T1
- selected_next_action_id: R4-A3-T1
- worktrack_gate_verdict: N/A
- worktrack_blocker: none
- worktrack_residual_risk: soft80; 510300; caps_not_enforced_yet; live_needs_batch_approve
- execution_not_started: true

## Active Milestone

- active_milestone: MS-R4-001
- milestone_status: active
- milestone_kind: goal-driven
- milestone_artifact: milestone/MS-R4-001.md
- milestone_backlog: repo/milestone-backlog.md
- milestone_history: repo/milestone-history.md
- milestone_pipeline_summary:
  - active_count: 1
  - planned_count: 0
  - completed_count: 9
  - superseded_count: 0
  - note: MS-R4-001 active; WT-R4-A3 Init; next R4-A3-T1
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 1
- latest_review_checkpoint: MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00
- effective_review_pass: true
- next_milestone_route: Dispatch R4-A3-T1 then T2; live only after batch approve; no full-campaign / train / Phase4 / EXEC-002

## Baseline Branch

- baseline_branch: develop
- baseline_ref: 7453daaa7dc6275f27086bc74f3221927be415f4

## Branch Environment Guard

- current_branch_context: milestone
- expected_branch_context: milestone
- branch_context_guard_status: pass_with_caveat
- branch_context_required_ref: refs/heads/milestone/MS-R4-001-tushare-datalake
- active_milestone_branch: milestone/MS-R4-001-tushare-datalake
- active_milestone_branch_sync_state: tip 4474da9 (A2 close pin); A3 Init on same branch
- worktrack_branch: milestone/MS-R4-001-tushare-datalake
- observed_checkout: milestone/MS-R4-001-tushare-datalake @ 4474da9

## Current Next Action

- WT-R4-A3 **Init complete**. Next: **R4-A3-T1** — wire caps into fetch limiter (**zero live**). T3+ needs explicit live batch approve.

## Linked Formal Documents

- repo_snapshot: repo/snapshot-status.md
- repo_analysis: repo/analysis.md
- milestone_artifact: milestone/MS-R4-001.md
- milestone_backlog: repo/milestone-backlog.md
- milestone_history: repo/milestone-history.md
- pre_milestone_intake: repo/MS-R4-001-pre-milestone-intake-review.md
- planned_worktrack_backlog: repo/worktrack-backlog.md
- worktrack_contract: worktrack/WT-R4-A3-contract.md
- plan_task_queue: worktrack/WT-R4-A3-plan-task-queue.md
- gate_evidence: N/A
- closeout_ref: N/A
- worktrack_init_result: worktrack/WT-R4-A3-init-result.md
- worktrack_intake_review: worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- last_closed_worktrack_closeout: worktrack/WT-R4-A2-closeout.md
- completed_milestone_artifact: milestone/MS-T1-001.md

## Approval Boundary

- needs_programmer_approval: yes
- reason: Persistent Servo work habit controls are configured; commit, push, destructive cleanup, production/external side effects, dependency changes, release/version actions, final milestone acceptance, unapproved scope expansion, and Worktrack Init outside confirmed active milestone/intake remain approval-gated.
- approval_scope: commit, push, destructive operation, production/external side effect, dependency install/upgrade, release/version action, final milestone acceptance, scope expansion, and any branch/worktree action outside the configured one-development-branch-per-confirmed-milestone policy.
- approval_persistence: persistent_work_habits_confirmed_on_2026-06-10
- milestone_brief_confirmation: received for MS-ENV-000 and MS-S0-001 only; does not approve Worktrack Init, code mutation, package installation, environment repair, commit, push, or production actions.
- one_shot_repair_confirmation: received on 2026-06-11 for WT-ENV-001 py311-private dependency repair and environment-contract migration only; does not approve commit, push, destructive cleanup, production/external side effects, release/version actions, or final milestone acceptance.
- final_acceptance_MS_ENV_000: received on 2026-06-11T16:40:59+08:00; accepted CPU-first continuation and non-blocking GPU residual risk.
- final_acceptance_MS_S0_001: received on 2026-06-12T01:28:03+08:00; accepted evaluation/guardrail/planning milestone with residual risk and no model promotion.
- final_acceptance_MS_S2_001: received on 2026-06-22T12:45:00+08:00; accepted stock-pool stratification milestone with all 5 worktracks pass, 11/11 completion signals, 9/10 acceptance criteria. Commit: 98ef372.
- final_acceptance_MS_R0_001: received on 2026-06-23T00:00:00+08:00; accepted selection-layer refactor. 4/4 worktracks (A1-A4), 8/8 completion signals, 6/6 acceptance criteria, 402/402 tests pass.
- final_acceptance_MS_R1_001: received on 2026-06-23T02:00:00+08:00; accepted model-layer extraction and governance. 8/8 worktracks (A1-A8), 10/10 completion signals, 6/6 acceptance criteria, 397/397 tests pass. Commit: 5da7cde.
- final_acceptance_MS_R2_001: received on 2026-06-23T04:00:00+08:00; accepted repo directory restructuring (inputs/workspace/outputs). 11/11 worktracks, 11/11 completion signals, pytest 395/397 (2 residual path failures deferred to later milestones). History: repo/milestone-history.md § MS-R2-001.
- final_acceptance_MS_R3_001: received on 2026-07-14T17:24:00+08:00; accepted deep cleanup. 3/3 worktracks, pytest 397/397, merge develop@296318b. History: repo/milestone-history.md § MS-R3-001.
- final_acceptance_MS_T1_001: received on 2026-07-14T20:11:00+08:00; accepted T-heavy test suite rewrite. 4/4 worktracks, pytest full 396/396, fast 277, cov~78%/fail_under=76, merge develop@eed3e24. History: repo/milestone-history.md § MS-T1-001.
- milestone_brief_MS_R2_001: received on 2026-06-23T01:00:00+08:00; planned milestone registered for repo directory restructuring with 3-zone model; later expanded to 11 worktracks and completed/accepted.
- milestone_brief_MS_R3_001: received and confirmed on 2026-07-14; decisions D1=B, D2=T2, D3=P3, D4=confirm; Init authorized by programmer message「初始化 MS-R3-001」.
- milestone_activation_MS_R3_001: received on 2026-07-14T11:35:00+08:00; MS-R3-001 set active; branch milestone/MS-R3-001-deep-cleanup.
- milestone_brief_MS_T1_001: received and confirmed on 2026-07-14; decisions D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirm; Init authorized after Formal Close R3 by programmer message「按照你的建议来：1. Formal Close 2. 再开始 init MS-T1-001」.
- milestone_activation_MS_T1_001: received on 2026-07-14T17:24:00+08:00; MS-T1-001 set active; branch milestone/MS-T1-001-test-suite-rewrite.
- milestone_brief_MS_S1_001: received on 2026-06-12T10:01:18+08:00; planned milestone registered for three-head prediction credibility and report contract, explicitly excluding alpha_score optimization/promotion.
- milestone_brief_MS_S2_001: received on 2026-06-22T09:21:03+08:00; planned milestone registered for stock-pool stratification definition and registry contract, explicitly excluding 3/5/10d revalidation, model retraining, and signal promotion.
- milestone_plan_update_MS_S2_001: received on 2026-06-22T10:15:03+08:00; Worktrack planning updated to use TuShare cache-first, dry-run-first, quota-aware analysis and to keep low-control-probability labels as proxy/candidate boundaries.
- milestone_plan_update_MS_S2_001_A2_testing: received on 2026-06-22T10:18:40+08:00; A2 must include fetch-strategy tests and explicitly account for TuShare 1H frequency-wall time-waiting / resume behavior before A3 may rely on quota-consuming fetch paths.
- milestone_activation_MS_S2_001: received on 2026-06-22T10:48:41+08:00; user approved starting MS-S2-001 and requested a programmer mid-review after A2 and before A3.
- milestone_plan_update_MS_S2_001_A2_next: received on 2026-06-22T11:12:24+08:00; user requested inserting A2-next before A3 to compress A1 output due to over-expansion risk.

## User-Defined Servo Controls

> 初始化时只记录用户可定义的控制偏好；不要询问或手动维护 Servo 可自动维护的 runtime facts。未确认字段按保守默认解释，不扩大权限。

- continuous_progression_permission: allowed_within_confirmed_milestone
  - semantics: Harness may continue through planned/approved Worktracks inside a confirmed active milestone until a formal stop condition is hit; this does not authorize new milestone creation, final milestone acceptance, release-sensitive actions, or out-of-scope work.
- auto_append_worktrack_permission: allowed_within_active_milestone_budget
  - semantics: Harness may append missing low-risk Worktracks only inside the active milestone, only when they preserve the approved milestone purpose and remain within the automatic Worktrack budget.
- per_milestone_automatic_worktrack_budget: 6
- default_servo_work_branch: develop
  - basis: programmer confirmed on 2026-06-09 that future work should focus on the current worktree/current branch instead of multiple worktrees.
  - semantics: `develop` is the default review/baseline branch for Servo-managed work, not a blanket authorization for direct mutation.
- protected_branch_policy: develop_as_programmer_review_branch
  - basis: programmer confirmed on 2026-06-10 that `develop` should be the day-to-day programmer review branch under Servo.
  - semantics: Direct mutation of `develop` remains approval-gated except for explicitly approved checkpoint/acceptance flows.
- branch_mutation_policy: one_development_branch_per_milestone
  - allowed: create or use one independent development branch per confirmed milestone.
  - forbidden_by_default: per-feature branch proliferation, multiple worktrees, branch deletion, force reset, and branch/worktree expansion outside the active milestone policy.
  - commit_push_policy: git commit and git push require explicit programmer approval.
  - commit_push_policy: git commit and git push require explicit programmer approval.
  - observed_standing_rule: no git commit, git push, git reset, branch deletion, worktree expansion, or production call unless explicitly requested by the programmer.
  - semantics: A confirmed active milestone may use one dedicated development branch; feature branch proliferation, extra worktrees, branch deletion, reset/force operations, and branch expansion remain approval-gated.
- milestone_branch_policy:
  - default_review_branch: develop
  - milestone_development_branch_required: yes
  - branch_naming_hint: milestone/{milestone_id}-{short-slug}
  - branch_creation_authority: allowed for confirmed active milestones; do not create ad hoc feature branches.
  - semantics: Branch creation authority applies only after a milestone is confirmed active; no ad hoc branch creation for candidate or unapproved milestones.
- auto_maintained_runtime_facts_not_asked:
  - active_milestone
  - active_worktrack
  - observed_git_hash
  - progress_counters
  - runtime_dispatch_profile
  - latest_observed_checkpoint
  - last_doc_catch_up_checkpoint
  - milestone_pipeline_summary

### Programmer Decisions Needed

- none for current persistent work-habit variables.
- still_required_per_action:
  - git commit approval
  - git push approval
  - destructive operation approval
  - production or external side-effect approval
  - final milestone acceptance
  - any branch/worktree action outside one development branch per confirmed milestone

## Continuation Authority

> `subagent_dispatch_mode` 是使用 SubAgent 的 repo 级默认开关。`subagent_dispatch_mode_override_scope: worktrack-contract-primary` 表示默认让工作追踪内的 `runtime_dispatch_mode` 优先；只有显式改为 `global-override` 时，control-state 才压过 worktrack 合同。

- post_contract_autonomy: delegated-continuous
  - semantics: After a Worktrack Contract is established inside a confirmed active milestone, Harness may continue across bounded Worktrack control steps until a formal stop condition is hit.
- autonomy_scope: active-milestone-only
  - semantics: No autonomous continuation is allowed when `active_milestone` is none, completed, unconfirmed, or outside the approved milestone purpose.
- max_auto_new_worktracks: 6
  - semantics: Mirrors `per_milestone_automatic_worktrack_budget`; budget applies only to missing in-purpose Worktracks inside the active milestone.
- stop_after_autonomous_slice: no
  - semantics: Do not stop merely because one bounded slice completed; still stop on approval, evidence, route, runtime, branch, scope, or handback conditions.
- subagent_dispatch_mode: auto
  - semantics: Repo-level fallback policy; automatically attempt SubAgent dispatch when runtime support, permissions, dispatch package safety, task coupling, parallel value, risk profile, and context budget make delegation appropriate. If delegation is unsafe or unavailable, record explicit runtime fallback instead of silently claiming SubAgent dispatch.
- subagent_dispatch_mode_override_scope: worktrack-contract-primary
  - semantics: Current Worktrack Contract `runtime_dispatch_mode` wins; set to `global-override` only when the repo-level mode must override every Worktrack.
- subagent_default_model: N/A
- runtime_dispatch_profile:
  - backend_runtime: codex
  - model_family: GPT-5 Codex
  - subagent_dispatch_shell: not_probed
  - runtime_supports_subagent: unknown_until_dispatch_probe
  - subagent_permission_state: permitted_by_persistent_policy
  - permission_allows_delegation: yes
  - dispatch_package_safety: safe_for_readonly_sidecar
  - delegation_attempted: yes
  - attempted_carrier: none for C0 implementation
  - carrier_decision: current-carrier synthesis
  - fallback_reason: C0 draft synthesis required direct integration with current dirty worktree and Servo control artifacts
- persistent_authority_notes:
  - Servo bootstrap may update `.servo` control artifacts and installed skill files for initialization.
  - Within a confirmed active milestone, Servo may continue through worktracks and append needed worktracks up to the configured per-milestone budget of 6.
  - Each confirmed milestone should use one independent development branch, with `develop` acting as the programmer review branch.
  - SubAgent dispatch is retained as the default execution carrier preference.
  - Destructive filesystem cleanup, git commit, git push, reset, production API calls, and dependency upgrades still require explicit programmer instruction.
  - One-shot execution-cycle authority granted on 2026-06-11 for `MS-S0-001`: up to 30 continuous Worktrack actions, SubAgent delegation, low-risk Worktrack self-approval, strict validation, automatic append/start for missing Worktracks within this milestone. This is not persistent authority for commit, push, install, repair, destructive cleanup, production/external side effects, model retraining, or final milestone acceptance.
  - One-shot repair authority granted on 2026-06-11 by programmer message "批准更改": install missing dependencies into `py311-private` and migrate active environment contract from `ashare-lab` to `py311-private`.

## Low-Risk Default-Flow Autonomy Policy

> 本段把连续执行权限收窄为可校验的默认流规则。它不扩大 Approval Boundary；任一 forbidden 或 stop_condition 命中时必须 handback、审批或 recover。

- policy_status: explicit_control_constraint
- allowed:
  - read-only observation and artifact hydration inside the current approved scope.
  - state consistency checks, route estimation, and Worktrack task queue scheduling inside a confirmed active milestone.
  - non-destructive docs/template/test edits that match the active Worktrack Contract.
  - local validation commands that have no external side effect and fit the active Worktrack verification requirements.
  - repo-refresh writeback after a passed Gate when closeout evidence is complete.
  - SubAgent dispatch attempts when runtime support, permission, dispatch package safety, context budget, and task risk allow it.
- forbidden:
  - goal change, unapproved scope expansion, new milestone creation, or final milestone acceptance.
  - release, publish, package version, tag, dist-tag, GitHub Release, or publish workflow changes.
  - protected branch mutation, force push/reset, branch deletion, worktree expansion, or branch action outside one development branch per confirmed milestone.
  - destructive cleanup, dependency install/upgrade, environment repair, secret/security/privacy-sensitive action, deploy/network/database migration, production/external side effect, external paid/quota-consuming call, model retraining, or model promotion.
- stop_condition:
  - missing, stale, or conflicting evidence.
  - branch context mismatch for a mutating Function.
  - Gate soft-fail, hard-fail, or blocked verdict.
  - runtime dispatch gap when the next route requires a safe delegation carrier.
  - Worktrack Contract scope boundary, approved milestone purpose, or automatic Worktrack budget would be exceeded.
  - programmer judgment is required, approval boundary is unclear, release-sensitive signal appears, or final milestone acceptance boundary is reached.
- evidence_required:
  - hydrated control-state and linked artifacts.
  - route decision and selected Scope/Function.
  - Worktrack Contract / scope boundary when in WorktrackScope.
  - selected task, dispatch packet, and runtime dispatch profile before execution.
  - validation, governance, policy evidence, Gate verdict, closeout record, and repo-refresh checkpoint before baseline advancement.

## Handback Guard

- handoff_state: a3_initialized_awaiting_t1
- last_stop_reason: WT-R4-A3 Init complete; await Dispatch T1; no live; push gated
- last_handback_signature: WT-R4-A3/Init/2026-07-22T14:16:00+08:00
- handback_reaffirmed_rounds: 0
- stable_handback_threshold: 2
- handback_lock_active: false
- last_unlock_signal: programmer Init WT-R4-A3

## Baseline Traceability

> 记录最近一次 worktrack 关闭后的已验证基线，供后续续跑时快速定位。

- last_verified_checkpoint: 6a2413e
- latest_observed_checkpoint: 6a2413e
- last_doc_catch_up_checkpoint: 6a2413e
- milestone_input_checkpoint: WT-R4-A3-init-2026-07-22T14:16:00+08:00
- checkpoint_type: git_commit
- checkpoint_ref: 4474da9d86c21eaa219988b187302895647e7b06
- verified_at: 2026-07-22T14:16:00+08:00
- if_no_commit_reason: N/A for Init baseline; A3 Init artifacts uncommitted until programmer approve
- alternative_traceability:
  - A3 contract: .servo/worktrack/WT-R4-A3-contract.md
  - A3 plan: .servo/worktrack/WT-R4-A3-plan-task-queue.md
  - A3 intake: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md
  - A3 init result: .servo/worktrack/WT-R4-A3-init-result.md
  - A2 close: .servo/worktrack/WT-R4-A2-closeout.md

## Autonomy Ledger

- autonomy_budget_remaining: 6
- active_persistent_autonomy_budget_source: MS-R4-001 (within confirmed active milestone; still stop on approval/evidence gates)
- historical_one_shot_budget_remaining: 26
- autonomous_worktracks_opened: 0
- one_shot_execution_cycle_budget:
  - granted_at: 2026-06-11
  - scope: MS-S0-001
  - worktrack_action_budget: 30
  - consumed_worktrack_actions: 4
  - remaining_worktrack_actions: 26
  - non_persistent: true
  - excludes: commit, push, package install, dependency upgrade, environment repair, destructive cleanup, production/external side effect, model retraining, final milestone acceptance

## Notes

- returning_to_repo_scope_does_not_clear_handoff: yes
- single_worktree_policy_observed: yes
- multi_worktree_cleanup_completed: yes
- `.servo` bootstrap was generated by the installed Servo deploy helper, then project facts were filled from README, NEXT_STEPS, ROADMAP, pyproject, and git status.
- three_track_plan_ref: docs/overview/three_track_development_plan_20260609.md
- completed_milestone_latest: MS-T1-001 广义测试体系清理 (accepted; merge develop@eed3e24)
- last_active_milestone_initialized: MS-R4-001
- planned_milestone_waiting: none (MS-R4-001 active)
- worktrack_init_blocked_until: N/A (WT-R4-A3 active)
- active_worktrack_initialized: WT-R4-A3
- last_closed_worktrack: WT-R4-A2
- worktrack_intake_review_ref: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- worktrack_gate_evidence_ref: N/A
- closeout_ref: .servo/worktrack/WT-R4-A2-closeout.md
- environment_validation_report_ref: .servo/worktrack/environment-validation-report.md
- current_stop_condition: A3 Init done; await T1 Dispatch; no live until batch approve; no full-campaign / train / Phase4 / EXEC-002; push gated
- active_intake_review_ref: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- control_plane_refresh_ref: .servo/repo/refresh-report-MS-T1-001-close-2026-07-14.md
- persistent_work_habits_updated: 2026-06-10
- default_workflow_policy: develop is programmer review branch; one development branch per confirmed milestone; delegated SubAgent execution retained; commit and push require approval.
