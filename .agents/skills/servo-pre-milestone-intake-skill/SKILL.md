---
name: pre-milestone-intake-skill
description: 当需要在创建、更新或激活 Milestone 前对用户需求做一轮限定范围核实、追问、挑战和推荐，并产出 pre_milestone_intake_review 时，使用这个技能。
---

# Pre-Milestone Intake Skill

## 概览

把这个技能作为 `RepoScope` 下的 Milestone 前置 intake / grill gate 使用。

本技能运行在 `init-milestone-skill` 之前。它接收 programmer 的自然语言需求、已有 repo truth、当前控制状态和最小代码仓库上下文，先把需求整理为可确认的 milestone brief 草案，再识别模糊点、风险点、范围扩张点和需要 programmer 决策的地方。它的输出是结构化 `pre_milestone_intake_review`，供 `init-milestone-skill` 消费；当目标 milestone 已创建或准备激活时，该 review 同时作为 Milestone Review Gate 的输入。

Continuous intake mode is allowed and expected when one assistant turn is not enough to resolve the entry review. In that mode the skill returns `intake_status = questions_required`, persists `continuation_state`, asks exactly one `next_required_question`, and waits for the programmer answer before producing the next review checkpoint. A questions-required checkpoint is not a pass; it is a continuation handoff.

本技能不创建 milestone，不写入 `.servo/milestone/`，不更新 milestone-backlog，不创建 worktrack，不修改代码，不替 programmer 确认业务目标。

当需要稳定输出格式时，使用 `templates/pre-milestone-intake-review.template.md`。模板是 before-start question contract 的执行载体，必须保留事实、推断、未知项、问题、推荐答案、取舍、范围边界、验收信号、确认状态和跳过风险记录的分区。

## 何时使用

以下情况应使用本技能：

- 新建 goal-driven milestone。
- 用户需求模糊，例如"优化一下"、"完善一下"、"重构一下"、"做一个方案"。
- 涉及 release、publish、migration、数据、权限、安全、兼容性或部署边界。
- 涉及多 repo、跨系统、跨团队或 integration acceptance。
- 涉及大型无文档或弱文档代码库。
- 涉及复杂项目入口判断，尤其是弱文档、多服务、多 repo、迁移、部署、数据、安全、权限、破坏性操作或外部契约边界。
- 涉及 Harness doctrine、artifact contract、canonical skill 或 workflow family 变更。
- `init-milestone-skill` 准备 create / upsert / activate，但 milestone brief 仍依赖未确认假设。

以下情况可轻量跳过，但必须记录跳过理由：

- 用户给出明确、低风险、单文件或单模块的小修复。
- 当前 active milestone 下执行已确认 worktrack。
- 纯只读检查或验证。
- 用户明确要求不追问并接受风险。

## 工作流

1. 确认这是一轮 Milestone 前置 intake，不是 milestone 初始化、worktrack 初始化或实现执行。
2. 读取当前需求、Goal Charter、Repo Snapshot、Control State、live milestone-backlog，以及回答当前问题所需的最小 repo context。
3. 将输入分为：
   - `observed_facts`：可从 repo 或已给输入直接证明的事实；
   - `inferred_assumptions`：模型推断但未确认的假设；
   - `unknowns`：影响 scope、risk 或 acceptance 的未知项；
   - `programmer_decisions_required`：必须由 programmer 决策的事项。
   能从 repo truth、current control state、milestone-backlog、worktrack-backlog、recent evidence 或明确用户输入中查到的事实，必须先作为 observed facts 收集；不得把这些可发现事实全部转嫁为 programmer 问题。
4. 生成 `request_summary` 和 `suggested_milestone_brief` 草案，至少包含 title、purpose、scope、non_goals、candidate worktracks、completion signals、acceptance criteria、risk flags。
   若输出多个 candidate milestone brief，必须先说明 `primary_contradiction`、`main_aspect_now` 和每个候选的 evidence / unknowns / programmer confirmation requirement；通常收敛到 1 到 3 个候选。
5. 执行 grill gate：
   - 默认优先提出 3 到 5 个最高杠杆问题；若进入 continuous intake mode，则本轮只提出一个最高杠杆 `next_required_question`；
   - 每个问题必须说明为什么要问，并写入 `why_it_matters`；
   - 每个问题必须给出 recommended answer；
   - 每个 recommended answer 必须说明取舍影响；
   - 能从 repo 查到的事实先查，不把可发现事实全部推给 programmer。
   - 若命中 complex-project trigger，生成或更新 `complex_project_entry_gate`；该 gate 是 Milestone-side blocking gate，不是固定 heavy mode。
   - complex gate 必须记录 `scanner_evidence_ref` 和 `complexity_signals`，但 scanner output is evidence, not verdict。
   - complex gate 必须记录 programmer-owned `operator_safety_policy` 和 `dialog_review_questions`，至少覆盖 docker/compose、database/migration、deploy/network、destructive cleanup、secrets、protected paths/branches，以及允许的 high-risk command modes。`normal`、`autoreview`、`yolo` 只是可由 programmer 选择的回答，不得作为生成默认授权。
