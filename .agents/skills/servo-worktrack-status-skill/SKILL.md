---
name: worktrack-status-skill
description: 当 Harness 处于 WorktrackScope.observing，且需要一轮限定范围的状态估计来形成当前工作追踪的结构化状态评估时，使用这个技能。
---

# 工作追踪状态技能

## 概览

把这个技能作为 `Codex` 中专门的 `工作追踪范围` 状态观察器使用。

本技能实现 `WorktrackScope.Observe` 状态转移算子，对应 Harness 控制回路中的**状态估计**阶段。它是 `WorktrackScope` 控制回路的**传感器**层，负责通过读取当前工作追踪的正式产物形成结构化状态估计，为后续的 `Decide`（`schedule-worktrack-skill`）、`Dispatch`（`dispatch-skills`）、`Verify`（`review-evidence-skill` / `test-evidence-skill` / `rule-check-skill`）等算子提供输入。

它实现一轮限定范围的 `工作追踪范围.观察中`，读取回答当前问题所需的最小标准产物，并向 `Harness` 返回结构化的 `WorktrackStateEstimate` 和一份观察交接结果。

这个技能首先是给 `Harness` 使用的稳定格式观察载体。当监督器希望在决策轮之前先拿到一份字段可重复的狭窄工作追踪状态包时，它很有价值；但它不是工作追踪的规划器，也不是每次运行 `调度工作追踪技能` 都必须满足的前置条件。

它的主要观察依据是工作追踪级真相：

- `Worktrack Contract`
- `Plan / Task Queue`
- 当前 evidence（`review-evidence-skill`、`test-evidence-skill`、`rule-check-skill` 产出的结构化证据）
- 当前 branch 与 baseline 的差异状态
- 当前 `Harness Control State`

`代码仓库目标/章程`、`代码仓库快照/状态` 等 Repo 级产物不是工作追踪基准。只有在当前工作追踪观察依赖于理解 Repo 长期基线时才读取它们，并且必须明确让这种使用从属于工作追踪级产物。对 `.servo/repo/*` 产物的唯一合法操作是读取消费。更新或重写 `.servo/repo/*` 产物的行为必须从本技能被阻断。

## 何时使用

当当前问题不是"下一步该做什么"，而是"当前工作追踪处于什么状态"时，使用这个技能：

- 在进入 `schedule-worktrack-skill` 之前需要状态估计
- 在 `recover-worktrack-skill` 之前需要评估失败路径上下文
- 在 `close-worktrack-skill` 之前需要评估收尾阶段
- 任何需要"当前工作追踪状态是什么"的时刻
- 暴露活动任务、阻塞项、证据变化与已知风险
- 在 `调度工作追踪技能` 或 `恢复工作追踪技能` 之前刷新状态依据
- 提供一份限定范围工作追踪状态上下文包，而不是发散成宽泛的工作追踪探索

## 工作流

1. 确认这是一轮 `工作追踪范围` 状态观察轮次，不是工作追踪调度、分派或直接执行。
2. 载入本轮所需的最小 `工作追踪范围` 产物：`Worktrack Contract`、`Plan/Task Queue`、当前 evidence、branch 状态，以及当前问题所需的最小额外产物。
3. 读取 `Worktrack Contract` 的当前状态，确认其完整性与时效性。
   - 读取 `Node Type` 与节点策略字段：`type`、`source_from_goal_charter`、`baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy`
   - 读取 Branch Policy 字段：`baseline_branch`、`branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref`、`checkpoint_base_ref`
   - 如果节点策略缺失或无法追溯到 Goal Charter，在状态估计中标记 `node_type_status` 风险，而不是静默使用默认值
4. 读取 `Plan/Task Queue` 的快照，评估队列与约定的对齐状态。
5. 评估证据变化：对比当前 evidence 与上次调度时的证据状态，识别自上次调度以来的新增、变更或衰减。
6. 评估阻塞项状态：检查当前阻塞项是否仍然有效、是否已解除、是否有新增阻塞。
7. 评估验收标准覆盖度：检查当前已处理标准与剩余标准，识别规划层覆盖缺口。
8. 评估实际 branch 与合同 Branch Policy 的差异状态：检查当前 checkout 是否匹配 `worktrack_branch`，分支父基准是否匹配 `branch_source_ref`，closeout/PR/merge/checkpoint 目标是否匹配 `closeout_target_ref` / `checkpoint_base_ref`，并记录相对 `baseline_branch` 的最终基线风险。
9. 判断当前观察依据是否足以进入下一轮限定范围工作追踪判定，并显式记录该就绪状态。
10. 向 `Harness` 返回一份固定格式的 `Worktrack 状态估计报告`。
11. 如果没有命中正式停止条件，允许监督器直接进入下一个合法工作追踪级判定。

