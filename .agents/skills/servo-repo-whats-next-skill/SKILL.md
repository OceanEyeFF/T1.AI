---
name: repo-whats-next-skill
description: 当 Harness 处于代码仓库范围，且需要一轮不变更控制状态的限定范围下一步方向判断，并包含轻量级的优先级重构/矛盾分析模式与 overview fallback 模式时，使用这个技能。
---

# 代码仓库下一步技能

## 概览

本技能实现 `RepoScope.Decide` 状态转移算子，对应 Harness 控制回路中的**算子选择**阶段。

这个技能消费上游 `RepoScope.Observe` 算子（如 `repo-status-skill`）产出的结构化状态估计，在合法的状态转移算子集合中（`Observe`、`Init`/进入工作追踪、`Close`/`refresh-repo-state`、`保持并观察`）选择一个算子。它的决策必须投影成显式路由、阻塞项集合与审批状态，供 Harness 消费，而不是文字摘要。本技能的唯一合法行为是返回建议；直接变更 `Harness 控制状态` 的行为必须返回 blocked。

当 `Harness` 已经处于 `代码仓库范围`，并需要对代码仓库最合适的下一步演进方向做一轮限定范围判断时，使用这个技能。

这个技能是一个供 `通用高能力模型` `SubAgent` 使用的决策载体：它会消费一份限定范围代码仓库上下文包，评估当前代码仓库基准和 Milestone Pipeline 状态，并在不直接变更 `Harness 控制状态` 的前提下向 `Harness` 返回建议。

它实现一轮限定范围的 `代码仓库范围.决策`，采用 **Milestone-First** 推理策略：先在 Milestone 层级锚定（是否需要创建/激活/关闭 milestone），再下沉到 Worktrack 层级派生执行单元。它的工作是选出一个代码仓库动作，然后把这个决策投影成显式的继续路由、审批状态与阻塞项集合，让 `Harness` 无需重新解释文字就能消费。

当本轮是 pre-milestone 讨论、任务点归纳或“还有什么可推进”查询时，本技能可以输出 candidate milestone recommendation。该 recommendation 是 RepoScope.Decide 的建议，不是已获批准的 milestone，也不是 Worktrack task queue。推荐必须先列 `observed_facts`、`inferred_assumptions`、`unknowns`，再给出 `primary_contradiction` 与 `main_aspect_now`；candidate milestone brief 必须包含目标、证据、预期改变、验收信号、主要风险和 programmer confirmation requirement。通常只给 1 到 3 个候选；证据不足时应输出调研问题或保持观察，而不是创建 Milestone。

当已有新鲜的 `代码仓库状态摘要`，或者 `Harness` 明确希望先拿到稳定观察包时，这个技能可以消费该摘要。但在没有现成 `代码仓库状态技能` 输出时，它仍必须能直接基于代码仓库真相运行。

它的主要判断依据是代码仓库级真相：

- `代码仓库目标/章程`
- `代码仓库快照/状态`
- 当前 `Harness 控制状态`
- 可选的新鲜 `Repo Analysis` artifact

`工作追踪约定` 和 `计划/任务队列` / `Plan / Task Queue` 不是代码仓库级任务来源。它们只能作为关于当前活动中或刚关闭工作追踪的边界证据被查询，例如前一个切片是否完成、继续权限是否受限、或某个交接包是否仍在生效。一个关闭的队列不代表代码仓库没有下一步，只代表那个工作追踪的本地执行序列或 task window 已经结束。本技能对 `.servo/worktrack/*` 的唯一合法行为是将其读取为边界证据；更新或重写 `.servo/worktrack/*` 的行为必须返回 blocked。

这个技能有一条默认决策路径、一个内嵌的 `优先级重构/矛盾分析` 模式，以及一个只在完全找不到可更新内容时启用的 `overview fallback` 模式。这些模式都属于这个 `代码仓库范围` 技能本身，不是独立技能，不是 `工作追踪范围` 技能，也不是产出长篇战略报告的许可。

这个文档是标准可执行骨架。它定义了该模式的限定范围操作格式与输出约定，但并不声称已经存在一套完全自动化的规划器或监督器实现。

## 路由边界

