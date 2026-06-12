---
name: repo-refresh-skill
description: 当 Harness 在工作追踪收尾后回到代码仓库范围，并需要一轮限定范围的代码仓库刷新外加一份已验证的回写交接时，使用这个技能。
---

# 代码仓库刷新技能

## 概览

本技能实现 `RepoScope.Close`（`refresh-repo-state`）状态转移算子，对应 Harness 控制回路中的**状态更新**阶段。

它是 Worktrack 闭环的**终点和 Repo 闭环的起点**：在 Worktrack 关闭（merge → cleanup）后，必须回到 RepoScope 刷新 repo snapshot，才能让 Repo 的慢变量被真实更新。这是完整控制回路的关键闭合环节。

它只从**已验证证据**刷新代码仓库级真相，而不是从工作追踪产物直接抄写。代码仓库真相产物的唯一合法写入前提是经过 `Gate` 验证；未经验证的结论写入代码仓库真相产物的行为必须返回 blocked。

它与 `close-worktrack-skill` 的关系：close-worktrack-skill 处理 WorktrackScope 的 Close（PR → merge → cleanup），而 repo-refresh-skill 处理回到 RepoScope 后的状态更新。

当 `Harness` 完成了一轮 `工作追踪范围` 收尾，并需要根据已验证证据刷新代码仓库级慢变量时，使用这个技能。

这个技能会为 `通用高能力模型` `SubAgent` 打包一轮限定范围的收尾后刷新，更新代码仓库级评估，并返回一份供程序员审批的结构化回写交接结果，而不是假设代码仓库真相已经被更新。

这个技能只负责代码仓库级回写。它不会维护、修补或重新打开工作追踪本地 `.servo/worktrack/*` 产物。

它的主要刷新依据是：

- 已验证的 `关卡证据`
- 当前 `代码仓库目标/章程`
- 当前 `代码仓库快照/状态`
- 当前 `Harness 控制状态`

已关闭的工作追踪产物只是已完成切片的辅助证据。它们本身不是代码仓库级真相层，仅当有经过验证的证据支撑时，直接向上抄写才合法；否则必须声明证据缺失并阻塞该写入路径。

## 何时使用

当当前问题不是"如何完成这个工作追踪"，而是"哪些代码仓库级真相现在需要根据那次已验证收尾来刷新"时，使用这个技能：

- 某个工作追踪已经进入收尾或合并完成状态
- `关卡证据` 可用且已经建立了已验证结果
- `代码仓库快照/状态` 现在需要慢变量刷新
- 已验证发现可能需要回写到代码仓库级正式产物
- `Harness` 在决定下一个代码仓库动作前需要限定范围的代码仓库刷新结果

## 工作流

1. 载入当前 `代码仓库目标/章程`、当前 `代码仓库快照/状态`、当前 `Harness 控制状态`，以及刚刚关闭的工作追踪的已验证 `关卡证据`。
2. 为一轮限定范围的 `通用高能力模型` `SubAgent` 构建一份 `代码仓库刷新任务简报` 和一份 `代码仓库刷新信息包`。
3. 从 close-worktrack 交接读取 `baseline_branch`、`branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref`、`checkpoint_base_ref`、PR target、merge target 与 checkpoint 基准；这些值的唯一合法来源是原始 `Worktrack Contract` 的 Branch Policy 字段。`baseline_branch` 表示 servo-managed final baseline；Milestone-derived worktrack 的直接 checkpoint/merge target 通常是 `closeout_target_ref` 指向的 Milestone branch。从当前分支名或写死默认分支名推断的行为必须返回 blocked。
4. 根据 `代码仓库目标/章程`、当前 `代码仓库快照/状态` 和已验证收尾证据刷新代码仓库级评估。
5. 将项目分开：
   - 已验证回写候选
   - 推迟或仍未验证的项目
   - 收尾后仍开放的代码仓库级风险
6. 将已关闭 worktrack 的条目（worktrack_id / milestone_id / status / node_type / scope / merge_commit / validation / intake_route）写入 `.servo/repo/worktrack-backlog.md`（若 backlog 不存在则创建）。`status` 按以下映射从 gate verdict 转换后写入：gate pass/merge success → `done`，gate blocked → `blocked`，deferred decision → `deferred`，superseded/resolved → `resolved`。按 `worktrack_id` upsert：若同一 `worktrack_id` 已存在则更新（覆盖旧状态），否则追加新条目。`milestone_id` 按以下优先级获取：Worktrack Contract frontmatter `milestone_id` → close handoff 引用 → `null`（无绑定）。`intake_route` 按以下优先级获取：Worktrack Contract frontmatter → close handoff 中的 append request 引用 → `"direct"` fallback。此步骤对每个已验证关闭的 worktrack 无条件执行。
7. 如果存在活跃 Milestone，检查已关闭 worktrack 是否在 Milestone 的 `worktrack_list` 中；若在列表中，标记 Milestone progress counter 需要由 milestone-status-skill 在下一轮 Observe 中更新。
7b. **Milestone Backlog 刷新**：若已关闭 worktrack 携带 `milestone_id`，读取 live `.servo/repo/milestone-backlog.md`，在该 milestone 的 `worktrack_list` 中标记对应 worktrack 完成。不修改 milestone status（该职责属于 `harness-skill` 在收到 `milestone-status-skill` 输出后的状态更新阶段）。若 milestone 已在 `.servo/repo/milestone-history.md` 中，只有在修正 completed/superseded 历史记录的 stale worktrack marker 时才可更新 history，且必须保留 status 为 completed/superseded。
8. 在一轮限定范围代码仓库刷新后停止，并返回一份固定格式的 `代码仓库刷新报告` 加一份 `已验证回写交接`。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 回写的唯一合法输入是已验证证据；将工作追踪产物直接当成回写依据的行为禁止出现。
- `工作追踪约定` 和 `计划/任务队列` 的输出角色仅限于工作追踪本地执行记录；将其当成代码仓库回写目标的行为禁止出现。
- 唯一合法行为是将已验证结论写进代码仓库真相产物；将未经验证结论写入的行为必须返回 blocked。
- 如果传入的代码仓库刷新交接缺少基线追溯信息，或基线不可验证，标记为基线缺失风险并回写审批请求。
- 回写目标的唯一合法来源是已验证且可追溯的基线证据；从工作追踪产物直接抄写回写目标的行为必须返回 blocked。