## 状态估计约定

使用这个技能时，产出一份 `WorktrackStateEstimate`，至少包含以下字段：

| 字段 | 说明 |
|------|------|
| `queue_freshness` | 队列与约定的对齐状态：队列是否仍干净映射到当前验收标准，是否存在过期、缺失或矛盾的队列条目 |
| `contract_node_type` | 从 Worktrack Contract 读取的节点类型及其来源 |
| `node_policy` | 当前工作追踪适用的 `baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy` |
| `node_type_status` | 节点策略是否完整、是否能追溯到 Goal Charter、是否需要初始化或恢复路径修补 |
| `contract_branch_policy` | 从 Worktrack Contract 读取的 `baseline_branch`、`branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref`、`checkpoint_base_ref` |
| `evidence_delta` | 自上次调度以来的证据变化：新增 evidence、evidence 衰减、evidence 冲突，以及变化对工作追踪状态的影响 |
| `blocker_status` | 阻塞项的当前状态：活动阻塞项列表、阻塞原因、阻塞持续时间、是否可解除、是否有新增阻塞 |
| `acceptance_coverage_gap` | 验收覆盖缺口：已处理标准、剩余标准、规划层覆盖缺口、验收标准与任务队列的对齐偏差 |
| `branch_drift_status` | 分支漂移状态：当前 branch 与 `worktrack_branch`、`branch_source_ref`、`closeout_target_ref`、`checkpoint_base_ref` 和 final `baseline_branch` 的差异度量、冲突风险、合并就绪度、是否需要 sync/recover |
| `observation_confidence` | 状态估计置信度：高 / 中 / 低，以及置信度判定理由 |
| `observation_ready_for_decide` | 是否足以支撑决策：当前状态估计是否足够完整、新鲜、一致，能够为 `Decide` 算子提供可靠输入 |
| `recommended_next_function` | 基于状态估计建议的下一算子：如 `Decide`（`schedule`）、`Recover`、`Close`、`Verify` 等；注意这只是状态估计的附带推断，不是决策本身 |

## 正式停止条件

至少在以下任一条件成立时停止并返回控制权：

- 观察依据缺失、过期或相互矛盾到足以让 `工作追踪范围.决策` 只能靠猜
- `Worktrack Contract` 缺失或严重过期，无法建立有效的状态估计基准
- `Plan/Task Queue` 与 `Worktrack Contract` 严重脱节，队列无法映射到验收标准
- 为了拿到下一条探查信号而扩张成完整工作追踪重新发现，而不再是一轮限定范围观察
- 下一次所需探针会跨越只读边界或需要显式审批的权限边界

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 对 `.servo/repo/*` 的唯一合法操作是作为次要边界证据读取。重写 `.servo/repo/*` 的行为必须被阻断。
- 优先使用标准工作追踪产物，而不是工作追踪本地部署副本或模板。
- 状态报告的时效性标注必须反映实际状态。将过期状态标注为新鲜状态的行为必须被阻断。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `Worktrack 状态估计报告`：

- `工作追踪范围状态`
- `当前约定状态`
- `队列快照与对齐`
- `证据变化评估`
- `阻塞项状态`
- `验收覆盖度`
- `分支漂移状态`
- `观察就绪度`
- `路由交接`
- `已知风险与未知项`
- `交接给 Harness`

结果中至少应包含以下字段或等价表达：

- `当前范围`
- `当前阶段`
- `控制状态`
- `观察状态`
- `约定依据`
- `约定时效性`
- `使用的约定引用`
- `节点类型`
- `节点策略`
- `节点类型完整性`
- `合同分支策略`
- `队列快照`
- `队列与约定对齐状态`
- `证据变化`
- `活动阻塞项`
- `阻塞原因`
- `已处理验收标准`
- `剩余验收标准`
- `验收覆盖缺口`
- `分支状态`
- `分支来源与目标匹配状态`
- `分支漂移度量`
- `合并就绪度`
- `过期或缺失输入`
- `限定范围探查检查`
- `工作追踪判定就绪`
- `允许的下一路由`
- `建议下一路由`
- `可继续`
- `继续阻塞项`
- `需要审批`
- `审批理由`
- `交接信号`
- `需要监督器决策`

## 资源

使用当前 `Harness 控制状态`、当前 `Worktrack Contract`、当前 `Plan/Task Queue`、当前 evidence、当前 branch 状态，以及本轮观察所需的最小限定范围探查证据。只有当 Repo 级产物会实质影响工作追踪观察的时效性或边界解释时才读取它们，并且必须让它们从属于工作追踪级产物，禁止作为工作追踪真相的替代品。结果应保持足够狭窄，以便交给工作追踪判定，而不是扩张成工作追踪规划或代码仓库文档维护。