这个标准技能保留完整的 `代码仓库范围.决策` 动作空间，但任何缩窄路由支持范围的已部署负载配置，仍然是当前轮次的活动约定。

当这个技能通过一个被收窄的部署配置被消费时，应把该配置视为硬路由边界，而不是可选的适配器元数据。对当前 `agents` 第一波配置而言，有效的 `支持的代码仓库动作` 子集是：

- `进入工作追踪`
- `保持并观察`

在这个第一波边界下：

- 继续把 `刷新代码仓库状态` 作为标准可能性保留下来，但在当前轮中标记为 `范围外`
- 唯一合法行为是在活动路由边界内推荐代码仓库动作；推荐或输出不受支持的代码仓库动作的行为必须返回 blocked。
- 如果最佳的标准动作落在当前活动子集之外，就把本轮降级为 `保持并观察`，并在 `决策约束`、`继续阻塞项` 或 `最小缺失信息` 中解释缺失的配置支持或审批边界

## 何时使用

当当前问题不是"谁来执行某个工作项"，而是"代码仓库在 `代码仓库范围` 下下一步应该做什么"时，使用这个技能：

- 判断下一方向是否应该是：
  - 进入一个新的 `工作追踪范围`
  - 刷新代码仓库基准或代码仓库状态
  - 继续停留在 `代码仓库范围`，直到缺失证据被补齐
- 解释为什么这个方向是当前最优动作
- 当存在多个看似合理但没有决定性首选项的方向时，重新框定代码仓库优先级
- 暴露下一轮所需的最小前置条件和限定范围上下文
- 把建议返回给 `Harness`；只有当所选路由真正跨越正式审批边界时，才显式提出程序员审批

当以下至少一个条件成立时，使用内嵌的 `优先级重构/矛盾分析` 模式：

- 代码仓库存在多个看似合理的下一方向，但没有明确的一步先手
- 当前路径看起来很忙，但并不决定性
- 时间、范围或资源相较于既定目标明显更紧
- 某轮 `工作追踪范围` 刚关闭或停滞，代码仓库级优先级可能需要重构

本技能的输出仅限于一轮 `代码仓库范围` 判定；把它当成工作追踪规划或执行分派替代品的行为禁止出现。它仍然是一轮 `代码仓库范围` 判定。

当默认 `下一步方向` 模式无法找到可信的可更新内容，且当前 repo truth 没有明确阻止继续分析时，启用 `overview fallback` 模式：

- 默认模式只能得到空泛的 `保持并观察`
- 当前 repo truth 没有明确阻止继续分析
- Harness 需要一份未来可用 worktrack 候选建议，而不是立即执行

`overview fallback` 可参考基本面与矛盾分析方法（如当前部署中可用的 `project-dialectic-planning-skill` 等全局分析技能），唯一合法行为是压缩为 repo 级下一步判定输出；扩展成大型战略报告的行为必须返回 blocked。该外部参考为可选增强路径；不存在时，唯一合法行为是继续执行 overview fallback 的正常流程；阻塞行为必须标记为超出本技能权限。

## 工作流

1. 确认这是一轮 `代码仓库范围` 判定，而不是 `工作追踪范围` 规划或执行。
2. 载入本轮判定所需的最小代码仓库产物与当前控制状态视图；如果当前 `代码仓库状态摘要` 已经存在，应优先使用；仅允许将其作为可选增强输入，禁止将其设为硬前置条件。
3. 如果存在新鲜 `Repo Analysis` artifact，可以把它作为结构化判定输入；它必须从属于 `代码仓库目标/章程` 与 `代码仓库快照/状态`；替代目标真相或工作追踪队列的行为禁止出现。
4. 从 `Harness 控制状态` 读取当前 `继续权限` 策略，尤其是在前一个工作追踪刚在 `约定边界` 收束时。
5. 如果一个刚关闭或仍在活动中的工作追踪会影响判断，就只读取理解边界所需的最小 `工作追踪约定` 或 `计划/任务队列` 字段。工作追踪产物的唯一合法角色是判定边界证据；把它们重新当成代码仓库的全局待办列表的行为禁止出现。
6. 解析当前安装或负载的活动路由边界。如果当前部署配置缩窄了 `支持的代码仓库动作`，要先记录这个收窄后的子集，再去推理下一步。
7. 选择运行模式，并记录触发原因：
   - 默认 `下一步方向` 模式
   - `优先级重构/矛盾分析` 模式
   - `overview fallback` 模式
