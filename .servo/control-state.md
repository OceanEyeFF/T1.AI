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

- updated: 2026-06-17T14:00:13+08:00
- owner: OceanEyeFF

## Current Control Level

- repo_scope: active
- worktrack_scope: inactive

## Active Worktrack

- active_worktrack: none
- worktrack_status: none
- worktrack_contract: worktrack/contract.md
- plan_task_queue: worktrack/plan-task-queue.md
- gate_evidence: worktrack/gate-evidence.md
- active_task_window: WT-S1-CLEANUP-closeout
- selected_next_action_id: RepoScope.Observe
- worktrack_gate_verdict: N/A
- worktrack_blocker: none
- worktrack_residual_risk: WT-S1-CLEANUP completed local checkpoint; merge/push remain approval-gated.

## Active Milestone

- active_milestone: none
- milestone_status: completed
- milestone_kind: goal-driven
- milestone_artifact: milestone/MS-S1-001.md
- milestone_backlog: repo/milestone-backlog.md
- milestone_history: repo/milestone-history.md
- milestone_pipeline_summary:
  - active_count: 0
  - planned_count: 0
  - completed_count: 3
  - superseded_count: 0
- milestone_review_gate_ready: yes
- latest_review_status: effective_pass
- milestone_review_count: 1
- latest_review_checkpoint: MS-S1-001-intake-2026-06-12T10:01:18+08:00
- effective_review_pass: true
- next_milestone_route: observe repo and prepare next Milestone intake when requested.

## Baseline Branch

- baseline_branch: develop
- baseline_ref: 0095699d5610554bb23bbe511d2d2df8ad27abeb

## Branch Environment Guard

- current_branch_context: baseline
- expected_branch_context: baseline
- branch_context_guard_status: pass
- branch_context_required_ref: refs/heads/develop
- active_milestone_branch: milestone/MS-S1-001-three-head-credibility
- active_milestone_branch_sync_state: merged_to_develop_at_13fc2a2
- worktrack_branch: none

## Current Next Action

- `MS-S1-001` was accepted by programmer on 2026-06-17, locally checkpointed by WT-S1-CLEANUP, and fast-forwarded into `develop`; next route is RepoScope.Observe / future Milestone intake.

## Linked Formal Documents

- repo_snapshot: repo/snapshot-status.md
- repo_analysis: repo/analysis.md
- milestone_artifact: milestone/MS-S1-001.md
- milestone_backlog: repo/milestone-backlog.md
- milestone_history: repo/milestone-history.md
- planned_worktrack_backlog: repo/planned-worktrack-backlog.md
- worktrack_contract: worktrack/contract.md
- plan_task_queue: worktrack/plan-task-queue.md
- gate_evidence: worktrack/gate-evidence.md

## Approval Boundary

- needs_programmer_approval: yes
- reason: Persistent Servo work habit controls are configured; commit, push, destructive cleanup, production calls, new dependency changes, and Worktrack Init beyond approved intake remain approval-gated.
- approval_scope: commit, push, destructive operation, production/external side effect, release/version action, final milestone acceptance, and any branch/worktree action outside the configured milestone-branch policy.
- approval_persistence: persistent_work_habits_confirmed_on_2026-06-10
- milestone_brief_confirmation: received for MS-ENV-000 and MS-S0-001 only; does not approve Worktrack Init, code mutation, package installation, environment repair, commit, push, or production actions.
- one_shot_repair_confirmation: received on 2026-06-11 for WT-ENV-001 py311-private dependency repair and environment-contract migration only; does not approve commit, push, destructive cleanup, production/external side effects, release/version actions, or final milestone acceptance.
- final_acceptance_MS_ENV_000: received on 2026-06-11T16:40:59+08:00; accepted CPU-first continuation and non-blocking GPU residual risk.
- final_acceptance_MS_S0_001: received on 2026-06-12T01:28:03+08:00; accepted evaluation/guardrail/planning milestone with residual risk and no model promotion.
- milestone_brief_MS_S1_001: received on 2026-06-12T10:01:18+08:00; planned milestone registered for three-head prediction credibility and report contract, explicitly excluding alpha_score optimization/promotion.

## User-Defined Servo Controls

> 初始化时只记录用户可定义的控制偏好；不要询问或手动维护 Servo 可自动维护的 runtime facts。未确认字段按保守默认解释，不扩大权限。

