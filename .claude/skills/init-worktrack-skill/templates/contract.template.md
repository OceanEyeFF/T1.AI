# 工作追踪约定模板

> 使用方式：在 `初始化工作追踪技能` 需要生成或重写工作追踪约定草稿时，使用本模板组织输出。
> 按 `Control Signal` / `Supporting Detail` 双层输出：`Control Signal` 只放影响下一动作决策的关键结论；`Supporting Detail` 放完整上下文。

## 元数据

- 工作追踪编号：N/A
- 分支：N/A
- 基准分支：N/A
- 基准引用：N/A
- 约定状态：N/A
- 负责人：N/A
- 更新时间：N/A
- milestone_id：N/A

## Branch Policy

> `baseline_branch` 是 servo-managed final baseline；Worktrack branch 来源和直接 closeout 目标必须用本节字段表达，不得由当前 checkout 推断。

- baseline_branch: N/A
- branch_source_ref: N/A
- worktrack_branch: N/A
- integration_target_ref: N/A
- closeout_target_ref: N/A
- final_baseline_branch: N/A
- checkpoint_base_ref: N/A

## Milestone Binding

> 若此 worktrack 属于活跃 Milestone，在此引用绑定。

- milestone_id: N/A
- derived_from_milestone: N/A

## Worktrack Intake Review

> Milestone 派生 worktrack 必须引用 RepoScope.Decide 的 pre-init intake review。

- worktrack_intake_review: N/A
- repo_fundamentals: N/A
- snapshot_freshness: N/A
- milestone_purpose_alignment: N/A
- historical_conflict_risk: N/A
- worktrack_adjustment_recommendations: N/A
- add_remove_worktrack_recommendations: N/A
- intake_review_verdict: N/A
- ready_for_worktrack_init: N/A
- milestone_review_gate_ready: N/A
- latest_review_status: N/A
- milestone_review_count: N/A
- latest_review_checkpoint: N/A
- effective_review_pass: N/A
- review_invalidated_by: N/A

Milestone Review Gate route guard: `effective_pass` with review count >= 1 and a non-empty checkpoint is required before Worktrack Init/Dispatch. `questions_required`, `blocked`, `skipped`, `missing`, `stale`, `invalidated`, or `milestone_review_gate_not_ready` block initialization.

## Node Type

> 从 Goal Charter 的 Engineering Node Map 绑定，决定本 worktrack 的基线策略与判定标准。

- type: N/A
- source_from_goal_charter: N/A
- baseline_form: N/A
- merge_required: N/A
- gate_criteria: N/A
- if_interrupted_strategy: N/A

## Execution Policy

> Execution Policy canonical semantics are not repeated here. Runtime defaults are embedded below so installed skill packages do not need source-repo docs. Source-side authoring trace: docs/harness/artifact/worktrack/contract.md#execution-policy.

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes

## 任务目标

### Control Signal

- 目标摘要：N/A

### Supporting Detail

- 完整目标：N/A

## 范围

### Control Signal

- 范围摘要：N/A

### Supporting Detail

- 详细范围项：N/A

## 非目标（不做的事）

### Control Signal

- 非目标摘要：N/A

### Supporting Detail

- 完整非目标：N/A

## 受影响模块

### Control Signal

- 关键影响模块：N/A

### Supporting Detail

- 完整影响模块清单：N/A

## 计划中的下一状态

### Control Signal

- 下一状态：N/A

### Supporting Detail

- 状态迁移理由：N/A

## 验收标准

### Control Signal

- 核心验收项：N/A

### Supporting Detail

- 完整验收标准：N/A

## 约束

### Control Signal

- 关键约束：N/A

### Supporting Detail

- 详细约束条件：N/A

## 验证要求

### Control Signal

- 必要验证：N/A

### Supporting Detail

- 完整验证要求：N/A

## 回滚条件

### Control Signal

- 回滚触发条件：N/A

### Supporting Detail

- 回滚步骤与回退路径：N/A

## 依赖项

### Control Signal

- 关键依赖：N/A

### Supporting Detail

- 完整依赖项：N/A

## 当前阻塞项

### Control Signal

- 当前阻塞项：N/A

### Supporting Detail

- 阻塞详情与解除条件：N/A

## 备注

### Control Signal

- 备注摘要：N/A

### Supporting Detail

- 完整备注：N/A