8. 为当前 `通用高能力模型` 推理轮构建一份限定范围代码仓库判定包。
9. 评估允许的候选代码仓库动作：
   - `进入工作追踪`
   - `刷新代码仓库状态`
   - `保持并观察`
10. 把标准动作集合与当前活动路由边界取交集。如果边界比标准集合更窄，就只把不受支持的动作保留为阻塞或范围外上下文。
11. 如果前一个工作追踪刚关闭，且 `约定后自动性：最小委派` 正在生效，那么任何自动 `进入工作追踪` 建议都必须被限制在已批准的低风险类别中的一个同目标限定范围切片。
12. 执行 Milestone-First 判定：
    若 `active_milestone` 为空（无活跃 Milestone）：
      a. 读取 milestone-backlog，检查所有 planned/active milestone
      b. 语义匹配：将当前待处理的工作与已有 milestone 的 purpose/worktrack_list 进行语义匹配
         - 全部匹配某个 milestone → `suggested_milestone_action = "append_worktracks"`，输出 `suggested_milestone_id`，并要求下游 `init-milestone-skill` 执行 `coverage_verdict` 检查
         - 拆分匹配（分别归入不同 milestone）→ 分别输出匹配结果，建议 programmer 确认
         - 无匹配 → 进入步骤 c
      c. 内聚性判断：评估待处理工作之间是否存在语义内聚（是否服务于同一可表述的目的）
         - 有内聚 → `suggested_milestone_action = "create"`，路由到 goal-driven 路径：暂停，要求 programmer 定义 milestone（purpose/completion_signals/acceptance_criteria/completion_threshold_pct）
         - 无内聚 → `suggested_milestone_action = "create"`，路由到 work-collection 路径：harness 自动创建 work-collection milestone（`milestone_kind = "work-collection"`，名称 = `工作集合 MS-YYYYMMDD-NNN`，priority = 最低，直接激活）
      d. 读取 milestone-backlog，检查是否存在满足激活条件的 planned milestone
         - 若存在：`suggested_milestone_action = "activate"`，输出 `suggested_milestone_id`
      e. `suggested_next_scope = "RepoScope"`，绑定 `init-milestone-skill`
      f. 若本轮建议 `create` / `activate` / `append_worktracks`，必须同时输出结构化 `milestone_brief`，并将 `需要审批 = true`、`审批理由 = "milestone brief 待 programmer 确认"`
      f1. 当输出 candidate milestone recommendation 时，必须显式标记 `candidate_only = true`，并区分 `observed_facts` / `inferred_assumptions` / `unknowns`。candidate brief 不得写入 live milestone-backlog，不得增加 progress counter，不得把 candidate worktracks 写入 `.servo/worktrack/*`。只有 programmer confirmation 后，才可把该 brief 交给 `init-milestone-skill`。
      f2. 若命中 complex-project trigger，必须同时输出或消费 `complex_project_entry_gate`。`milestone_blocking_decision` 包含 `block_create`、`block_upsert` 或 `block_activate` 时，推荐 `保持并观察` 或 reinforcement documentation / project-understanding Milestone，不得绑定 `init-milestone-skill` 执行被阻断动作。若 `entry_verdict = needs_reinforcement_milestone`、`reinforcement_milestone_recommendation.needed = true`、`recommendation_status = recommended|required|pending_operator_review` 或 `blocks_implementation_until_resolved = true`，只能推荐 reinforcement documentation / project-understanding Milestone brief，且不能把 implementation-oriented create / activate / append_worktracks 投影为可绑定路由。若 gate 缺失、空白、placeholder、`pending_programmer_confirmation` 或字段不全，按 unresolved gate blocking default 处理，不得把 create / activate / append_worktracks 建议投影成可绑定的 `init-milestone-skill` 路由。Canonical terms: missing, blank, placeholder, pending, incomplete, not_applicable。
      g. **禁止在此分支建议"进入工作追踪"**（work-collection 路径是合法例外：work-collection milestone 激活后可直接进入 WorktrackScope）
      h. 输出 `milestone_kind` 字段，供下游 skill 分派
    若存在活跃 Milestone 且 `milestone_acceptance_verdict` 为 `not_achieved`（未完成）：
      - 若 active milestone 或当前候选 worktrack 命中 complex-project trigger，先消费 `complex_project_entry_gate`
      - `complex_project_entry_gate` 是 Milestone-side blocking gate, not fixed heavy mode；scanner output is evidence, not verdict
      - 若 `milestone_blocking_decision` 包含 `block_derive_worktrack`，推荐 `保持并观察`，在继续阻塞项中写明 `operator_safety_policy`、`dialog_review_questions` 或 `reinforcement_milestone_recommendation` 缺口，不得进入 WorktrackScope.Init
      - 若 `entry_verdict = needs_reinforcement_milestone`、`reinforcement_milestone_recommendation.needed = true`、`recommendation_status = recommended|required|pending_operator_review` 或 `blocks_implementation_until_resolved = true`，推荐 reinforcement documentation / project-understanding Milestone，不得把当前候选派生为 implementation-oriented Worktrack；temporary understanding 只能作为 runtime evidence, not Goal Charter truth
      - 若 gate 缺失、空白、placeholder、`pending_programmer_confirmation` 或字段不全，按 unresolved gate blocking default 处理，不得把候选 worktrack 派生为 ready。Canonical terms: missing, blank, placeholder, pending, incomplete, not_applicable。
      - 检查 Milestone Review Gate route guard：goal-driven active milestone 必须有 `milestone_review_gate_ready = true`、`latest_review_status = effective_pass`、`milestone_review_count >= 1`、`effective_review_pass = true`、`latest_review_checkpoint` 非空，且 `review_invalidated_by` 无阻断项。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全必须设置 `intake_review_verdict = blocked`，在继续阻塞项中写明 `milestone_review_gate_not_ready`，不得推荐 WorktrackScope.Init 或 Worktrack Init/Dispatch。
      - 若 `.servo` runtime artifact 缺少新添加字段，只能使用 conservative runtime backfill：缺失值按 `false`、`unknown`、`missing`、`blocked`、`not ready` 或 `N/A` 处理。Backfill 是 forward-only runtime evidence，不得推断 programmer confirmation、不得扩大权限、不得增加 `milestone_review_count`、不得把 `effective_review_pass` 或 `milestone_review_gate_ready` 设为 true；缺失 review/backfill 字段必须保持 `milestone_review_gate_not_ready`。
      - 先从活跃 Milestone 的 `worktrack_list` 中选取下一个待执行的 worktrack，并对照 worktrack-backlog 过滤已完成/已阻塞/已推迟的 worktrack
      - RepoScope.Decide / Milestone-level scheduler 每轮一次只输出一个 `selected_worktrack_id` / current worktrack；不得把整个 `worktrack_list` 批量转成 Worktrack `Plan / Task Queue`、task window 或 dispatch queue
      - 将选中的 current worktrack 组织为一个独立执行单元：它拥有自己的 branch、contract、plan-task-queue、verify、closeout 和 repo-refresh 追踪，然后再回到 milestone 上下文继续推进
      - 若 `worktrack_list` 为空或全部完成但 `milestone_gate_verdict != "pass"`：不得自动创建补救 worktrack；应触发 handback，要求先处理 `Milestone Gate`
      - 若 `worktrack_list` 为空或全部完成且 `milestone_gate_verdict == "pass"` 但 `purpose_achieved == false`：触发 milestone 重新评估（handback），不得通过静默追加 worktrack 扩边界
      - 仅当仍存在合法待执行 worktrack，且 `milestone_gate_verdict` 未形成上层阻断时，才从 milestone 上下文推导 `suggested_node_type`（优先使用 milestone 声明的，fallback 到 Goal Charter 的 Engineering Node Map）
      - 仅当上述条件成立时，必须先生成结构化 `worktrack_intake_review`，作为进入 WorktrackScope.Init 的前置判定：
        - `repo_fundamentals`：当前 active milestone、目标/非目标、baseline branch、已关闭 worktrack、release/package/deploy 禁止项是否仍一致
        - `snapshot_freshness`：`Repo Snapshot/Status`、`Harness Control State`、milestone-backlog、worktrack-backlog 与当前 git HEAD 是否足够新鲜，是否需要先 `refresh_required`
        - `milestone_purpose_alignment`：候选 worktrack 是否仍服务于 active milestone 的 purpose、completion_signals 和 acceptance_criteria
        - `historical_conflict_risk`：候选 worktrack 是否与刚关闭 worktrack、历史决策、既有文档真相、待处理阻塞项或 handback 边界冲突
        - `worktrack_adjustment_recommendations`：是否建议保持、拆分、合并、改写、推迟、阻塞当前候选 worktrack
        - `add_remove_worktrack_recommendations`：是否需要新增、移除或重排 worktrack；若不需要必须显式写 `none`
        - `intake_review_verdict`：`ready_for_worktrack_init` / `refresh_required` / `adjust_worktracks` / `blocked`
        - `ready_for_worktrack_init`：布尔值，只能在 verdict 为 `ready_for_worktrack_init` 且无阻塞时为 true
      - 若 `intake_review_verdict == "refresh_required"`：`suggested_next_scope = "RepoScope"`，推荐刷新/观察，不得绑定 `init-worktrack-skill`
      - 若 `intake_review_verdict == "adjust_worktracks"`：返回 `suggested_milestone_action = "append_worktracks"` 或结构化调整建议；需要 programmer 确认的范围变更必须设置 `需要审批 = true`
      - 若 `intake_review_verdict == "blocked"`：推荐 `保持并观察`，在继续阻塞项中写明原因，不得进入 WorktrackScope.Init
      - 仅当 `worktrack_intake_review.ready_for_worktrack_init == true` 时：`suggested_next_scope = "WorktrackScope"`，绑定 `init-worktrack-skill`
      - 仅当 `worktrack_intake_review.ready_for_worktrack_init == true` 时：`derived_from_milestone = true`，`target_milestone_id = <active_milestone>`，并把完整 `worktrack_intake_review` 交给 `init-worktrack-skill`
    若存在活跃 Milestone 且 `milestone_acceptance_verdict` 为 `achieved`（已完成）：
      - `suggested_milestone_action = "closeout"`
      - `recommended_repo_action = "保持并观察"`
      - 设置 `需要审批 = true`（milestone closeout 需 programmer 验收）
      - 检查 pipeline 下一个可激活的 planned milestone，输出 `pipeline_advancement_hint`
      - `handback_required = true`
    若存在活跃 Milestone 且 `milestone_acceptance_verdict` 为 `blocked`：
      - 在 `继续阻塞项` 中反映 Milestone 阻塞状态
      - `recommended_repo_action = "保持并观察"`
      - 阻止自动 `进入工作追踪`（即使存在剩余 autonomy budget）
      - 返回控制权等待 developer 决策
