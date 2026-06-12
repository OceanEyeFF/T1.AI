---
name: repo-change-goal-skill
description: 当需要修改 Repo 级目标（Goal Charter）时，使用这个技能。它分析变更影响、生成 goal-charter 草案，在用户确认后直接执行改写。
---

# 修改 Repo 目标技能

## 概览

本技能在 `RepoScope` 下执行目标变更，对应 Harness 控制回路中的**参考信号变更**阶段。

**关键约束：本技能不参与 Harness 的常规控制回路循环。** 它和 `SetGoal` 同属参考信号设定层——在循环外由外部请求触发，设定/重设完成后才启动（或重新启动）常规循环。常规循环中的 `Decide` 唯一合法行为是选择常规状态转移算子；主动选择目标变更作为下一步动作的行为必须返回 blocked。否则会出现"移动球门"问题：控制器为了让误差变小，不去修系统，而去改目标。

目标变更至少回答：为什么要改、改目标会影响哪些现有 worktrack、是否需要废弃现有计划、是否需要重新定义 baseline、变更幅度有多大。

本技能的工作方式区别于旧有的 SubAgent 打包分析模式：

- **在当前 carrier 直接分析**，不再把任务打包给独立 SubAgent 做限定范围分析。目标级变更涉及 repo 全局意图，当前 carrier 对上下文的理解比被压缩后的 SubAgent 简报更完整。
- **分析 → 草案 → 确认 → 执行** 的完整闭环。不再停在"出报告等审批"就结束；用户确认后，本技能直接执行对 `goal-charter.md`、`repo/snapshot-status.md`、`control-state.md` 的改写。

当 `Harness` 处于 `RepoScope` 并收到目标级变更请求时，使用这个技能。

## 何时使用

当需要修改 `Goal Charter` 时，使用这个技能：

- **总需求方向少量改动**：愿景不变，只对核心功能目标、技术方向或成功标准做局部调整
- **版本变更级别的目标更新**：从 v1 到 v2 的阶段性目标切换，如从 MVP 阶段跨入连续开发阶段
- **不变量调整**：需要增删或修改系统不变条件
- **其他需要修改总目标的场景**：任何会影响 repo 长期参考信号的变更请求

**不**使用的情况：

- 普通任务重排、局部实现细节变更，或不会改变 repo 目标的工作范围调整（用 `schedule-worktrack-skill`）
- 完全新建 repo 目标（用 `set-harness-goal-skill`）
- 已有活跃 worktrack 且需要判断下一步（用 `repo-status-skill` + `repo-whats-next-skill`）
- 只需要刷新 repo 快照（用 `repo-refresh-skill`）

## 工作流

1. **读取当前状态**
   - 当前 `.servo/goal-charter.md`
   - 当前 Goal Charter 中的 `Engineering Node Map`
   - 当前 `.servo/repo/snapshot-status.md`
   - 当前 `.servo/control-state.md`
   - 用户提出的变更请求文本
   - 需要时读取活跃 worktrack 产物作为影响面参考

2. **分析变更影响**（在当前 carrier 直接执行）
   - 识别目标差异：当前 goal-charter 与请求后的目标差异是什么
   - 评估变更幅度：`minor`（局部调整）/ `moderate`（结构性调整）/ `major`（方向性变更）
   - 评估对现有 worktracks 的影响：哪些活跃 worktrack 需要重新验证、暂停或终止
   - 评估对 baseline 的影响：当前 branch 与 snapshot 是否仍然有效
   - 评估对 `Engineering Node Map` 的影响：节点类型 registry、本 Goal 节点集合、节点依赖图、默认 baseline policy 是否需要保留、增删或重算
   - 评估节点策略差异：`merge_required`、`baseline_form`、`gate_criteria`、`if_interrupted_strategy` 是否变化，以及活跃 worktrack 是否需要重新绑定节点类型
   - 评估受威胁的不变量：哪些系统不变条件需要增删改
   - 识别证据缺口：当前 repo 状态是否足以支撑这次变更决策

3. **生成草案**
   - 输出 `目标变更分析报告`（结构化，使用 `templates/goal-change-request.template.md` 格式）
   - 输出 `goal-charter 草案`：可直接写入 `.servo/goal-charter.md` 的完整内容
   - `goal-charter 草案` 必须保留或重建 `Engineering Node Map`，并显式列出本次变更后的节点类型、baseline 策略、gate 标准和中断处理策略
   - 如果变更幅度为 `major`，额外输出 `baseline 重建建议`

4. **用户确认**
   - 展示 `目标变更分析报告` 摘要和 `goal-charter 草案` 的关键差异
   - 展示 `Engineering Node Map` 差异摘要，包括新增/删除/变更的节点类型、默认 baseline policy 变化、活跃 worktrack 兼容性
   - 等待用户确认、提出修改意见或拒绝
   - **在用户确认前不写入任何文件**
   - 如果用户提出修改意见，回到步骤 3 更新草案
   - 如果用户拒绝，返回 `变更被拒绝`，并建议回到 `RepoScope.Observe`

