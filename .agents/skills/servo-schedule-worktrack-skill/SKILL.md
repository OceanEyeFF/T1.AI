---
name: schedule-worktrack-skill
description: 当 Harness 处于 WorktrackScope.scheduling，且需要一轮限定范围调度来刷新任务队列并选出当前下一步动作、但不直接分派下游执行时，使用这个技能。
---

# 调度工作追踪技能

## 概览

本技能实现 `WorktrackScope.Decide` 状态转移算子，对应 Harness 控制回路中的**算子选择**阶段。它基于状态估计结果（由 `worktrack-status-skill` 或等效状态估计提供）选择合法的下一步动作，而不是自行执行状态估计。

当 `Harness` 已经有一个活动中的 `工作追踪`，并需要一轮限定范围规划来刷新当前 `计划/任务队列` 时，使用这个技能。

这个技能会消费当前 `工作追踪约定` 和状态估计结果，重新评估队列，纳入活动中的验收标准、阻塞状态与可用证据，然后选出一个 `当前下一步动作`，或者返回明确的 `没有安全的下一步动作` 结果。

在 `工作追踪范围` 内，这是一轮限定范围规划：把当前任务列表转成一个可分派的工作项外加一份限定范围分派交接包。`Harness` 与 `分派技能` 应消费这个包，而不是替换它。

当队列刚被播种、刚恢复，或通过自动继续路径进入时，选出的工作项默认应是能安全推进 `工作追踪` 的最小可验证切片。初始调度应先收紧范围，再进入分派，而不是把第一个看起来可行的端到端打包块当成默认答案。

这个技能应让规划始终可追溯到当前验收标准，但它不负责收集验证证据，也不负责判断这些标准是否已经满足。

`Plan / Task Queue` 是当前 Worktrack 的局部任务窗口 / task window。它可以包含多个连续小任务，但每轮调度只能选出一个 `selected_next_action` 和一份 bounded dispatch handoff packet。任务窗口不得被解释为 Repo backlog、Milestone backlog、candidate milestone list 或全局待办；新增/移除/重排 Worktrack 必须回到 RepoScope.Decide / programmer approval。

队列实例必须保留 `task_window_id`、`window_boundary`、`selected_next_action_id`、`selected_next_action` 和 `dispatch_handoff_packet`。这些字段共同表达“window 内可以有多个 task，但当前 round 只有一个可分派动作”的控制边界。

## 何时使用

当当前问题不是"谁来执行这个任务"，而是"此刻正确的下一项限定范围工作项是什么"时，使用这个技能：

- 在约定澄清、新证据出现或阻塞项变化后刷新队列
- 在现有 `工作追踪` 内拆分、重排、延后或标记被阻塞的任务
- 选出一个已经可以交接的当前下一步动作
- 说明所选动作与剩余队列是否仍覆盖当前验收标准
- 判断下一步应该进入 `分派技能`、恢复路径，还是监督器升级
- 打包下一轮限定范围流程所需的最小上下文

## 工作流

1. 消费当前 `WorktrackStateEstimate`（由 Observe 阶段产出）和本轮所需的最小 `工作追踪范围` 产物。
2. 基于状态估计结果中的约定、队列快照、证据变化和阻塞项状态构建一份限定范围 `调度包`。
3. 只针对本轮刷新队列：
   - 保持就绪项不变
   - 当依赖或证据需要时重排任务
   - 如果当前项太宽而无法安全分派，就拆分任务
   - 推迟或阻塞未就绪的项
   - 当这是当前队列状态首个面向执行的切片时，优先选择一个最小依赖解锁步骤或一个验收标准切片，而不是更大的包
   - 如果当前候选跨越多个验收切片、多个子系统，或多个执行阶段，就拆出最小安全首个切片，除非约定明确要求原子性处理
   - 保留并维护任务字段语义：`task_id` 是稳定任务标识，`priority` 表示调度优先级，`depends_on` 表示硬依赖，`acceptance` 必须映射到当前 Worktrack Contract 的验收标准，`risk_level` 与 `stop_condition` 决定是否允许继续自动调度。
4. 检查刷新后的队列是否仍能干净映射到当前验收标准；若存在规划层覆盖缺口，要明确暴露。
5. 选出一个 `当前下一步动作`，或者带上阻塞原因返回 `没有安全的下一步动作`。
6. 如果存在 `当前下一步动作`，就把它封装成一份限定范围 `分派交接包`，其中包含任务简报、信息包，以及本轮明确的返回调度条件。
   - 分派交接包必须引用当前 `Worktrack Contract` 的 `Node Type`，并携带本轮适用的 `gate_criteria` 与 baseline policy。这些策略的唯一合法来源是 `Worktrack Contract`；在调度阶段重写这些策略的行为必须被阻断。
   - 分派交接包必须包含 `shared_fact_pack` 和 `context_budget`。`shared_fact_pack` 只给出 repo goal、snapshot、worktrack contract、当前任务验收切片、baseline 和不变量的引用；`context_budget` 必须列出 `must_read` / `may_read` / `do_not_read`、预算上限和扩读理由要求。