13. 当建议 `进入工作追踪` 且 `derived_from_milestone == true` 时，从活跃 Milestone 的上下文推导 `suggested_node_type`：
    - 优先使用 Milestone 的 `worktrack_list` 中该 worktrack 声明的 node_type
    - Fallback 到 Goal Charter 的 `Engineering Node Map` 匹配
    - 在输出中携带 `target_milestone_id` 和 `derived_from_milestone`，供 `init-worktrack-skill` 绑定 milestone 关联
    - 在输出中携带当前 worktrack 的独立执行语义，供 `init-worktrack-skill` 建立专属 branch / contract / queue / closeout traceability
    - 如果无法建议节点类型，应把缺口暴露为初始化风险
14. 只推荐一个代码仓库动作，解释为什么它是当前最高优先级，并把该决策投影成显式继续路由、阻塞项集合与审批状态。
15. 向 `Harness` 返回一份固定格式的 `代码仓库下一步判定`。
16. 如果选中的路由已经获批，且没有命中正式停止条件，就允许监督器直接继续进入相应的下一范围。

## 正式停止条件

至少在以下任一条件成立时停止并返回控制权：

- 证据太弱，无法支持决定性的代码仓库动作，因此结果必须停留在 `保持并观察`
- 所选路由跨越了权限边界，因此需要把 `需要审批` 置为 `真`
- 本轮允许的代码仓库动作集合中已经不存在合法候选路由

