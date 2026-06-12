---
name: repo-status-skill
description: 当 Harness 处于代码仓库范围，且需要一轮限定范围的状态观察时使用这个技能；如果宿主运行时支持，也可以交给专用的 通用高能力模型 子代理承载。
---

# 代码仓库状态技能

## 概览

把这个技能作为 `Codex` 中专门的 `代码仓库范围` 状态观察器使用。

本技能实现 `RepoScope.Observe` 状态转移算子，对应 Harness 控制回路中的**状态估计**阶段。它是控制回路的**传感器**层：通过读取 `代码仓库目标/章程`、`代码仓库快照/状态` 和 `Harness 控制状态` 等传感器来源，形成当前 Repo 级的结构化状态估计，而不是自报状态。其输出（结构化状态摘要）是下游 `RepoScope.Decide` 算子（如 repo-whats-next-skill）的输入依据。

它实现一轮限定范围的 `代码仓库范围.观察中`，读取回答当前问题所需的最小标准产物，并向 `Harness` 返回结构化的代码仓库状态摘要和一份观察交接结果。

这个技能首先是给 `Harness` 使用的稳定格式观察载体。当监督器希望在决策轮之前先拿到一份字段可重复的狭窄代码仓库状态包时，它很有价值；但它不是代码仓库的规划器，也不是每次运行 `代码仓库下一步技能` 都必须满足的前置条件。

它的主要观察依据是代码仓库级真相：

- `代码仓库目标/章程`
- `代码仓库快照/状态`
- 当前 `Harness 控制状态`
- 当前活跃 Milestone artifact（`.servo/milestone/{milestone_id}.md`）
- Milestone Backlog（`.servo/repo/milestone-backlog.md`）— Pipeline 上下文

`工作追踪约定`、`计划/任务队列` 以及其他工作追踪本地产物都不是代码仓库基准。只有在当前代码仓库观察依赖于理解一个活动中或刚关闭的工作追踪边界时才读取它们，并且必须明确让这种使用从属于代码仓库级产物。本技能对 `.servo/worktrack/*` 的唯一合法行为是读取为边界证据；更新或重写 `.servo/worktrack/*` 的行为必须标记为超出本技能权限。

## 何时使用

当当前问题不是"下一步该做什么"，而是"代码仓库基准现在处于什么状态"时，使用这个技能：

- 总结 `代码仓库范围` 所需的当前主线状态
- 暴露活动分支、治理信号与已知风险
- 在 `代码仓库下一步技能` 或 `目标变更控制技能` 之前刷新状态依据
- 提供一份限定范围代码仓库状态上下文包，而不是发散成宽泛的代码仓库探索

## 工作流

1. 确认这是一轮 `代码仓库范围` 状态观察轮次，不是工作追踪分派、下一步决策或直接执行。
2. 载入 `Harness 控制状态`、`代码仓库目标/章程`、`代码仓库快照/状态`，以及当前问题所需的最小额外产物。
   - 检查 `Goal Charter` 的 `Engineering Node Map` 是否存在、字段是否完整，并记录 `goal_node_map_status`
3. 如果标准快照缺失、过期或明显不足，只收集解释缺口所需的最小探查证据。
4. 以狭窄、可重复的字段集总结当前代码仓库基准状态、活动分支、治理与时效性信号、以及已知风险。
5. 判断当前观察依据是否足以进入下一轮限定范围代码仓库判定，并显式记录该就绪状态。
6. 向 `Harness` 返回一份固定格式的 `代码仓库状态摘要`。
7. 如果没有命中正式停止条件，允许监督器直接进入下一个合法代码仓库级判定。

## 正式停止条件

至少在以下任一条件成立时停止并返回控制权：

- 观察依据缺失、过期或相互矛盾到足以让 `代码仓库范围.决策` 只能靠猜
- 为了拿到下一条探查信号而扩张成完整代码仓库重新发现，而不再是一轮限定范围观察
- 下一次所需探针会跨越只读边界或需要显式审批的权限边界

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 对 `.servo/worktrack/*` 的唯一合法行为是将其读取为边界证据；重写 `.servo/worktrack/*` 的行为必须标记为超出本技能权限。
- 优先使用标准代码仓库产物，而不是代码仓库本地部署副本或模板。
- 仅当 `latest_observed_checkpoint` 已存在且其 hash 与当前 `git rev-parse HEAD` 一致时，才可跳过刷新；hash 不一致或 checkpoint 缺失时必须执行完整状态估计。
- 如果 `latest_observed_checkpoint` 记录的 hash 在当前 git history 中不可达（如曾被 `git reset`），应标记 `baseline_gap_risk: high` 并强制重新刷新。
- 代码仓库状态的唯一有效输入是标准代码仓库级产物；本地挂载结果禁止作为真相依据。
- 仅当 `latest_observed_checkpoint` 已存在时，幂等性守卫才有效；`latest_observed_checkpoint` 缺失时不等同于基线未变化，首次启动必须执行完整状态估计。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `代码仓库状态摘要`：

- `代码仓库范围状态`
- `当前基准`
- `活动分支与层面`
- `治理与时效性信号`
- `观察就绪度`
- `路由交接`
- `已知风险与未知项`
- `交接给 Harness`

结果中至少应包含以下字段或等价表达：

- `当前范围`
- `当前阶段`
- `控制状态`
- `观察状态`
- `快照依据`
- `快照时效性`
- `使用的目标引用`
- `goal_node_map_status`
- `active_milestone`：当前活跃的 Milestone ID（如存在）
- `milestone_status`：当前活跃 Milestone 的状态（planned / active / completed / superseded / N/A）
- `milestone_pipeline_planned_count`：Pipeline 中处于 planned 状态的 milestone 数量
- `milestone_pipeline_ready_count`：Pipeline 中满足前置条件、可激活的 planned milestone 数量
- `milestone_pipeline_stale`：Pipeline 是否需要重新评估（backlog 与 active milestone 状态不一致时标记）
- `milestone_acceptance_verdict`、`proceed_blockers`、`handback_required`：当 active_milestone 非空时，这些字段由 `milestone-status-skill` 产出；`repo-status-skill` 仅标记 Milestone 存在性，Harness 应在 Observe→Decide 之间追加调用 `milestone-status-skill` 获取裁决细节
- `主线状态`
- `活动分支`
- `治理信号`
- `已知风险`
- `过期或缺失输入`
- `限定范围探查检查`
- `代码仓库判定就绪`
- `允许的下一路由`
- `建议下一路由`
- `可继续`
- `继续阻塞项`
- `需要审批`
- `审批理由`
- `交接信号`
- `需要监督器决策`

## 资源

使用当前 `Harness 控制状态`、当前 `代码仓库目标/章程`、当前 `代码仓库快照/状态`，以及本轮观察所需的最小限定范围探查证据。只有当工作追踪本地产物会实质影响代码仓库观察的时效性或边界解释时才读取它们；仅允许将它们作为辅助边界证据使用，禁止将它们当作代码仓库真相的替代品。结果应保持足够狭窄，以便交给代码仓库判定，而不是扩张成代码仓库规划或工作追踪文档维护。