7. 产出一份固定格式的 `调度结果`；有需要时，让队列草稿与 `templates/plan-task-queue.template.md` 保持对齐。
8. 如果选定路由已经分派就绪，且没有命中正式停止条件，就允许监督器继续进入 `分派技能`。
9. 否则，把调度结果作为当前停止边界返回。

## 调度包

如果这个技能由 `通用高能力模型` `子代理` 承载，传入的限定范围包至少应包含：

- `工作追踪目标`
- `节点类型`
- `节点策略`
- `范围内`
- `范围外`
- `验收标准`
- `当前队列快照`
- `依赖状态`
- `阻塞项状态`
- `证据变化`
- `规划约束`
- `所需判定`

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 分派任务的唯一合法来源是当前 `计划/任务队列` 中已选出的当前下一步动作。在队列尚未选出动作时，根据代码仓库目标或初始化说明推导分派任务的行为必须被阻断。
- `Plan / Task Queue` 只属于当前 Worktrack。把它当成 Repo/Milestone backlog、candidate milestone recommendation 或跨 Worktrack 自动执行列表的行为必须被阻断。
- Worktrack-level scheduler 只能调度当前 Worktrack 的 task window；不得选择、追加、移除或重排 Milestone `worktrack_list`，也不得输出多个 current worktrack。Milestone-level scheduler 每轮一次只选一个 Worktrack，唯一 current worktrack 字段是 `selected_worktrack_id` / current worktrack。
- 每个 task 必须保留 `task_id`、`status`、`priority`、`assigned`、`description`、`depends_on`、`acceptance`、`risk_level` 与 `stop_condition` 的可追踪语义；调度输出必须说明 `selected_next_action` 如何覆盖对应 `acceptance`，以及为何其 `risk_level` / `stop_condition` 允许或阻断连续推进。
- 工作分派就绪的判定依据必须同时包含 `已选下一步动作` 和完整的分派交接包。仅凭 `已选下一步动作` 不能判定为分派就绪。
- 当更窄的首个切片可以被安全调度时，唯一合法的首个切片是最小安全切片。吸收多个验收切片、多子系统变更或端到端实现加验证的行为必须被阻断，应拆分为更细粒度切片。
- 仅当当前约定、依赖形状或显式原子性要求确实要求时，保留更宽首个切片才合法；否则必须拆分为更窄切片，并显式给出拆分理由。
- 当首个候选项使用模糊动词（如"完成""结束""把所有东西连起来"）时，唯一合法行为是拆分它或返回 `没有安全的下一步动作`。以模糊动词隐藏过大批次的行为必须被阻断。
- 当不存在安全的下一步动作时，唯一合法行为是明确返回该结论及阻塞原因。隐藏歧义的行为必须被阻断。
- 只有当当前路由已经把这次切换标记为可继续，且没有任何正式停止条件要求审批时，范围切换才可以在没有新的程序员交接的情况下继续。
- 当继续推进的判定依据已存在显式路由、阻塞项与审批字段时，唯一合法行为是消费这些显式字段。从文字推断继续推进的行为必须被阻断。
- `建议下一路由` 和 `建议下一动作` 是不同的路由字段，不可相互替代。当 `建议下一路由` 已存在时，必须消费它作为标准路由字段。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `调度结果`：

- `消费的状态估计`
- `队列刷新决策`
- `验收对齐`
- `当前下一步动作`
- `分派交接包`
- `分派或升级就绪度`
- `使用的证据`
- `待解决问题`
- `返回 Harness`

结果中至少应包含以下字段或等价表达：

**消费的状态估计（输入）**
- `当前工作追踪状态`
- `队列变化`
- `就绪任务`
- `被阻塞或推迟任务`
- `已考虑验收标准`
- `当前已处理标准`
- `剩余标准`
- `使用的证据`

**产出的调度决策（输出）**
- `刷新后队列快照`
- `验收覆盖缺口`
- `已选下一步动作编号`
- `selected_next_action`
- `task_id`
- `priority`
- `depends_on`
- `acceptance`
- `risk_level`
- `stop_condition`
- `已选下一步动作`
- `选择理由`
- `切片边界理由`
- `更宽切片理由`
- `剩余前置条件`
- `分派任务简报草稿`
- `分派信息包草稿`
- `dispatch handoff packet`
- `节点类型`
- `本轮适用判定标准`
- `基线策略`
- `分派包就绪`
- `返回调度条件`
- `分派就绪`
- `下一轮所需上下文`
- `shared_fact_pack`
- `context_budget`
- `建议下一路由`
- `待解决问题`
- `可继续`
- `建议下一技能或路由`

## 资源

当你需要本轮稳定的队列草稿格式时，使用当前工作追踪队列、约定、证据变化、任意由初始化产出的调度交接包，以及 `templates/plan-task-queue.template.md`。
