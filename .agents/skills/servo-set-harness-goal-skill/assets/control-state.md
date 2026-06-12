# Harness Control State

> 这是 `.servo/control-state.md` 的模板来源，用来维护当前 Harness supervisor 的控制面状态，不要把业务真相写进来。
> 每轮 Harness 启动必须先读取本文件，恢复 linked artifact、审批边界、自动性、交接守卫、基线追溯和预算配置；缺失字段只能按 artifact 合同默认值降级解释，不能扩大权限。

## Metadata

- updated:
- owner:

## Current Control Level

- repo_scope: active
- worktrack_scope: closed

## Active Worktrack

- 

## Baseline Branch

- baseline_branch:
- baseline_ref:

## Branch Environment Guard

- current_branch_context: unknown
- expected_branch_context: unknown
- branch_context_guard_status: blocked
- branch_context_required_ref:
- active_milestone_branch:
- active_milestone_branch_sync_state: unknown
- worktrack_branch:

## Current Next Action

- 

## Linked Formal Documents

- repo_snapshot:
- repo_analysis:
- worktrack_contract:
- plan_task_queue:
- gate_evidence:

## Approval Boundary

- needs_programmer_approval:
- reason:
- approval_scope:
- approval_persistence: one-shot

## User-Defined Servo Controls

> 初始化时只询问用户可定义的控制偏好；不要询问 Servo 可自动维护的 runtime facts。未确认字段按保守默认解释，不扩大权限。

- continuous_progression_permission: pending_programmer_confirmation
- per_milestone_automatic_worktrack_budget: pending_programmer_confirmation
- default_servo_work_branch: pending_programmer_confirmation
- protected_branch_policy: pending_programmer_confirmation
- branch_mutation_policy: pending_programmer_confirmation
- auto_maintained_runtime_facts_not_asked:
  - active_milestone
  - active_worktrack
  - observed_git_hash
  - progress_counters
  - runtime_dispatch_profile
  - latest_observed_checkpoint
  - last_doc_catch_up_checkpoint
  - milestone_pipeline_summary

## Continuation Authority

> `subagent_dispatch_mode` 是使用 SubAgent 的 repo 级默认开关。`subagent_dispatch_mode_override_scope: worktrack-contract-primary` 表示默认让工作追踪内的 `runtime_dispatch_mode` 优先；只有显式改为 `global-override` 时，control-state 才压过 worktrack 合同。`auto` 按 Dispatch Decision Policy 选择 SubAgent、专用 skill、generic worker 或 current-carrier；`delegated` 要求真实委派；`current-carrier` 明确关闭 SubAgent 委派。若 `auto` 不能安全委派，必须在结果中写明 `runtime fallback`、权限边界阻断或 `dispatch package unsafe`。
> 用户授予的长期权限、自动性或分派策略变更必须写入本段或 Autonomy Ledger；一次性审批只写入本轮 evidence / handoff，不改变长期默认值。

- post_contract_autonomy: delegated-minimal
- autonomy_scope: current-goal-only
- max_auto_new_worktracks: 1
- stop_after_autonomous_slice: yes
- subagent_dispatch_mode: auto
- subagent_dispatch_mode_override_scope: worktrack-contract-primary
- subagent_default_model:
- runtime_dispatch_profile:
  - backend_runtime:
  - model_family:
  - subagent_dispatch_shell:
  - runtime_supports_subagent:
  - subagent_permission_state:
  - permission_allows_delegation:
  - dispatch_package_safety:
  - delegation_attempted:
  - attempted_carrier:
  - carrier_decision:
  - fallback_reason:
- persistent_authority_notes:

## Handback Guard

- handoff_state: none
- last_stop_reason:
- last_handback_signature:
- handback_reaffirmed_rounds: 0
- stable_handback_threshold: 2
- handback_lock_active: false
- last_unlock_signal: N/A

## Baseline Traceability

> 记录最近一次 worktrack 关闭后的已验证基线，供后续续跑时快速定位。
> `latest_observed_checkpoint` 与 `last_doc_catch_up_checkpoint` 是 git hash 幂等性锚点，用于避免对同一代码基线重复执行 repo-refresh 和 doc-catch-up。空值表示锚点尚未建立，首次观察必须完整刷新；harness-skill 启动时通过 git rev-parse HEAD 对比这两个字段决定是否跳过重复刷新。

- last_verified_checkpoint:
- latest_observed_checkpoint:
- last_doc_catch_up_checkpoint:
- milestone_input_checkpoint:
- checkpoint_type:
- checkpoint_ref:
- verified_at:
- if_no_commit_reason:
- alternative_traceability:

## Autonomy Ledger

- autonomy_budget_remaining: 1
- autonomous_worktracks_opened: 0

## Notes

- returning_to_repo_scope_does_not_clear_handoff: yes
- 