## 输出协议

- 先生成尽可能长且完整的 `代码仓库刷新报告`，确保所有刷新评估信息被记录
- 然后从完整报告中提取 `Control Signal` 层（影响下一动作决策的关键结论）
- `基线验收状态` 必须显式评估 incoming checkpoint 的可追溯性
- 重复性上下文必须引用文件路径；内联全文的行为必须返回 blocked。
- 如果某个字段无实质内容，唯一合法行为是使用 `N/A` 或省略；用占位符填充的行为必须返回 blocked。
- `Supporting Detail` 保留完整内容，只用于后续查阅，不纳入传递上下文

## 代码仓库刷新约定

每次运行这个技能时，都使用同一套限定范围约定格式。

### 代码仓库刷新任务简报

- `触发条件`
- `目标`
- `已关闭工作追踪`
- `范围内`
- `范围外`
- `约束`
- `回写目标`
- `完成信号`

### 代码仓库刷新信息包

- `当前代码仓库状态`
- `参与中的代码仓库产物`
- `关卡证据摘要`
- `已接受变更摘要`
- `验证结果`
- `基线验收状态`
  - `baseline_branch`: 从 close handoff 接收，原始来源必须是 `Worktrack Contract.baseline_branch`
  - `branch_source_ref`: 从 close handoff 接收，原始来源必须是 `Worktrack Contract.branch_source_ref`
  - `worktrack_branch`: 从 close handoff 接收，原始来源必须是 `Worktrack Contract.worktrack_branch`
  - `integration_target_ref`: 从 close handoff 接收，原始来源必须是 `Worktrack Contract.integration_target_ref`
  - `closeout_target_ref`: 从 close handoff 接收，原始来源必须是 `Worktrack Contract.closeout_target_ref`
  - `checkpoint_base_ref`: 从 close handoff 接收，原始来源必须是 `Worktrack Contract.checkpoint_base_ref`
  - `pr_target`: 本轮 PR target
  - `merge_target`: 本轮 merge target
  - `incoming_checkpoint_ref`: 从 close-worktrack 交接接收的基线引用
  - `checkpoint_verified`: yes / no / deferred
  - `baseline_gap_risk`: 如果基线不可追溯，标记风险等级（low / medium / high）
  - `closed_worktrack_node_type`: 已关闭 worktrack 的节点类型
  - `expected_baseline_form`: close handoff 中声明的预期基线形式
  - `actual_baseline_form`: 实际 checkpoint 形式
  - `merge_required`: close handoff 中声明的合并要求
  - `checkpoint_policy_match`: expected 与 actual 是否匹配
- `已知风险`
- `所需上下文`
- `缺失或推迟项目`

### 已验证回写交接

- `回写目标`
- `已验证发现`
- `建议更新`
- `证据依据`
- `推迟项目`
- `审批请求`

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `代码仓库刷新报告`：

- `代码仓库刷新触发条件`
- `代码仓库刷新评估`
- `已验证回写交接`
- `推迟或未验证项目`
- `建议代码仓库范围下一步`
- `程序员审查请求`

结果中至少应包含以下字段或等价表达：

- `子代理模型`
- `刷新触发条件`
- `基准分支`
- `baseline_branch`
- `branch_source_ref`
- `worktrack_branch`
- `integration_target_ref`
- `closeout_target_ref`
- `checkpoint_base_ref`
- `PR target`
- `merge target`
- `已关闭工作追踪`
- `已关闭工作追踪节点类型`
- `checkpoint_policy_match`
- `代码仓库状态变化`
- `已验证发现`
- `快照更新`
- `回写目标`
- `建议回写`
- `证据依据`
- `推迟项目`
- `开放风险`
- `建议下一代码仓库动作`
- `需要程序员回写审批`
- `如何审查`

## 资源

使用刚关闭的工作追踪对应的已验证 `关卡证据`、当前 `代码仓库目标/章程`、当前 `代码仓库快照/状态`、当前 `Harness 控制状态`，以及收尾后刷新所需的最小额外代码仓库上下文。读取已关闭的工作追踪产物时，工作追踪产物的输出角色仅限于已验证切片的辅助证据；把它们当成代码仓库真相替代品的行为，或把它们当作工作追踪维护目标的行为禁止出现。
