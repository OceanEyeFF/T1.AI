---
name: init-worktrack-skill
description: 当 Harness 处于 WorktrackScope.initializing，且需要一轮限定范围流程来建立分支、基准、约定和初始计划，并干净地交给限定范围工作追踪调度时，使用这个技能。
---

# 初始化工作追踪技能

## 概览

本技能实现 `WorktrackScope.Init` 状态转移算子，对应 Harness 控制回路中的**初始化**阶段。它负责建立分支、固定基准、构建约定和播种初始队列，使工作追踪进入可被调度的状态。

当 `Harness` 已经决定开启或修复某个特定 `工作追踪`，并且现在需要一轮限定范围初始化时，使用这个技能。

这个技能会为 `工作追踪` 创建限定范围分支，明确基准，构建或刷新初始 `工作追踪约定`，播种第一版 `计划/任务队列`，并为下一轮限定范围规划准备最小调度交接包。

它本身不执行实现、验证或关卡判定。它的职责是让工作追踪进入可被限定范围调度的状态，而不是自行决定执行归属，或生成新的权威分派包。

## 何时使用

当当前问题不是"这个任务应该如何执行"，而是"这个工作追踪是否被正确初始化"时，使用这个技能：

- 创建这个 `工作追踪` 将要运行的限定范围分支
- 固定当前基准分支或提交引用
- 把已批准的工作项转译成一份限定范围 `工作追踪约定`
- 把该约定展开成一份初始 `计划/任务队列`
- 打包下一轮调度所需的最小上下文
- 明确暴露下一条路由是否可继续，还是被正式停止条件阻断

## 工作流

1. 载入当前 `Harness 控制状态`、`Goal Charter` 中的 `Engineering Node Map`、与初始化所需的最小代码仓库/工作追踪产物。
2. 判断当前属于：
   - 一个新的 `工作追踪`
   - 一个恢复中的 `工作追踪`，其分支、基准、约定或计划需要修复
