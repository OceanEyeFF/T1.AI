# Worktrack Contract

> 这是 `.servo/worktrack/contract.md` 的模板来源，用来填写单个 worktrack 的局部状态转移合同。
> 按 `Control Signal` / `Supporting Detail` 双层输出：`Control Signal` 只放影响下一动作决策的关键结论；`Supporting Detail` 放完整上下文。

## Metadata

- worktrack_id:
- branch:
- baseline_branch:
- baseline_ref:
- owner:
- updated:
- contract_status:

## Node Type

> 从 Goal Charter 的 Engineering Node Map 绑定，决定本 worktrack 的基线策略与判定标准。

- type:
- source_from_goal_charter:
- baseline_form:
- merge_required:
- gate_criteria:
- if_interrupted_strategy:

## Worktrack Intake Review

> Milestone 派生 worktrack 必须引用 RepoScope.Decide 的 pre-init intake review。

- worktrack_intake_review:
- repo_fundamentals:
- snapshot_freshness:
- milestone_purpose_alignment:
- historical_conflict_risk:
- worktrack_adjustment_recommendations:
- add_remove_worktrack_recommendations:
- intake_review_verdict:
- ready_for_worktrack_init:

## Execution Policy

> Execution Policy canonical semantics are not repeated here. Runtime defaults are embedded below so installed skill packages do not need source-repo docs. Source-side authoring trace: `docs/harness/artifact/worktrack/contract.md#execution-policy`.

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes

## Task Goal

-

## Scope

### Control Signal
- 范围摘要（一句话）：

### Supporting Detail
- 详细范围项：

## Non-Goals

-

## Impacted Modules

-

## Planned Next State

-

## Acceptance Criteria

### Control Signal
- 核心验收项：

### Supporting Detail
- 完整验收标准：

## Constraints

### Control Signal
- 关键约束：

### Supporting Detail
- 详细约束条件：

## Verification Requirements

-

## Rollback Conditions

### Control Signal
- 回滚触发条件：

### Supporting Detail
- 回滚步骤与回退路径：

## Notes

-
