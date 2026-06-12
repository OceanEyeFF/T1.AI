---
name: repo-append-request-skill
description: 当 RepoScope 收到 append-feature、append-design 或 append-milestone 追加请求时，使用这个技能做限定范围分类与路由；它只生成 Append Request 路由结果，不执行目标变更、范围扩展、Milestone 创建、设计或实现。
---

# Repo 追加请求路由技能

## 概览

本技能在 `RepoScope` 下处理外部追加请求，对应 Harness 控制面中的**追加请求 intake / route** 阶段。

它只支持一个 skill、三个 mode：

- `append-feature`
- `append-design`
- `append-milestone`

本技能的职责是把追加请求分类为一个明确路由，并输出 `Append Request` 路由结果。它不修改 repo 目标，不创建或扩展 milestone/worktrack，不写设计文档，不执行实现，也不改写 `Harness Control State`。如果分类结果需要审批或后续执行，应把边界显式返回给 Harness 或 programmer。

## 何时使用

当用户提出的请求语义是"在现有 repo 目标、Milestone Pipeline 或当前 worktrack 之外追加一项 milestone、feature 或 design"时，使用本技能：

- `append-feature`：追加一个功能、行为、交互、接口、能力或实现工作
- `append-design`：追加一个设计分析、方案、架构判断、UX / protocol design 或实现前设计步骤
- `append-milestone`：追加或调整一个 Milestone Pipeline 层级的目标容器，包括创建/注册/激活 milestone，或把 worktrack 追加到已有 milestone 的请求

不使用的情况：

- 已经明确是修改 `Goal Charter`，且用户要求直接进入目标变更流程（用 `repo-change-goal-skill`）
- 已经有批准过的 worktrack contract，且当前任务只是在其中调度下一步（用 `schedule-worktrack-skill`）
- 已经确定要初始化新的 milestone，且 milestone brief 已确认、无需先分类路由（用 `init-milestone-skill`）
- 已经确定要初始化新的 worktrack，且无需先分类路由（用 `init-worktrack-skill`）
- 只是 repo 下一步优先级判断，没有具体追加请求（用 `repo-whats-next-skill`）

## 输入

本技能至少读取：

- 用户原始追加请求
- 请求 mode：`append-feature` / `append-design` / `append-milestone`
- 当前 `Repo Goal / Charter`
- 当前 `Repo Snapshot / Status`
- 当前 `Harness Control State`
- 如当前存在活跃 worktrack，读取判断边界所需的最小 `Worktrack Contract` 摘要

只在判断"scope expansion"是否成立时读取活跃 worktrack 产物。活跃 worktrack 产物的唯一合法角色是判定 scope expansion 边界；将 worktrack 队列当成 repo 级待办列表的行为禁止出现。

## 分类规则

分类结果必须是以下五类之一：

### 1. goal change

当追加请求会改变 repo 长期参考信号时，分类为 `goal change`：

- 改变项目愿景、核心功能目标、成功标准或系统不变量
- 需要新增、删除或重定义 `Engineering Node Map` 中的节点类型或默认 baseline policy
- 与现有 `Goal Charter` 明显冲突，必须先重设目标才可执行
- 请求本身是"把这个 repo 的目标改成..."

路由结果：

- `recommended_next_route: repo-change-goal-skill`
- `recommended_next_scope: RepoScope`
- `approval_required: true`
- 不生成 goal-charter 草案；只说明为什么应进入目标变更控制

### 2. new milestone

当追加请求位于当前 repo 目标内，并且应在 Milestone Pipeline 层承接时，分类为 `new milestone`：

- 它要创建、注册或激活一个 milestone
- 它要把多个已确认 worktrack 合并到一个 milestone 级功能迭代
- 它要向已有 milestone 追加 worktrack，且应由 `init-milestone-skill` 做 coverage review
- 它需要 milestone brief、priority、depends_on、completion_signals、acceptance_criteria 或 activation intent
- 它不是对当前活跃 worktrack 的必要修正或验收缺口