5. **执行改写**（用户确认后）
   - 改写 `.servo/goal-charter.md` 为确认的草案版本
   - 更新 `.servo/repo/snapshot-status.md` 的已有字段：
     - 更新 `Metadata` 中的 `updated` 和 `status`
     - 在 `Known Issues And Risks` 中追加变更引入的新风险
     - 在 `Notes` 中追加本次变更的简要记录（时间、原因、幅度）
   - 重置 `.servo/control-state.md` 的控制状态（参考信号已变，所有下游状态必须重新观测）：
     - 更新 `Metadata` 中的 `updated`
     - 在 `Notes` 中记录目标变更摘要
     - 将 `Current Control Level` 重置为：
       - `repo_scope: RepoScope`
       - `worktrack_scope: none`（目标变更后任何活跃 worktrack 都需重新验证；继续旧 worktrack scope 的行为必须标记为无效）
     - 清空 `Current Next Action`
     - 将 `Handback Guard` 的 `handoff_state` 重置为 `none`
     - 将 `Approval Boundary` 的 `needs_programmer_approval` 重置为 `false`
     - 如需反映 worktrack 状态变化，在 `Active Worktrack` 中更新状态描述（如标记为 `待重新验证` 或 `已终止`）
   - 报告实际改写的文件清单

6. **返回 Harness**
   - 返回 `Repo 目标变更结果`
   - 建议下一动作：`RepoScope.Observe`

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

本技能特有约束：

- 本技能是控制回路的参考信号变更层；目标变更是改变控制系统的参考信号，不是常规状态转移，必须单独 gate 和审批。
- **写入文件的唯一合法时机是用户确认之后；在用户确认前写入任何文件的行为必须返回 blocked。**
- 唯一合法行为是暴露歧义等用户决策；代替用户做目标级决策的行为必须返回 blocked。
- 目标影响、worktrack 影响与权限边界的输出必须各自独立陈述；混成一段模糊叙述的行为禁止出现。
- 歧义必须显式暴露为未解决问题；将歧义当成批准的行为禁止出现。
- 变更执行后，必须同步更新 `repo/snapshot-status.md` 和 `control-state.md`，不能只改 `goal-charter.md`。
- 改写 `goal-charter.md` 时，唯一合法行为是保留或重建 `Engineering Node Map`；静默删除、降级或留空 node type policy 的行为必须返回 blocked。
- 如果目标变更导致 `Engineering Node Map` 不再能覆盖活跃 worktrack，必须显式标记重新初始化、重新绑定或终止旧 worktrack 的后续动作。
- 如果变更幅度为 `major`，必须显式提示用户考虑是否需要重建 baseline 或重新初始化 worktracks。
- 唯一合法行为是对这些动作进行显式路由；静默关闭 worktrack、切换 scope 或重建 baseline 的行为必须返回 blocked。
- 推断 repo 目标变化的唯一合法依据是直接的 target-level 变更请求；仅凭 worktrack 队列变动或本地任务重排推断的行为必须返回 blocked。

## 预期输出

使用这个技能时，产出至少包含以下部分：

### 目标变更分析报告

- `变更请求`
- `变更理由`
- `目标差异`
- `变更幅度`（minor / moderate / major）
- `影响分析`
  - 基准影响
  - 活跃 worktrack 影响
  - Engineering Node Map 影响
  - 节点策略差异
  - 受威胁的不变条件
  - 证据或缺口
- `建议决策`
- `权限边界`（需要审批 / 审批范围）

### goal-charter 草案

- 可直接写入 `.servo/goal-charter.md` 的完整内容
- 与当前版本的差异高亮

### 执行结果

- `用户确认状态`
- `实际改写的文件清单`
- `后续必要动作`
- `建议下一路由`
- `建议下一 Scope`
- `建议下一 Function`
- `可继续`

## 资源

使用当前 `.servo/goal-charter.md`、`.servo/repo/snapshot-status.md`、`.servo/control-state.md` 与用户提出的变更请求作为分析依据。需要时读取活跃 worktrack 产物作为影响面参考，但不把它们当成 repo 意图的主来源。

当需要整理 `目标变更分析报告` 时，使用 `templates/goal-change-request.template.md` 作为格式参考。

---

## 结构化输出字段约定

结果中至少应包含以下字段或等价表达：

- `变更请求`
- `变更理由`
- `目标差异`
- `变更幅度`
- `影响分析`
- `Engineering Node Map 差异`
- `受影响节点类型`
- `节点策略差异`
- `活跃 worktrack 节点类型兼容性`
- `建议决策`
- `权限边界`
- `用户确认状态`
- `实际改写的文件清单`
- `后续必要动作`
- `建议下一路由`
- `建议下一 Scope`
- `可继续`
