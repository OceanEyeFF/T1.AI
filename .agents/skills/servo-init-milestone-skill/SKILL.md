---
name: init-milestone-skill
description: 当 Harness 处于 RepoScope 且需要创建或注册一个新的 Milestone 到 Pipeline 中时使用这个技能；它是 RepoScope.Init 的 Milestone 初始化算子，负责创建 milestone artifact、upsert milestone-backlog、处理 latest-override 和激活规则，不修改 version/release 状态。
---

# 初始化 Milestone 技能

## 概览

把这个技能作为 `Codex` 中 `RepoScope` 下的 Milestone 初始化算子使用。

本技能实现 `RepoScope.Init` 状态转移算子的 Milestone 维度，对应 Harness 控制回路中为 Milestone Pipeline 创建/注册新 milestone 的初始化动作。它是 Pipeline 的**入口算子**：接收 programmer 或 harness 的 milestone 规格，验证唯一性和依赖合法性，先输出结构化 `milestone brief` 等待 programmer 确认，再按 latest-override 语义写入 milestone artifact 和 milestone-backlog，处理激活规则（同一时刻仅一个 active），并产出结构化的初始化结果供 `RepoScope.Decide` 和 `harness-skill` 消费。

它的角色是**初始化 Milestone**，而不是分析 Milestone 状态或驱动 next action。它产出的是经验证、已写入的 Milestone 初始化结果，包括新 milestone 的 artifact 路径、pipeline 位置和激活状态。

它的主要输入是 programmer 或 harness 提供的 milestone 规格：

- 上游 `pre-milestone-intake-skill` 产出的 `pre_milestone_intake_review`（当需求模糊、高风险、跨 repo、大型无文档、release/publish/migration 或 Harness 合同变更时必需）
- 上游或 runtime artifact 提供的 `complex_project_entry_gate`（当复杂项目、弱文档、高风险操作或跨系统 milestone 进入前需要 Milestone-side blocking gate 时必需）
- Programmer 直接提供的 milestone 规格（title、purpose、worktrack_list、priority、activation_rules、completion_threshold_pct 等）
- Harness 从 Goal Charter 和 repo snapshot 推理出的 milestone 建议（需经本技能验证后写入）
- 当前 live milestone-backlog（`.servo/repo/milestone-backlog.md`）用于唯一性检查和 pipeline 上下文；milestone-history（`.servo/repo/milestone-history.md`）用于依赖解析和历史冲突检查
- 当前 control-state（`.servo/control-state.md`）用于 active milestone 状态

本技能对 `.servo/milestone/` 的写入是创建或 upsert 单个 milestone artifact；对 `.servo/repo/milestone-backlog.md` 的写入是按 milestone_id upsert live 条目。依赖解析可读取 `.servo/repo/milestone-history.md`，但本技能不把 completed/superseded 条目写回 live backlog。本技能不修改 version/release 状态，不触发 worktrack 初始化。

## 何时使用

当当前问题不是"milestone 进展如何"，而是"需要创建或注册一个 milestone"时，使用这个技能：

- Programmer 显式声明一个新的 milestone 目标
- Harness 在 `RepoScope.Decide` 阶段推理出需要创建新 milestone 来组织 worktrack
- `repo-whats-next-skill` 输出 `suggested_milestone_action == "create"` 时（goal-driven 或 work-collection 路径）
- 需要更新已有 milestone（upsert）——如补充 worktrack_list、调整 priority
- Pipeline 中没有符合条件的 planned milestone 可激活时
- 向已有 goal-driven milestone 追加 worktrack 时（触发信号覆盖判定）

## 工作流