路由结果：

- `recommended_next_route: init-milestone-skill`
- `recommended_next_scope: RepoScope`
- `approval_required: true`，除非输入事实已明确包含 programmer 对 milestone brief 的确认
- 输出 `suggested_milestone_action`（create / activate / append_worktracks / upsert）与 milestone brief 所需最小字段
- 不写入 milestone artifact、milestone-backlog 或 control-state；只返回路由和审批边界

### 3. new worktrack

当追加请求位于当前 repo 目标内，但不是现有活跃 worktrack 的已批准范围时，分类为 `new worktrack`：

- 它是一个独立 feature / implementation slice
- 它能从 `Goal Charter` 的 `Engineering Node Map` 找到候选节点类型
- 它需要自己的 branch、baseline、contract、plan 和 gate
- 它不是对当前活跃 worktrack 的必要修正或验收缺口

路由结果：

- `recommended_next_route: init-worktrack-skill`
- `recommended_next_scope: WorktrackScope`
- `approval_required` 取决于该追加请求是否已经获得 programmer 授权
- 输出 `suggested_node_type` 与理由，最终绑定由 `init-worktrack-skill` 完成

### 4. scope expansion

当追加请求试图把一个新目标塞进当前活跃 worktrack 时，分类为 `scope expansion`：

- 当前存在活跃 worktrack
- 追加内容不在该 worktrack contract 的 `范围内`
- 追加内容会改变验收、影响模块、风险、验证要求或完成定义
- 用户希望"顺手一起做"或"把它加到当前这轮"

路由结果：

- `recommended_next_route: scope-expansion-approval`
- `recommended_next_scope: WorktrackScope`
- `approval_required: true`
- 不直接改写 worktrack contract；只输出扩范围理由、风险和建议审批边界

仅当追加内容超出了修复当前 worktrack 的已批准验收缺口范围时，才应归为 scope expansion；否则唯一合法行为是路由回当前 worktrack scheduling / dispatch。

### 5. design-only

当请求只需要形成设计判断或方案，不要求立刻进入实现时，分类为 `design-only`：

- 用户要求比较方案、定义接口、整理架构判断或写设计草案
- 设计结果可独立验收，不需要同轮执行实现
- 当前证据不足以安全进入实现，必须先收敛设计边界
- `append-design` 默认优先考虑本类，除非请求明确要求设计后继续实现

路由结果：

- `recommended_next_route: design-only-worktrack`
- `recommended_next_scope: WorktrackScope`
- `approval_required` 取决于是否已经批准建立该设计 worktrack
- 输出设计验收条件、非目标和后续是否可进入实现的判定口径

### 6. design-then-implementation

当请求要求先设计、再在设计结论被接受后实现时，分类为 `design-then-implementation`：

- 用户明确要求"先设计再实现"或等价语义
- feature 风险、架构耦合或 UX / protocol 不确定性要求先形成设计 gate
- `append-feature` 的实现前置条件是新增设计结论
- 设计产物通过 gate 后，才能初始化或继续实现 worktrack

路由结果：

- `recommended_next_route: design-then-implementation-worktrack`
- `recommended_next_scope: WorktrackScope`
- `approval_required` 取决于两阶段授权是否已明确
- 输出两个阶段的边界：`design_phase` 与 `implementation_phase`

## 冲突处理

- 如果同时命中 `goal change` 与其他类别，优先分类为 `goal change`。
- 如果 `append-milestone` 同时可归入 milestone 级承接和 worktrack 级承接，优先分类为 `new milestone`；只有用户明确要求纳入当前活跃 worktrack 时才归为 `scope expansion`。
- 如果同时命中 `scope expansion` 与 `new worktrack`，且用户要求纳入当前活跃 worktrack，优先分类为 `scope expansion` 并要求审批；否则分类为 `new worktrack`。
- 如果 `append-design` 同时可独立设计也可设计后实现，只有在用户明确授权实现或实现是请求不可分割的一部分时，才分类为 `design-then-implementation`。
- 如果证据不足以区分 `new worktrack` 与 `scope expansion`，返回 `classification_confidence: low`，建议 `保持并观察` 或请求最小缺失信息，擅自扩范围的行为必须返回 blocked。