## 优先级重构/矛盾分析模式

当这个模式启用时，把本轮压缩成一次限定范围的代码仓库级矛盾判定：

- 区分 `事实`、`推断` 与 `未知项`
- 只识别一个 `当前主要矛盾`
- 识别该矛盾当前的 `主要方面`
- 只命名一个 `当前最高优先级`
- 给出一份简短的 `不要做的事` 列表，用于剔除干扰而不是给答案注水
- 把该优先级映射到一个明确的 `建议代码仓库动作`
- 只暴露下一次代码仓库判定所需的 `最小缺失信息`

如果本轮消费 `Repo Analysis` artifact，必须先检查它的 baseline 是否仍匹配当前 `代码仓库快照/状态`。如果 baseline 过期，只能把它作为历史参考，不能直接沿用其中的 `recommended_repo_action`。

如果证据太弱，无法支持决定性的代码仓库动作，就建议 `保持并观察` 并附带最小缺失信息。如果矛盾只能通过改变代码仓库目标才能解决，唯一合法行为是返回 `保持并观察`，并在 `决策约束` 中说明目标级变更必须由外部请求触发 `ChangeGoal`；本 skill 内部处理目标变更的行为必须返回 blocked。如果矛盾已经准备好进入执行，就建议进入 `工作追踪范围`；当下一条路由已经获批且安全时，监督器继续推进可以在无需额外程序员交接的情况下继续。