1. 确认这是一轮 Milestone 初始化轮次，不是 Milestone 状态分析或 Worktrack 初始化。
2. 读取当前 live milestone-backlog（`.servo/repo/milestone-backlog.md`）、milestone-history（`.servo/repo/milestone-history.md`，若存在）和 control-state（`.servo/control-state.md`）获取 pipeline 上下文。
3. 检查 `pre_milestone_intake_review`：
   - 当 milestone creation/upsert/activation 命中以下任一触发条件时，必须存在 intake review：需求模糊；release/publish/migration；数据、权限、安全、兼容性或部署边界；多 repo/跨系统；大型无文档或弱文档代码库；Harness doctrine、artifact contract、canonical skill 或 workflow family 变更。
   - intake review 必须包含 `intake_status`、`request_summary`、`observed_facts`、`inferred_assumptions`、`unknowns`、`programmer_decisions_required`、`risk_flags`、`open_questions`、`answered_questions`、`unresolved_questions`、`continuation_state`、`continuation_reason`、`next_required_question`、`next_question_blocks_ready`、`why_it_matters`、`recommended_answer`、`tradeoff`、`recommended_answers`、`scope_boundary`、`out_of_scope`、`non_goals`、`acceptance_signals`、`suggested_milestone_brief`、`confirmation_required`、`programmer_confirmed`、`ready_for_init_milestone`、`intake_skipped`、`skip_reason`、`accepted_risk`、`residual_risk_accepted`、`accepted_residual_risk`、`handoff_to_init_milestone` 和 `template_contract_ref`。
   - 正常 ready handoff 的唯一可继续条件是 `intake_status == "ready"`、`ready_for_init_milestone == true`、`programmer_confirmed == true` 且 `intake_skipped == false`。
   - `intake_status == "skipped"` 只能表示 programmer 显式接受跳过 intake 的风险；必须同时记录 `intake_skipped = true`、`skip_reason`、`accepted_risk` 和 programmer confirmation。skipped 不等同 ready；本技能不自动 create / upsert / activate，必须 handback 给 programmer 或 RepoScope.Decide 暴露 approval 状态，除非本轮输入同时携带明确的“跳过 intake 后仍允许初始化”的 programmer 授权。
   - `intake_status == "questions_required"` 时，必须返回 blocked 并带回 `continuation_state` 和 `next_required_question`，建议回到 `pre-milestone-intake-skill` 继续 one-question-at-a-time；不得创建、upsert 或激活 milestone。
   - `intake_status == "blocked"` 时，必须返回 blocked 并建议回到 `pre-milestone-intake-skill` 或 programmer 决策；不得创建、upsert 或激活 milestone。
   - intake review 缺失、字段不全、状态矛盾（例如 skipped 同时 ready）、或未 ready 时，返回 blocked，建议先调用 `pre-milestone-intake-skill`，不得把薄弱的 milestone brief 伪装成已确认。