- continuous_progression_permission: allowed_within_confirmed_milestone
- auto_append_worktrack_permission: allowed_within_active_milestone_budget
- per_milestone_automatic_worktrack_budget: 6
- default_servo_work_branch: develop
  - basis: programmer confirmed on 2026-06-09 that future work should focus on the current worktree/current branch instead of multiple worktrees.
- protected_branch_policy: develop_as_programmer_review_branch
  - basis: programmer confirmed on 2026-06-10 that `develop` should be the day-to-day programmer review branch under Servo.
- branch_mutation_policy: one_development_branch_per_milestone
  - allowed: create or use one independent development branch per confirmed milestone.
  - forbidden_by_default: per-feature branch proliferation, multiple worktrees, branch deletion, force reset, and branch/worktree expansion outside the active milestone policy.
  - commit_push_policy: git commit and git push require explicit programmer approval.
  - observed_standing_rule: no git commit, git push, git reset, branch deletion, worktree expansion, or production call unless explicitly requested by the programmer.
- milestone_branch_policy:
  - default_review_branch: develop
  - milestone_development_branch_required: yes
  - branch_naming_hint: milestone/{milestone_id}-{short-slug}
  - branch_creation_authority: allowed for confirmed active milestones; do not create ad hoc feature branches.
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
- autonomy_scope: active-milestone-only
- max_auto_new_worktracks: 6
- stop_after_autonomous_slice: no
- subagent_dispatch_mode: delegated
- subagent_dispatch_mode_override_scope: worktrack-contract-primary
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

## Handback Guard

- handoff_state: repo_observe_ready
- last_stop_reason: MS-S1-001 accepted with residual risk; no active milestone
- last_handback_signature: MS-S1-001/local-checkpoint/WT-S1-CLEANUP/2026-06-18T10:06:55+08:00
- handback_reaffirmed_rounds: 0
- stable_handback_threshold: 2
- handback_lock_active: false
- last_unlock_signal: N/A

## Baseline Traceability

> 记录最近一次 worktrack 关闭后的已验证基线，供后续续跑时快速定位。

- last_verified_checkpoint: 0095699d5610554bb23bbe511d2d2df8ad27abeb
- latest_observed_checkpoint: 13fc2a2
- last_doc_catch_up_checkpoint: N/A
- milestone_input_checkpoint: MS-S1-001-active-2026-06-12T14:39:44+08:00
- checkpoint_type: git_commit
- checkpoint_ref: HEAD
- verified_at: 2026-06-18T10:20:00+08:00
- if_no_commit_reason: N/A; MS-S0 baseline checkpoint commit 0095699d5610554bb23bbe511d2d2df8ad27abeb was created with programmer approval
- alternative_traceability:
  - MS-S0 accepted baseline was checkpointed and fast-forwarded into `develop` at 0095699d5610554bb23bbe511d2d2df8ad27abeb with programmer approval.
  - WT-A2-001 closeout: .servo/worktrack/closeout-report.md
  - WT-A2-001 gate evidence: .servo/worktrack/gate-evidence.md
  - WT-B0-001 closeout: .servo/worktrack/b0-closeout-report.md
  - WT-B0-001 gate evidence: .servo/worktrack/b0-gate-evidence.md
  - WT-C0-001 closeout: .servo/worktrack/c0-closeout-report.md
  - WT-C0-001 gate evidence: .servo/worktrack/c0-gate-evidence.md

## Autonomy Ledger

- autonomy_budget_remaining: 26
- autonomous_worktracks_opened: 4
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
- completed_milestone_latest: MS-S1-001 mainline three-head prediction credibility and report contract
- last_active_milestone_initialized: MS-S1-001
- planned_milestone_waiting: none
- worktrack_init_blocked_until: N/A
- active_worktrack_initialized: none
- worktrack_intake_review_ref: .servo/worktrack/MS-S1-001-WT-S1-A5-intake-review.md
- worktrack_gate_evidence_ref: .servo/worktrack/gate-evidence.md
- environment_validation_report_ref: .servo/worktrack/environment-validation-report.md
- current_stop_condition: none; awaiting next programmer-directed milestone intake
- active_intake_review_ref: .servo/worktrack/MS-S1-001-WT-S1-A5-intake-review.md
- persistent_work_habits_updated: 2026-06-10
- default_workflow_policy: develop is programmer review branch; one development branch per confirmed milestone; delegated SubAgent execution retained; commit and push require approval.