如果活动路由边界比宽泛的标准答案更窄，唯一合法行为是在活动路由边界内推荐路由；仅仅因为在概念上正确就输出不受支持路由的行为必须返回 blocked。应把不受支持的分支保留在 `范围外`，解释约束，并回退到 `保持并观察`，除非当前配置明确允许更宽的路由。

当当前矛盾是"已批准的工作追踪已完成，但当前目标仍允许一个明显的低风险后续切片"时，只有在以下条件全部满足时才允许自动继续：

- `约定后自动性：最小委派`
- `自动范围：仅当前目标`
- 自动预算仍有余额
- 候选切片必须停留在以下类别之一：
  - `验证加固`
  - `文档与代码对齐`
  - `打包与入口清理`
  - `不改变行为的小重构`

如果这些条件有任意一个失败，唯一合法行为是路由到 `保持并观察`；把 `继续工作` 重新解释成发明新范围许可的行为必须返回 blocked；应改为路由到 `保持并观察`。

## Overview Fallback 模式

当默认模式和优先级重构模式都无法找到可更新内容时，本模式用于提高未来可用 worktrack 的发现效率。它只产出候选建议和一个推荐方向，不创建工作追踪，不修改 `.servo/worktrack/*`，不改变 Harness 控制状态。

使用本模式时：

- 先读取 `references/overview-fallback-mode.md`
- 用 `Facts / Inferences / Unknowns` 区分事实、推断和未知项
- 快速扫描产品/用户价值、Harness 控制闭环、deploy / installer / release、docs truth boundary、review / verify / governance、cross-platform operator experience
- 找出一个当前主要矛盾
- 输出最多 5 个候选 worktrack，每个候选都必须有小的可验证 first slice
- 只推荐一个 `top_candidate`
- 把结果折回 `recommended_repo_action`、`recommended_next_route`、approval 字段与 continuation 字段