4. 检查 `complex_project_entry_gate`：
   - 当 milestone creation/upsert/activation 命中复杂项目、弱文档、高风险操作或跨系统触发条件时，必须存在 `complex_project_entry_gate`。
   - gate 必须包含 `scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 和 `reinforcement_milestone_recommendation`。
   - scanner output is evidence, not verdict；不得把 scanner 阈值直接当成 ready 结论。
   - `complex_project_entry_gate` 是 Milestone-side blocking gate, not fixed heavy mode；低风险请求可用 `entry_verdict = not_applicable` 轻量跳过。
   - Worktrack execution modes `normal`、`autoreview`、`yolo` 是 user-owned safety policy，不替代 Milestone-side blocker。
   - 缺失、空白、placeholder、`pending_programmer_confirmation` 或字段不全的 gate 不得被解释为 clear；必须按 unresolved gate blocking default 处理。Canonical terms: missing, blank, placeholder, pending, incomplete, not_applicable。
   - 若 `entry_verdict = blocked`，或 `milestone_blocking_decision` 包含 `block_create`、`block_upsert` 或 `block_activate`，必须返回 blocked，不得 create / upsert / activate implementation-oriented milestone。
   - 若 `entry_verdict = needs_reinforcement_milestone`、`reinforcement_milestone_recommendation.needed = true`、`reinforcement_milestone_recommendation.recommendation_status = recommended|required|pending_operator_review` 或 `reinforcement_milestone_recommendation.blocks_implementation_until_resolved = true`，必须建议 reinforcement documentation / project-understanding Milestone，并不得 create/upsert/activate implementation-oriented milestone，也不得把弱文档推断升格为当前 milestone truth。
   - `reinforcement_milestone_recommendation` 必须是结构化 handoff，至少包含 `needed`、`recommendation_status`、`recommendation_type`、`suggested_title` 或 `suggested_purpose`、`reason` 或 `recommendation_reason`、`temporary_understanding_ref`、`evidence_refs`、`confirmation_required` 与 `blocks_implementation_until_resolved`；缺失或 placeholder 的 recommendation 不能被当作 implementation clearance。
5. 解析输入来源：
   - 若来自 programmer：直接使用提供的 milestone 规格
   - 若来自 harness 推理：验证规格完整性（至少包含 title、purpose），缺失关键字段时标记为规格不完整并停止
   - 若两者同时存在：programmer 规格优先，harness 推理作为补充建议
6. 确定 milestone_id：
   - 若输入提供了 milestone_id：检查是否与已有 milestone 冲突
   - 若未提供：自动生成，格式 `MS-YYYYMMDD-NNN`（如 `MS-20260510-001`）
   - 若 milestone_id 已存在：进入 upsert 模式（latest-override）
7. 验证依赖合法性：
   - 若 `depends_on_milestones` 非空，逐一检查是否存在于 live milestone-backlog 或 milestone-history 中
   - 引用的 milestone 不存在时标记为 `unknown_dependency` 并停止
   - 检查是否存在循环依赖（遍历 depends_on 链）
8. 确定 priority：
   - 输入提供的 priority 直接使用
   - 未提供时自动分配：取当前 pipeline 中最大 priority + 1
9. 确定 `milestone_kind`：
   - 若输入来自 programmer 且提供了 `milestone_kind`：直接使用
   - 若输入来自 programmer 但未提供 `milestone_kind`：默认 `goal-driven`
   - 若输入来自 harness（work-collection 路径）：`milestone_kind = "work-collection"`
   - work-collection 路径的自动生成字段：
     - `title`：`工作集合 MS-YYYYMMDD-NNN`（按创建时间自动编号）
     - `purpose`：`"工作集合 {milestone_id}"`
     - `completion_signals`：从 worktrack_list 逐条自动生成（每条映射为一个 signal）
     - `acceptance_criteria`：空（不适用）
     - `priority`：最低（取当前 pipeline 最大 priority + 1，确保不阻塞 goal-driven milestone）
     - `created_by`：`harness`
10. 规范化完成判定字段：
   - goal-driven milestone：若输入未提供 `completion_threshold_pct`，默认写入 `100`
   - work-collection milestone：`completion_threshold_pct` 记为 `100` 但不参与完成判定；验收仍下沉到 worktrack gate
   - 若本轮修改了 `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct`，标记 `milestone_reevaluation_required = true`
11. 输出结构化 `milestone brief` 并等待 programmer 确认：
   - brief 至少包含：`milestone_id`、`title`、`purpose`、`milestone_kind`、`worktrack_list`、`completion_signals`、`acceptance_criteria`、`completion_threshold_pct`、`priority`、`depends_on_milestones`、`activation_intent`、`scope_boundary_note`
   - 若本轮将 create / upsert / activate 任一 milestone，必须在 `milestone_brief_confirmed == true` 前停止，不得提前写入或激活
   - 若调用方已携带明确 programmer 确认记录，可直接继续；否则返回 brief 并等待确认
12. 追加 worktrack 时的信号覆盖判定（仅当向已有 goal-driven milestone 追加 worktrack 时执行）：
   a. 读取已有 milestone 的 `completion_signals` 和 `acceptance_criteria`
   b. 对每个新 worktrack，AI 辅助判定其验收是否被已有 signals 覆盖
   c. 输出 `coverage_verdict` ∈ {`fully_covered`, `partially_covered`, `not_covered`}
   d. 分支处理：
      - `fully_covered`：append + programmer 确认。"新 worktrack [X] 的验收已被已有 signals 覆盖，确认追加？"。标记 `signals_coverage_reviewed = true`
        追加完成后，该 worktrack 作为当前 milestone 中一个独立执行单元推进，建立自己的 branch、contract、queue、evidence、closeout 和 repo-refresh 追踪。
      - `partially_covered`：提示补充 signals → programmer 确认 → append。建议追加 signal 的自动推导内容。programmer 确认后更新 signals，并设置 `milestone_reevaluation_required = true`
        追加完成后，该 worktrack 同样以独立执行单元形式推进，并在新的 milestone 定义下形成清晰的单项追踪。
      - `not_covered`：拒绝归入。"新 worktrack [X] 与当前 milestone 的 purpose 不匹配。建议：创建新 milestone、归入其他已存在 milestone，或归入 work-collection milestone"
   e. 关键设计原则：不静默写入。AI 判断是提示，决策权在 programmer
   f. 稳定性规则：
      - 仅追加 worktrack 且 programmer 已确认其归属当前 milestone，同时 `coverage_verdict == fully_covered` 且未修改 `completion_signals` / `acceptance_criteria` / `completion_threshold_pct` 时，`milestone_reevaluation_required = false`；该 worktrack 直接进入当前 milestone 的独立执行序列
      - 若 append 导致上述任一字段修改，必须重新评估 milestone；不得沿用旧的 milestone 完成结论
      - `not_covered` 不得通过“先追加再观察”静默扩大范围，应直接建议其他 milestone 路径
13. 确定激活状态：
   - work-collection milestone 创建后直接激活（`status = "active"`）
   - goal-driven：若当前无 active milestone 且 `depends_on_milestones` 全部满足（所有前置为 `completed` 或 `superseded`）：设置为 `active`
   - 若 `activation_rules` 非空且条件满足：设置为 `active`
   - 否则：设置为 `planned`
   - 任一 milestone 的 `active` 判定都要求 `milestone_brief_confirmed == true`
   - 同一时刻仅允许一个 `active`：若设置当前 milestone 为 active 且已有 active milestone，先处理旧 active 的过渡（保持原状，标记冲突由 harness-skill 处理）
14. 创建或更新 milestone artifact：
   - 写入 `.servo/milestone/{milestone_id}.md`
   - 使用 milestone 模板字段结构（milestone_id、title、purpose、status、worktrack_list、completion_signals、acceptance_criteria、completion_threshold_pct、progress_counter、aggregated_evidence、release_version_consideration、developer_decision_boundary、depends_on_milestones、priority、activation_rules、created_by、updated、milestone_kind）
   - upsert 时保留已有字段，仅更新变化字段
15. 写入或更新 live milestone-backlog：
   - 按 milestone_id upsert 到 `.servo/repo/milestone-backlog.md`
   - 若 backlog 文件不存在则创建
   - 条目包含：milestone_id、title、purpose、status、priority、depends_on_milestones、worktrack_list、created_by、created_at、updated、updated_by、activation_rules、milestone_kind
16. 更新 control-state（若激活状态变化）：
   - 若新 milestone 被设为 active：更新 `active_milestone` 和 `milestone_status`
   - 若仅新增 planned milestone：不改变 `active_milestone`，仅更新 `milestone_pipeline_summary`
17. 产出一份结构化的 Milestone 初始化结果。
18. 如果没有命中正式停止条件，允许监督器直接进入下一个合法判定。

## 正式停止条件

至少在以下任一条件成立时停止并返回控制权：

- milestone_id 已存在且 programmer 未授权 upsert（在交互模式下需 programmer 确认）
- `depends_on_milestones` 引用了不存在的 milestone
- 检测到循环依赖
- 输入规格缺少 title 或 purpose 等关键字段且无法自动补全
- 需要创建、upsert 或激活 milestone，但 `milestone_brief_confirmed != true`
- 命中 pre-milestone intake 触发条件，但 `pre_milestone_intake_review` 缺失、未 ready 或未获 programmer confirmation
- 命中 complex-project trigger，但 `complex_project_entry_gate` 缺失、字段不全、`entry_verdict = blocked`，或 `milestone_blocking_decision` 阻止 create / upsert / activate
- 当前已有 active milestone 且 programmer 未明确指示替换
- milestone-backlog 损坏、不可读或不可解析（同上位 milestone-status-skill 的停止条件）
- 写入 `.servo/milestone/` 或 `.servo/repo/milestone-backlog.md` 失败

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 同一时刻仅允许一个 active milestone：设为 active 前必须检查 pipeline 状态
- latest-override 以 `updated` 时间戳为准；同时间戳 programmer 优先
- 不得静默覆盖 programmer 创建的 milestone；upsert 时需标记 `override_source` 和 `override_reason`
- goal-driven milestone 的 `completion_threshold_pct` 默认值为 `100`；调用方未显式提供时必须写出该默认语义，不得隐式使用其他阈值
- milestone_id 格式不做强制约束，但建议使用 `MS-YYYYMMDD-NNN` 保持可读性
- 循环依赖检测必须遍历完整 depends_on 链，不得仅检查直接依赖
- 仅当上游调用方（harness-skill 或 repo-whats-next-skill）明确授权时，才可变更 active milestone
- `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct` 任一修改都必须触发 milestone 重新评估标记
- append worktrack 只有在 programmer 确认其归属当前 milestone，且 `coverage_verdict` 不为 `not_covered` 时才可继续；否则必须建议其他 milestone 路径，避免静默 scope creep
- 在 create / upsert / activate 之前必须先输出结构化 `milestone brief` 并等待 programmer 确认；brief 不是可选摘要，而是激活前约束边界
- 高风险或模糊 milestone 在 create / upsert / activate 前必须先通过 `pre-milestone-intake-skill` 的 `pre_milestone_intake_review`；薄确认不得替代 intake review
- 复杂项目、弱文档或高风险 milestone 在 create / upsert / activate 前必须先通过 `complex_project_entry_gate`；该 gate 是 Milestone-side blocking gate, not fixed heavy mode。
- scanner output is evidence, not verdict；`scanner_evidence_ref` 与 `complexity_signals` 只能作为判定依据，不得替代 programmer confirmation 或 safety policy。
- `operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 和 `reinforcement_milestone_recommendation` 缺失时，必须 blocked。
- 空白、placeholder、pending 或 incomplete `complex_project_entry_gate` 与 missing gate 等价，必须 blocked；消费者不得把 unresolved gate 当成 `clear` 或 `not_applicable`。
- Weak-doc reinforcement routing 是 Milestone 创建/激活前的安全路由：`needed = true`、`recommendation_status = recommended|required|pending_operator_review` 或 `blocks_implementation_until_resolved = true` 时，默认 create / upsert / activate 的目标应改为 reinforcement documentation / project-understanding Milestone，不能继续实现型 Milestone；`needed = false` 且 `recommendation_status = not_needed` 不应阻断低风险 `clear` / `not_applicable` gate。
- Temporary understanding 是 runtime evidence, not Goal Charter truth；未经 programmer confirmation 或 verified evidence，本技能不得把其中 inferred facts 写入 milestone purpose、completion_signals、acceptance_criteria 或长期 docs truth。
- `init-milestone-skill` 只消费并验证 `pre_milestone_intake_review`；不得在本技能中生成 intake 问题、补写未确认事实或把 `inferred_assumptions` 升格为 programmer-confirmed truth。
- `intake_status = ready`、`intake_status = skipped`、`intake_status = questions_required`、`intake_status = blocked` 与 intake missing 必须有不同的 operator-facing 路由；把 skipped/questions_required/blocked/missing 归并为 ready 的行为必须返回 blocked。
- `questions_required` 必须保留 continuous intake metadata：`answered_questions`、`unresolved_questions`、`continuation_state`、`continuation_reason`、`next_required_question`、`next_question_blocks_ready` 和 one-question-at-a-time 语义。下游返回 blocked 时不得丢弃这些字段或把它们解释为 approval。
- 本技能不创建 worktrack、不触发 worktrack 初始化、不修改 version/release 状态

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 Milestone 初始化结果：