6. 判定是否 ready：
   - 若关键 scope、non-goal、acceptance 或 risk boundary 缺失，`ready_for_init_milestone = false`；
   - 若 high-risk trigger 命中，必须存在 `open_questions` 的明确回答或 `intake_skipped = true` 的风险接受记录；
   - 若 `complex_project_entry_gate.entry_verdict` 为 `needs_reinforcement_milestone` 或 `blocked`，`ready_for_init_milestone = false`，并通过结构化 `reinforcement_milestone_recommendation` 建议 reinforcement documentation / project-understanding Milestone；
   - 若剩余未知项不影响安全初始化，可记录 residual risk 并设置 ready；
   - 若存在阻断性未知项但一次性追问会制造噪声，设置 `intake_status = questions_required`、`ready_for_init_milestone = false`、`continuation_state.continuation_required = true`，并只输出一个 `next_required_question`；
   - 若 programmer 明确接受剩余未知项作为 residual risk，必须在 `residual_risk_accepted` 和 `accepted_residual_risk` 中记录；只有这些风险不改变 scope、non-goals、acceptance 或 risk boundary 时才可进入 `effective_pass`；
   - 若 programmer 已确认必要问题，设置 `programmer_confirmed = true`。
7. 输出结构化 `pre_milestone_intake_review`。若该 review 要作为 Milestone Review Gate 的 pass，必须写出 `milestone_review_gate_handoff`，并区分 `effective_pass`、`questions_required`、`blocked`、`skipped`、`missing`、`stale` 与 `invalidated`。continuous intake mode 可以跨多个 assistant turns；每一轮必须写入 `answered_questions`、`unresolved_questions`、`continuation_reason`、`next_required_question` 和 `continuation_state`。
8. 停止并交给 `init-milestone-skill` 或返回 programmer；本技能不得自行写入/激活 milestone。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 不得创建、更新或激活 milestone。
- 不得创建 worktrack 或执行实现。
- 不得把 inferred assumptions 写成 programmer-confirmed truth。
- 不得一次性提出大量低价值问题；问题应限于本轮 highest leverage。continuous intake mode 下必须 one-question-at-a-time：`open_questions` 只能包含一个 blocking question，且必须同步填充 `next_required_question`。
- 每个 open question 必须携带 recommended answer 和 tradeoff。
- `questions_required` 必须携带 `continuation_state`、`continuation_reason`、`answered_questions`、`unresolved_questions`、`next_required_question` 和 `next_question_blocks_ready = true`；缺少这些字段不得交给下游消费。
- 当 high-risk trigger 命中且缺少 programmer confirmation 时，必须设置 `ready_for_init_milestone = false`。
- 若用户明确要求跳过 intake，应记录 `intake_skipped = true`、`skip_reason` 和 `accepted_risk`，不得假装已经完成 grill gate。
- `intake_status = ready` 只能在 `programmer_confirmed = true` 且 `ready_for_init_milestone = true` 时使用；跳过 intake 时只能使用 `intake_status = skipped`，不得同时标记为 ready。
- Milestone Review Gate 的有效 pass 只能来自 `intake_status = ready`、`programmer_confirmed = true`、`ready_for_init_milestone = true`、`intake_skipped = false` 且 `milestone_review_gate_handoff.review_status = effective_pass`。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全不得作为 review pass。
- `questions_required`、`blocked`、`skipped`、`missing`、`stale`、`invalidated`、`residual_risk_unaccepted` 或 field-incomplete continuation state 不得增加 `milestone_review_count`。
- 若 review 发现 `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 发生变化，必须在 `review_invalidated_by` 中记录，并把 `review_status` 设置为 `invalidated` 或要求 fresh checkpoint。
- `observed_facts`、`inferred_assumptions`、`unknowns` 和 `programmer_decisions_required` 必须分开写；未经 programmer 确认的推断不得进入长期 truth 或 milestone artifact 的确认字段。
- Candidate milestone brief 必须保持 recommendation / draft 身份。它可以帮助 programmer 决策，但在 programmer confirmation 和 `init-milestone-skill` 写入前，不得成为 live milestone truth、planned milestone、active milestone 或 Worktrack task queue。
- 命中 complex-project trigger 时，必须输出 `complex_project_entry_gate`、`scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 与 `reinforcement_milestone_recommendation`。
- 当 weak-doc 或 insufficient project understanding 是阻断因素时，`reinforcement_milestone_recommendation` 必须至少携带 `needed`、`recommendation_status`、`recommendation_type`、`suggested_title` 或 `suggested_purpose`、`reason` 或 `recommendation_reason`、`temporary_understanding_ref`、`evidence_refs`、`confirmation_required` 与 `blocks_implementation_until_resolved`；`recommendation_status` 可为 `not_needed`、`recommended`、`required` 或 `pending_operator_review`；`needed = true` 或 `blocks_implementation_until_resolved = true` 时不得派生 implementation-oriented Worktrack，`needed = false` 才能允许低风险 `clear` / `not_applicable` gate 继续。
- unresolved gate blocking default: missing, blank, placeholder, `pending_programmer_confirmation`, pending, or incomplete `complex_project_entry_gate` 不得被视为 clear 或 `not_applicable`；默认阻断 create/upsert/activate/derive-worktrack，直到 programmer confirmation 或 verified evidence 存在。
- scanner output is evidence, not verdict；不得把 scanner 阈值或启发式结果直接写成 `entry_verdict` 或 milestone truth。
- `complex_project_entry_gate` 是 Milestone-side blocking gate, not fixed heavy mode。小型低风险请求可以记录 `entry_verdict = not_applicable`，但不能因此跳过已命中的高风险安全策略必填项。
- temporary understanding 是 runtime evidence, not Goal Charter truth；未经 programmer confirmation 或 verified evidence，不得把 inferred purpose、owner boundary、maintenance rule 或 acceptance rule 升格为 milestone truth、Goal Charter truth 或 docs truth。
- `suggested_milestone_brief` 必须保持草案身份，直到 `init-milestone-skill` 消费已确认的 intake review 后再写入正式 milestone artifact。
- 本技能输出的 milestone brief 是草案；只有 `init-milestone-skill` 可以写入 artifact 和 backlog。