如果活动路由边界不允许进入工作追踪，就必须把候选作为建议返回，并把实际 `recommended_repo_action` 降级为 `保持并观察`。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- `计划/任务队列` 的输出角色仅限于工作追踪本地执行序列记录；将其当成代码仓库级待办列表的行为，或将 `队列状态：已完成` 当成代码仓库没有下一步证据的行为禁止出现。
- 停留在当前部署配置的活动路由边界内。如果活动路由边界比标准动作集合更窄，唯一合法行为是在边界内推荐路由；推荐不受支持路由的行为必须返回 blocked。
- 仅当默认模式和优先级重构模式都找不到可信的下一步时，`overview fallback` 启用才合法；默认模式或优先级重构模式已有明确下一步时，启用 `overview fallback` 的行为必须返回 blocked。
- `overview fallback` 只能生成未来 worktrack 候选建议，不能直接创建或执行 worktrack。
- **Milestone-First**：无 active milestone 时，"进入工作追踪" 路由必须 blocked，必须优先建议创建或激活 milestone。work-collection milestone 路径是合法例外：无内聚任务可由 harness 自动创建 work-collection milestone 后进入 WorktrackScope。
- `Milestone Gate` 是 goal-driven milestone 的上层集成验收，不替代 worktrack gate；`milestone_gate_verdict != "pass"` 时不得自动继续派生新 worktrack 来“补过”集成失败。
- `complex_project_entry_gate` 是 Milestone-side blocking gate, not fixed heavy mode；在 create / upsert / activate / derive-worktrack 前必须尊重 `milestone_blocking_decision`。
- 缺失、空白、placeholder、pending 或 incomplete `complex_project_entry_gate` 不得被解释为 `clear` 或 `not_applicable`；必须阻断 derive-worktrack 并返回 `保持并观察` 或 reinforcement documentation / project-understanding Milestone 建议。
- scanner output is evidence, not verdict；`scanner_evidence_ref` 和 `complexity_signals` 只能作为判定依据，不能替代 programmer confirmation、`operator_safety_policy` 或 `dialog_review_questions`。
- Worktrack execution modes `normal`、`autoreview`、`yolo` 是 user-owned safety policy，不替代 Milestone-side blocker。
- 弱文档命中且当前理解不足时，优先推荐 reinforcement documentation / project-understanding Milestone，并通过 `reinforcement_milestone_recommendation` 暴露。
- `reinforcement_milestone_recommendation` 必须保留 `needed`、`recommendation_status`、`recommendation_type`、`suggested_title` 或 `suggested_purpose`、`reason` 或 `recommendation_reason`、`temporary_understanding_ref`、`evidence_refs`、`confirmation_required` 与 `blocks_implementation_until_resolved`；`needed = true`、`recommendation_status = recommended|required|pending_operator_review` 或 `blocks_implementation_until_resolved = true` 阻断实现型 Worktrack 派生，`needed = false` 且 `recommendation_status = not_needed` 不应阻断低风险 `clear` / `not_applicable` gate。
- milestone closeout（`milestone_acceptance_verdict == achieved`）需 programmer 审批（`需要审批 = true`），不得自动推进。
- 建议 `create` / `activate` / `append_worktracks` 时必须附带结构化 `milestone brief`；在 programmer 确认前不得把该建议伪装成已获准的自动路由。
- Candidate milestone recommendation 必须是 fact-first / field-research：先 `observed_facts`，再 `inferred_assumptions`，再 `unknowns`，再 `primary_contradiction` 与 `main_aspect_now`。候选 brief 是 recommendation，不是 live backlog truth；不得自动 create / activate / append。
- 若追加 worktrack 只有在确认归属当前 milestone 且不触发 `coverage_verdict = not_covered` 时才可继续；否则应建议其他 milestone，避免静默 scope creep。
- 从 milestone 派生 worktrack 时必须携带 `target_milestone_id` 供 `init-worktrack-skill` 绑定。
- 从 active milestone 派生 worktrack 时必须携带唯一 `selected_worktrack_id` / current worktrack。一次 RepoScope.Decide 不得选择多个 worktrack；若需要新增、移除、重排或批量调整 worktrack，必须返回 RepoScope.Decide / append-worktrack 路由和必要的 programmer approval。
- 从 active milestone 派生 worktrack 时必须携带 `worktrack_intake_review`，且只有 `intake_review_verdict = ready_for_worktrack_init` 与 `ready_for_worktrack_init = true` 才能进入 WorktrackScope.Init。缺失 `repo_fundamentals`、`snapshot_freshness`、`milestone_purpose_alignment`、`historical_conflict_risk`、`worktrack_adjustment_recommendations` 或 `add_remove_worktrack_recommendations` 任一字段时，推荐 Init 的行为必须返回 blocked。
- 从 active goal-driven milestone 派生 worktrack 时还必须满足 Milestone Review Gate route guard：`latest_review_status = effective_pass`、`milestone_review_count >= 1`、`effective_review_pass = true`、`latest_review_checkpoint` 非空，且 `review_invalidated_by` 未标记 `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 变化。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全必须返回 blocked，不得当成 ready。
- 缺少 additive `.servo` 字段时必须执行 conservative runtime backfill：`false`、`unknown`、`missing`、`blocked`、`not ready`、`N/A`；forward-only；preserve existing observed facts；must not grant permissions；must not infer programmer confirmation；must not increment counters；must not enable Worktrack Init/Dispatch。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `代码仓库下一步判定`：

- `模式`
- `模式触发原因`
- `事实`
- `推断`
- `未知项`
- `当前主要矛盾`
- `主要方面`
- `当前最高优先级`
- `不要做的事`
- `overview_trigger_reason`
- `overview_scan`
- `candidate_worktracks`
- `top_candidate`
- `top_candidate_reason`
- `建议代码仓库动作`
- `路由/审批判定`
- `最小缺失信息`
- `返回 Harness`

结果中至少应包含以下字段或等价表达：

- `当前阶段`
- `模式`
- `模式触发理由`
- `事实`
- `推断`
- `未知项`
- `当前主要矛盾`
- `主要方面`
- `当前最高优先级`
- `不要做的事`
- `建议代码仓库动作`
- `suggested_node_type`
- `suggested_node_type_reason`
- `允许的下一路由`
- `建议下一路由`
- `建议下一范围`
- `允许的代码仓库动作`
- `路由边界来源`
- `约定后自动性`
- `自动候选类别`
- `剩余自动预算`
- `范围内`
- `范围外`
- `决策约束`
- `选择依据`
- `选择理由`
- `最小缺失信息`
- `请求变更控制状态`
- `可继续`
- `继续阻塞项`
- `需要审批`
- `审批范围`
- `审批理由`
- `需要程序员审批`
- `如何审查`
- `active_milestone_id`
- `milestone_pipeline_state`
- `suggested_milestone_action`：activate / create / continue / closeout / none / append_worktracks
- `suggested_milestone_id`
- `milestone_kind`：goal-driven / work-collection / N/A（与 suggested_milestone_action 联动）
- `milestone_brief`
- `milestone_brief_required`
- `milestone_reevaluation_required`
- `milestone_reevaluation_reason`
- `derived_from_milestone`
- `target_milestone_id`
- `selected_worktrack_id`
- `current_worktrack`
- `pipeline_advancement_hint`
- `worktrack_intake_review`
- `complex_project_entry_gate`
- `scanner_evidence_ref`
- `complexity_signals`
- `operator_safety_policy`
- `dialog_review_questions`
- `milestone_blocking_decision`
- `reinforcement_milestone_recommendation`
- `repo_fundamentals`
- `snapshot_freshness`
- `milestone_purpose_alignment`
- `historical_conflict_risk`
- `worktrack_adjustment_recommendations`
- `add_remove_worktrack_recommendations`
- `intake_review_verdict`
- `ready_for_worktrack_init`

当活动部署配置缩窄了路由空间时，`允许的代码仓库动作`、`允许的下一路由`、`范围外` 与 `决策约束` 必须反映这个收窄后的子集，而不是完整的标准动作空间。

如果默认模式已经足够，且不需要完整的矛盾重构，就与矛盾相关的章节必须保持简短；展开成报告的行为必须返回 blocked。输出仍应保持限定范围且面向判定。

如果启用 `overview fallback`，必须显式设置 `模式：overview-fallback`，并说明为什么默认模式和优先级重构模式都不足以发现可用下一步。

## 资源

使用当前 `Harness 控制状态`、当前 `代码仓库目标/章程` 与当前 `代码仓库快照/状态` 作为本轮判定的主要输入。若当前 `代码仓库状态摘要` 可用，就使用它；仅允许将其作为可选输入，禁止将其设为前置条件。只有当当前代码仓库判定依赖于一个活动中或刚关闭工作追踪的边界时，才读取 `工作追踪约定` 或 `计划/任务队列`，并把它们视为本地边界证据，而不是代码仓库级任务库存。只有当本轮实际进入 `优先级重构/矛盾分析` 模式时，才读取 `references/priority-reframe-mode.md`；只有当默认模式和优先级重构都找不到可用更新方向时，才读取 `references/overview-fallback-mode.md`。