- `初始化决策`
- `Milestone 基本信息`
- `Pipeline 上下文`
- `依赖验证`
- `激活判定`
- `Artifact 写入`
- `Backlog 写入`
- `Control State 更新`
- `交接给 Harness`

结果中至少应包含以下字段或等价表达：

- `milestone_id`
- `milestone_title`
- `milestone_kind`：goal-driven / work-collection
- `completion_threshold_pct`
- `milestone_status`：planned / active
- `init_action`：created / upserted
- `priority`
- `pipeline_position`：当前在 pipeline 中的位置
- `depends_on_validation`：依赖检查结果
- `activation_decision`：为何设置为 active/planned
- `previous_active_milestone`：被替换的旧 active milestone（如有）
- `artifact_path`：写入的 milestone artifact 路径
- `backlog_updated`：boolean
- `control_state_updated`：boolean
- `override_source`：programmer / harness / none
- `milestone_brief`：object
- `milestone_brief_confirmed`：boolean
- `pre_milestone_intake_review`：object / N/A
- `pre_milestone_intake_required`：boolean
- `pre_milestone_intake_status`：ready / questions_required / blocked / skipped / N/A
- `complex_project_entry_gate`：object / N/A
- `scanner_evidence_ref`：string / N/A
- `complexity_signals`：array / N/A
- `operator_safety_policy`：object / N/A
- `dialog_review_questions`：array / N/A
- `milestone_blocking_decision`：array / N/A
- `reinforcement_milestone_recommendation`：object / N/A
- `signals_coverage_reviewed`：boolean — 信号覆盖判定是否已完成 programmer 确认（仅追加 worktrack 时适用）
- `coverage_verdict`：fully_covered / partially_covered / not_covered / N/A（仅追加 worktrack 时适用）
- `milestone_reevaluation_required`：boolean
- `milestone_reevaluation_reason`：string / array
- `can_proceed`：boolean
- `proceed_blockers`：阻止推进的因素列表
- `recommendations`：对 RepoScope.Decide 的建议

## 资源

使用当前 live milestone-backlog（`.servo/repo/milestone-backlog.md`）、milestone-history（`.servo/repo/milestone-history.md`，若存在）、control-state（`.servo/control-state.md`）、milestone 模板（`.servo/milestone/milestone-template.md`）作为主要输入。当 milestone 规格来自 harness 推理时，还需读取 Goal Charter（`.servo/goal-charter.md`）和 repo snapshot（`.servo/repo/snapshot-status.md`）以验证推理依据。

结果应保持聚焦于 Milestone 的初始化动作，而不是扩张成 pipeline 分析或 worktrack 规划。输出应可直接作为 `RepoScope.Decide` 和 `harness-skill` 的 pipeline 状态输入。