## 工作流

1. 确认 mode 是 `append-feature`、`append-design` 或 `append-milestone`。
2. 读取最小 repo truth 与当前控制状态。
3. 判断追加请求是否改变长期目标；若是，分类为 `goal change`。
4. 判断追加请求是否属于 Milestone Pipeline 层；若是，分类为 `new milestone` 并路由到 `init-milestone-skill`。
5. 判断是否存在活跃 worktrack，以及追加请求是否越过当前 worktrack contract。
6. 判断请求是 implementation、design-only，还是 design-then-implementation。
7. 对 worktrack 级请求从 `Engineering Node Map` 提取候选节点类型；对 milestone 级请求提取 `suggested_milestone_action` 与 milestone brief 边界；无法提取时暴露缺口。
8. 生成 `Append Request 路由结果`，可使用 `templates/append-request.template.md`。
9. 返回 Harness；不执行推荐路由。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

本技能特有约束：

- 唯一合法行为是分类与路由；执行任何后续操作的行为必须返回 blocked。
- 唯一合法行为是输出路由结果；创建 milestone artifact、写 milestone-backlog、创建 branch、contract、plan 或 design artifact 的行为必须返回 blocked。
- `append-feature` 的输出仅限于分类路由结果；将其自动解释为已批准的新 worktrack 的行为禁止出现。
- `append-design` 的输出仅限于分类路由结果；将其自动解释为已批准的实现工作的行为禁止出现。
- `append-milestone` 的输出仅限于分类路由结果；将其自动解释为已确认 milestone brief、已创建 milestone 或已激活 milestone 的行为禁止出现。
- scope expansion 必须显式暴露审批边界；将其包装成普通 scheduling 的行为禁止出现。
- 唯一合法行为是由本技能统一处理三个 mode（append-feature / append-design / append-milestone）；用多个 skill 分别处理的行为必须返回 blocked。
- 如果路由需要 programmer authority，必须设置 `approval_required: true` 并说明审批范围。
- `approval_required`、`continuation_ready` 与 `continuation_blockers` 必须一致：仅当不需要新审批时，设置 `continuation_ready: true` 才合法；需要新审批时必须设置 `continuation_ready: false`。
- `classification_confidence: low` 或存在阻塞性最小缺失信息时，必须设置 `continuation_ready: false` 并列出 blocker。
- 仅当输入事实已经明确批准该边界时，`continuation_ready` 才可为 `true`；`goal change` 与 `scope expansion` 默认停在审批边界。

## 预期输出

使用这个技能时，产出一份 `Append Request 路由结果`，至少包含：

- `mode`
- `原始追加请求`
- `分类结果`
- `分类置信度`
- `分类理由`
- `目标影响`
- `活跃 worktrack 影响`
- `建议下一路由`
- `建议下一范围`
- `suggested_node_type`
- `suggested_milestone_action`
- `milestone_brief_boundary`
- `设计阶段边界`
- `实现阶段边界`
- `权限边界`
- `最小缺失信息`
- `可继续`

结构化字段至少包含：

- `append_mode`
- `append_classification`
- `classification_confidence`
- `recommended_next_route`
- `recommended_next_scope`
- `suggested_node_type`
- `suggested_milestone_action`
- `approval_required`
- `approval_scope`
- `approval_reason`
- `continuation_ready`
- `continuation_blockers`

## 资源

使用当前 `.servo/goal-charter.md`、`.servo/repo/snapshot-status.md`、`.servo/control-state.md`、用户追加请求与必要的活跃 worktrack 摘要作为依据。

当需要整理 `Append Request 路由结果` 时，使用 `templates/append-request.template.md` 作为格式参考。
