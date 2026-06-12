---
name: dispatch-skills
description: 当 Harness 处于 WorktrackScope.dispatching，且需要一轮不扩大范围的限定范围分派来选择专用技能或执行载体时，使用这个技能。
---

# 分派技能

## 概览

本技能实现 `WorktrackScope.Dispatch` 状态转移算子，对应 Harness 控制回路中的**分派执行**阶段。它负责将已选工作项绑定到合适的执行载体（专用技能或通用回退载体），并分派一轮限定范围执行，而不是 Harness 自己执行编码。

当 `Harness` 已经有当前 `Worktrack` 动作，并且需要把这个动作绑定到合适的执行载体上完成一轮限定范围执行时，使用这个技能。

这个技能会消费一个已经选定的当前工作项，以及 `schedule-worktrack-skill` 为其准备的限定范围分派交接包；当存在明显匹配的专用技能时，选择最合适的那个，否则回退到 `generic-worker-skill` 这类通用任务完成执行载体。若当前工作项的主要产物是把已验证事实追平到长期文档层，应优先绑定 `doc-catch-up-worker-skill`。没有现成专用技能不是阻塞条件：分派结果可以给出一次性、限定范围的任务专用执行指令，并绑定到通用 `SubAgent` 或明确的当前载体回退。一次性指令的唯一合法身份是本轮限定范围执行指令；将其伪装成新的永久技能的行为必须被阻断。

这个技能也是执行前最后一道限定范围防线。如果调度包对单轮而言过大，这个技能应拒绝它并返回调度阶段，而不是把过大的初始切片强行规范成一次执行。

执行载体选择必须由可开关参数控制：先读取 `.servo/control-state.md` 的 `subagent_dispatch_mode_override_scope` 来判断覆盖意图。默认值 `worktrack-contract-primary` 表示当前 `Worktrack Contract` 的 `runtime_dispatch_mode` 优先；只有该字段明确设为 `global-override` 时，`.servo/control-state.md` 的 `subagent_dispatch_mode` 才作为全局覆盖。若 worktrack 未声明 `runtime_dispatch_mode`，再使用 control-state 的 `subagent_dispatch_mode` 作为 repo 级默认值；最终默认值为 `auto`。`auto` 基于任务耦合度、状态共享需求、并行价值、风险和 context budget 选择 `SubAgent`、专用 skill、`generic-worker-skill` 或 `current-carrier`；它不表示"能委派就委派"。`delegated` 表示必须真实委派，无法委派时应返回运行时缺口或权限阻塞；自动改为当前载体执行的行为必须被阻断。`current-carrier` 表示显式关闭 SubAgent 委派。只有 `auto` 命中 runtime fallback、权限边界禁止委派，或交接包不满足安全分派条件时，才允许在当前载体内执行同一份限定范围任务/信息约定，并明确报告为运行时回退，而不是伪装成子代理分派。Runtime decision inputs: `task_coupling`、`state_sharing_need`、`parallel_value`、`risk_profile`、`context_budget_fit`、`runtime_supports_subagent`、`permission_allows_delegation`、`dispatch_package_safety`。Source-side authoring trace: `docs/harness/foundations/dispatch-decision-policy.md`。

## 何时使用

当当前问题不是"下一个工作追踪动作是什么"，而是"这个动作现在应该如何分派"时，使用这个技能：

- 消费已经从活动 `计划/任务队列` 中选出的当前下一步动作
- 把当前工作项打包成一份限定范围执行约定
- 继承能够支撑这一轮限定范围执行的验收标准切片与验收对齐结果
- 判断是否存在语义上合适的专用技能
- 如果没有，就回退到 `generic-worker-skill` 承载的通用任务完成 `SubAgent`
- 如果当前工作项是文档追平，就绑定 `doc-catch-up-worker-skill`
- 如果没有专用技能但任务仍可安全执行，就生成本轮限定范围的任务专用指令、所需上下文和完成信号，并选择合适执行载体
- 执行一轮限定范围分派
- 把结构化证据与交接数据返回给 `Harness`

## 工作流

1. 载入理解当前已选工作项所需的最小 `WorktrackScope` 产物。
2. 确认当前工作项已经从活动 `计划/任务队列` 中选出；如果没有，返回调度阶段，而不是在这里臆造一个。
3. 确认当前工作项已经存在限定范围分派交接包；如果交接包缺失、过期或自相矛盾，返回调度阶段，而不是盲目封装执行。
4. 在执行前校验交接包，并明确记录任何约定缺口。
   - 确认交接包仍表示一个可在单轮执行的限定范围工作项
   - 确认验收标准切片仍足够窄，足以支撑一轮执行
   - 确认交接包保留了 `Node Type`、本轮适用 `gate_criteria`、baseline policy，并与 `Worktrack Contract` 的验证要求一致
   - 确认交接包含有 `shared_fact_pack` 与 `context_budget`；缺失时返回调度阶段补齐
   - 如果交接包现在更像一个端到端打包批次，而不是一个限定范围切片，应返回调度阶段，而不是在这里扩张它