3. 若当前 worktrack 来自 active milestone（`derived_from_milestone == true` 或传入 `target_milestone_id`），必须先读取上游 `repo-whats-next-skill` 的 `worktrack_intake_review`：
   - 必须包含 `repo_fundamentals`、`snapshot_freshness`、`milestone_purpose_alignment`、`historical_conflict_risk`、`worktrack_adjustment_recommendations`、`add_remove_worktrack_recommendations`、`intake_review_verdict` 和 `ready_for_worktrack_init`
   - 必须包含 `milestone_review_gate_ready`、`latest_review_status`、`milestone_review_count`、`latest_review_checkpoint`、`effective_review_pass` 和 `review_invalidated_by`
   - 只有 `milestone_review_gate_ready == true`、`latest_review_status == "effective_pass"`、`milestone_review_count >= 1`、`effective_review_pass == true` 且 `latest_review_checkpoint` 非空时，才允许 milestone-derived worktrack 继续初始化
   - 若 review 状态为 `skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全，返回被阻塞初始化结果，暴露 `milestone_review_gate_not_ready`，不得进入 Worktrack Init/Dispatch
   - 若上游 `.servo` runtime artifact 缺少 additive review/backfill 字段，使用 conservative runtime backfill：缺失字段按 `false`、`unknown`、`missing`、`blocked`、`not ready`、`N/A` 解释；该 backfill forward-only 且不得扩大权限、不得推断 programmer confirmation、不得增加 `milestone_review_count`、不得设置 `effective_review_pass = true` 或 `milestone_review_gate_ready = true`，不得创建 worktrack branch。
   - 只有 `intake_review_verdict == "ready_for_worktrack_init"` 且 `ready_for_worktrack_init == true` 时，才允许继续创建分支和写入 Worktrack Contract
   - 若 verdict 为 `refresh_required`，返回被阻塞初始化结果并建议回到 `RepoScope.Observe` / `RepoScope.Refresh`，不得创建 worktrack branch
   - 若 verdict 为 `adjust_worktracks`，返回被阻塞初始化结果并建议回到 `RepoScope.Decide` / milestone backlog 调整；需要新增、移除、重排 worktrack 时不得在 Init 中静默改写范围
   - 若 verdict 为 `blocked` 或 intake review 缺失/字段不全，返回被阻塞初始化结果，暴露 `worktrack_intake_review_missing_or_not_ready`
   - 初始化成功时，必须把 `worktrack_intake_review` 的摘要写入 `Worktrack Contract`
4. 为这个 `工作追踪` 创建限定范围分支。
5. 如果该分支无法安全创建，返回一个被阻塞的初始化结果，而不是静默复用另一条分支。
6. 记录这个 `工作追踪` 用来比较的基准引用，并把 Branch Policy 写入 `Worktrack Contract`：
   - 优先从当前已批准输入读取明确的 `baseline_branch`
   - 否则从 `origin/HEAD` 动态解析 baseline branch（执行 `git remote show origin | grep 'HEAD branch' | awk '{print $NF}'`）
   - baseline branch 的唯一合法来源是 `origin/HEAD` 动态解析，技能必须通过解析获取，写死默认分支名的行为禁止发生
   - 若 baseline branch 无法确认，初始化必须阻断，而不是猜测 PR target 或 merge target
   - 若 worktrack 来自 active milestone 且 milestone artifact 声明 `milestone_branch`，`branch_source_ref` 和 `integration_target_ref` 默认取 active Milestone branch head；`final_baseline_branch` 仍为 `baseline_branch`
   - 若 worktrack 来自 active milestone 但 `milestone_branch` 尚不存在，必须按已批准的 Milestone branch policy 创建或同步 Milestone branch，或返回 blocked；不得从另一个 Milestone branch、当前 checkout 或 stale branch 猜测来源
   - 非 milestone-derived worktrack 默认 `branch_source_ref = baseline_branch@HEAD`、`integration_target_ref = baseline_branch`、`closeout_target_ref = baseline_branch`
   - `branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref`、`checkpoint_base_ref` 必须写入 Worktrack Contract，供 observe / close / refresh / gate 消费
7. 构建或刷新一份 `工作追踪约定`；有需要时，让草稿与 `templates/contract.template.md` 对齐。
   - **从 Goal Charter 的 Engineering Node Map 中确定本 worktrack 的节点类型**
   - **根据节点类型填充 contract 中的类型化字段**：baseline_branch、baseline_form、merge_required、gate_criteria、if_interrupted_strategy
   - 如果 Goal Charter 未定义 Engineering Node Map，标记为缺失风险并在初始化结果中暴露
   - **Milestone 绑定**（若传入 `target_milestone_id`）：
     - 验证 `target_milestone_id` 在 live milestone-backlog 中存在且 status 为 `active`
     - 验证通过后将 `milestone_id` 写入 Worktrack Contract
     - 标记 `derived_from_milestone: true`（若 worktrack 来自 milestone 的 `worktrack_list`）
     - 若 milestone 不存在或非 active：标记为阻塞并停止，不得静默忽略绑定
8. 使用显式队列项播种一份初始 `计划/任务队列`，而不是只写自由文本任务说明。
9. 产出一份 `调度交接包`，告诉 `调度工作追踪技能` 已播种了什么、还有哪些内容需要调度判断，以及此前轮次是否已存在兼容的下游包。
10. 产出一份固定格式的 `工作追踪初始化结果`。
11. 如果没有命中正式停止条件，交给 `调度工作追踪技能`，让播种后的队列在本轮被刷新，并选出一个当前下一步动作。
12. 只有当活动队列状态中明确存在一份仍然有效、由调度阶段编写的分派包，且不再需要额外调度判断时，才允许直接继续到 `分派技能`。
13. 如果下一条路由尚未可继续，返回被阻塞或受审批门控的初始化结果，而不是假装执行已经开始。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

本技能特有约束：

- 初始化完成的判定条件是分支、基准、约定与初始计划全部明确存在。仅完成分支创建不能被视为初始化完成。
- 工作追踪初始化的合法输出必须是新创建的限定范围分支。复用已存在的实现分支不能被视为成功的工作追踪初始化；应返回被阻塞的初始化结果。
- 播种初始任务列表是调度阶段的种子输入。选出用于执行的当前下一步动作是调度阶段的职责，二者不可等同。
- 本技能唯一合法的分派相关输出是面向调度阶段的种子输出。创建新的权威分派包的行为必须返回 blocked——该职责属于 `dispatch-skills`。
- 本技能的输出只能包含调度交接包。`执行者交接包` 的行为禁止替代调度交接包出现在本技能的输出中。
- 当代码仓库状态含糊不清时，唯一合法行为是返回一个被阻塞的初始化结果。猜测分支、基准或范围的行为必须被阻断。
- baseline branch 的唯一合法来源是 `Worktrack Contract.baseline_branch`。当前分支名不能作为 baseline branch 的来源。
- Worktrack branch 来源与直接 closeout 目标的唯一合法来源是 `Worktrack Contract.branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref` 与 `checkpoint_base_ref`。PR target、merge target 与后续 checkpoint 判定必须来自这些 contract 字段；不得从当前分支名或写死默认分支名推断。
- 仅当预期下一状态与所需审批已显式暴露后，`Harness 控制状态` 的变更才合法；否则必须保持当前控制状态不变并暴露阻断原因。
- 仅当宿主运行时真的能发起分派时，声称回退式 `子代理` 已就绪才合法；否则必须显式暴露运行时缺口或权限阻塞。
- 若传入 `target_milestone_id`，必须验证其存在于 live milestone-backlog 且为 `active`；引用不存在、仅存在于 milestone-history 或非 active 的 milestone 必须返回 blocked。
- milestone 绑定信息（`milestone_id`、`derived_from_milestone`）必须写入 Worktrack Contract，供 `repo-refresh-skill` 在 closeout 时写入 worktrack-backlog。
- milestone 派生 worktrack 必须有上游 `worktrack_intake_review`，且 `intake_review_verdict = ready_for_worktrack_init`、`ready_for_worktrack_init = true`。还必须有 Milestone Review Gate route guard：`milestone_review_gate_ready = true`、`latest_review_status = effective_pass`、`milestone_review_count >= 1`、`effective_review_pass = true`、`latest_review_checkpoint` 非空，且 `review_invalidated_by` 无阻断项。缺失或非 ready 的 intake review / review gate 必须返回 blocked，不得创建分支、不得播种队列、不得进入 Worktrack Init/Dispatch、不得把执行直接交给当前载体。
- Conservative runtime backfill 只能填补 additive runtime 字段的保守默认值：`false`、`unknown`、`missing`、`blocked`、`not ready`、`N/A`。它必须 preserve existing observed facts，must not grant permissions，must not infer programmer confirmation，must not increment counters，must not set effective pass, and must not enable Worktrack Init/Dispatch。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `工作追踪初始化结果`：

- `初始化决策`
- `分支与基准`
- `工作追踪约定`
- `Worktrack Intake Review`
- `初始计划/任务队列`
- `调度交接包`
- `执行者交接包`
- `停止并返回 Harness`

结果中至少应包含以下字段或等价表达：

- `工作追踪编号`
- `工作追踪身份`
- `初始化状态`
- `分支动作`
- `分支名称或规则`
- `基准分支`
- `baseline_branch`
- `branch_source_ref`
- `worktrack_branch`
- `integration_target_ref`
- `closeout_target_ref`
- `final_baseline_branch`
- `checkpoint_base_ref`
- `基准引用`
- `基准理由`
- `PR target 来源`
- `目标`
- `范围内`
- `范围外`
- `受影响模块`
- `节点类型`
- `节点类型来源`
- `worktrack_intake_review`
- `repo_fundamentals`
- `snapshot_freshness`
- `milestone_purpose_alignment`
- `historical_conflict_risk`
- `worktrack_adjustment_recommendations`
- `add_remove_worktrack_recommendations`
- `intake_review_verdict`
- `ready_for_worktrack_init`
- `milestone_review_gate_ready`
- `latest_review_status`
- `milestone_review_count`
- `latest_review_checkpoint`
- `effective_review_pass`
- `review_invalidated_by`
- `基线形式`
- `合并要求`
- `判定标准`
- `中断处理策略`
- `下一状态`
- `验收标准`
- `约束`
- `回滚条件`
- `初始队列项`
- `队列播种状态`
- `初始任务`
- `任务顺序`
- `依赖项`
- `当前阻塞项`
- `调度交接模式`
- `调度交接包`
- `下一动作来源`
- `下一动作`
- `验证要求`
- `所需上下文`
- `已知风险`
- `建议下一路由`
- `需要审批`
- `审批范围`
- `审批理由`
- `执行者交接包`
- `执行尚未开始`
- `可继续`
- `建议下一动作`
- `需要审批`
- `待审批`

## 输出协议

- 先生成尽可能长且完整的 `工作追踪初始化结果`，确保所有初始化信息被记录
- 然后从完整结果中提取 `Control Signal` 层（影响下一动作决策的关键结论）
- `节点类型` 字段必须显式填充；如果 Goal Charter 未定义 Engineering Node Map，在 `Control Signal` 层暴露缺失风险
- 重复性上下文的唯一合法呈现形式是文件路径引用。内联全文的行为禁止发生
- 如果某个字段无实质内容，唯一合法行为是使用 `N/A` 或省略。用占位符填充的行为必须被阻断
- `Supporting Detail` 保留完整内容，只用于后续查阅，不纳入传递上下文

## 资源

当你需要稳定的初始化约定草稿格式时，使用当前 `Harness 控制状态`、`Goal Charter` 中的 `Engineering Node Map`、活动中的代码仓库/工作追踪产物、已存在的当前队列状态，以及 `templates/contract.template.md`。