## 预期输出

使用本技能时，产出一份至少包含以下章节的 `pre_milestone_intake_review`：

- `Intake Status`
- `Request Summary`
- `Observed Facts`
- `Inferred Assumptions`
- `Unknowns`
- `Programmer Decisions Required`
- `Risk Flags`
- `Open Questions`
- `Recommended Answers`
- `Scope Boundary`
- `Non Goals`
- `out_of_scope`
- `Acceptance Signals`
- `Suggested Milestone Brief`
- `Confirmation State`
- `Handoff To Init Milestone`
- `Skip Record`

字段至少包含：

- `intake_status`: ready / questions_required / blocked / skipped
- `request_summary`
- `observed_facts`
- `inferred_assumptions`
- `unknowns`
- `programmer_decisions_required`
- `risk_flags`
- `open_questions`
- `answered_questions`
- `unresolved_questions`
- `continuation_state`
- `continuation_reason`
- `next_required_question`
- `next_question_blocks_ready`
- `recommended_answers`
- `scope_boundary`
- `non_goals`
- `acceptance_signals`
- `suggested_milestone_brief`
- `confirmation_required`
- `programmer_confirmed`
- `ready_for_init_milestone`
- `intake_skipped`
- `skip_reason`
- `accepted_risk`
- `residual_risk_accepted`
- `accepted_residual_risk`
- `handoff_to_init_milestone`
- `template_contract_ref`
- `complex_project_entry_gate`
- `scanner_evidence_ref`
- `complexity_signals`
- `operator_safety_policy`
- `dialog_review_questions`
- `milestone_blocking_decision`
- `reinforcement_milestone_recommendation`
- `milestone_review_gate_handoff`
- `milestone_review_count`
- `latest_review_status`
- `latest_review_checkpoint`
- `effective_review_pass`
- `review_invalidated_by`

## 资源

使用当前需求、`.servo/goal-charter.md`、`.servo/repo/snapshot-status.md`、`.servo/control-state.md`、`.servo/repo/milestone-backlog.md`，以及本轮核实所需的最小 repo context。对大型无文档 repo，运行时按 weak-doc / large-repo intake 规则处理：先收集只读事实，区分 observed facts 与 inferred assumptions，必要时建议 discovery / reinforcement milestone，不把未确认推断写入长期 truth。对多 repo 项目，运行时必须分别记录每个 repo 的目标、状态、边界、验证路径与是否允许 mutation；不得把一个 repo 的发现自动推广到另一个 repo。Source-side authoring traces: `docs/harness/workflow-families/large-undocumented-repo-onboarding.md`, `docs/harness/workflow-families/multi-repo-project-workflow.md`。