5. 复用交接包中的 `分派任务简报` 和 `分派信息包`。从头重建的行为必须被阻断——交接包是调度阶段的权威输出。
6. 检查是否存在与当前工作项语义上明确匹配的专用技能；文档追平任务优先选择 `doc-catch-up-worker-skill`。
7. 如果有，就通过该专用技能分派。
   - 如果没有，唯一合法行为是把调度包转成一次性的任务专用执行指令，明确目标、范围内、范围外、验收切片、完成信号、回传证据格式和执行载体。阻塞流程或临时发明新 skill 名称的行为必须被阻断。
8. 读取 `runtime_dispatch_mode`（按 `override_scope -> contract -> control-state default -> runtime auto`）并选择执行载体；默认 `worktrack-contract-primary` 必须让 worktrack 级设置生效，只有 `global-override` 才允许 control-state 压过 contract。
   - 若模式为 `auto`，必须应用 Dispatch Decision Policy，并记录 `dispatch_policy_ref`、`runtime_dispatch_profile`、`decision_inputs`、`delegation_attempted`、`attempted_carrier`、`carrier_decision` 与选择理由。
   - `runtime_dispatch_profile` 必须至少包含 `backend_runtime`、`model_family`、`subagent_dispatch_shell`、`runtime_supports_subagent`、`subagent_permission_state`、`permission_allows_delegation`、`dispatch_package_safety`。
   - 在 ClaudeCodeCLI / Deepseek 兼容 lane 中，如果无法证明真实 SubAgent dispatch shell 可用，必须写明 `subagent_dispatch_shell = unavailable | unknown`，并将未委派原因记录为 `runtime fallback`、`permission blocked` 或 `dispatch package unsafe`。不得静默回退到当前载体。
9. 如果没有合适专用 skill，就使用同一份限定范围任务/信息约定，通过 `generic-worker-skill` 承载的通用任务完成 `SubAgent` 分派。
   - 仅当 `runtime_dispatch_mode` 或 policy 判定为 `current-carrier`，或宿主运行时缺少真实分派壳层、权限边界禁止委派、交接包不满足安全分派条件时，才允许当前载体运行时回退。
10. 记录本轮使用的是：
   - 委派式 `子代理` 分派
   - 当前载体运行时回退
11. 返回一份固定格式的 `分派结果`。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- "没有专用技能可用"本身不构成阻塞状态。该情况下应走通用回退路径（`generic-worker-skill` 或一次性任务专用指令），而不是停止流程。
- `auto` 模式下必须按 Dispatch Decision Policy 选择载体；不得把"宿主支持 SubAgent"单独当成默认委派理由。
- `shared_fact_pack` 与 `context_budget` 是执行前必需字段；缺失、越界或预算不匹配时必须返回调度阶段。
- `context_budget` 必须显式包含 `must_read`、`may_read`、`do_not_read`；执行载体不得读取 `do_not_read` 中的上下文。
- 仅当调度包已经携带显式的原子性理由时，通过合并实现、清理和验证工作来放宽首个面向执行切片的行为才合法；否则必须保持原切片粒度或返回调度阶段。
- 仅当宿主运行时真的创建了委派载体时，声称使用了委派式 `子代理` 才合法；否则必须显式报告未委派原因（`runtime fallback`、`permission blocked` 或 `dispatch package unsafe`），不得伪装成子代理分派。
- 发生当前载体运行时回退时，必须显式记录回退原因、未委派原因和保持的任务/信息边界。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `分派结果`：

- `交接验证`
- `分派决策`
- `分派任务简报`
- `分派信息包`
- `已执行动作`
- `已收集证据`
- `待解决问题`
- `返回 Harness`

结果中至少应包含以下字段或等价表达：

- `所选执行器`
- `所选执行器类型`
- `是否命中专用技能`
- `无专用技能时的任务专用指令`
- `运行时分派模式`
- `dispatch_policy_ref`
- `runtime_dispatch_profile`
- `decision_inputs`
- `delegation_attempted`
- `attempted_carrier`
- `carrier_decision`
- `选择理由`
- `是否使用回退`
- `回退理由`
- `fallback_reason`
- `交接包来源`
- `分派包状态`
- `包限定范围判定`
- `过大原因`
- `分派约定缺口`
- `节点类型`
- `本轮适用判定标准`
- `基线策略`
- `任务`
- `目标`
- `范围内`
- `范围外`
- `约束`
- `本轮验收标准`
- `使用的验收对齐`
- `验证要求`
- `完成信号`
- `所需上下文`
- `shared_fact_pack`
- `context_budget`
- `已执行动作`
- `触及或预期文件`
- `已收集证据`
- `待解决问题`
- `未分派时返回路径`
- `建议下一动作`

## 资源

使用当前选中的工作项、调度输出，以及由调度阶段编写的限定范围执行交接包，作为本轮分派的权威依据。
