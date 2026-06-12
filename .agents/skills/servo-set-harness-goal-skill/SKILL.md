---
name: set-harness-goal-skill
description: 当 Harness 系统尚未初始化，或 `.servo/goal-charter.md` 不存在，需要将用户的自然语言需求转化为结构化的 Harness 控制面组件时，使用这个技能。
---

# 设置 Harness 目标技能

## 概览

本技能实现 `RepoScope.SetGoal` 状态转移算子，对应 Harness 控制回路中的**参考信号初始化**阶段。

控制系统的参考信号（Goal）必须在闭环运行前被显式设定。如果参考信号缺失或含糊，控制器就无法计算误差，整个控制回路将失去方向。本技能负责在系统"上电"时，将用户的自然语言需求转化为结构化的 Harness 系统组件，为后续控制回路提供明确的参考基准。

当 `.servo/` 目录尚未建立，或 `goal-charter.md` 不存在，或 Harness 被明确要求初始化一个新目标时，使用这个技能。

本技能支持两种初始化模式：

- `new-goal-initialization`：用户给出目标，从空白或未初始化 repo 建立 `.servo/` 控制面
- `existing-code-adoption`：目标 repo 已有代码、文档或治理线索，先采集只读事实输入，再让用户确认长期目标

## 何时使用

- `.servo/` 目录不存在或为空
- `goal-charter.md` 不存在
- 用户明确要求"设定新目标"或"初始化 Harness"
- 用户要求把既有代码库接入 Harness，或要求 adoption / onboarding 一个 existing code project
- 当前 repo 没有活跃的 Harness 控制面

**不**使用的情况：
- `goal-charter.md` 已存在且用户要求修改它 → 路由到 `repo-change-goal-skill`
- 已有活跃 worktrack 且需要判断下一步 → 路由到 `repo-status-skill` + `repo-whats-next-skill`
- 只需要刷新 repo 快照 → 路由到 `repo-refresh-skill`

## 工作流

1. **检查现有状态**
   - 检查 `.servo/goal-charter.md` 是否存在
   - 如果存在 → 停止并路由到 `repo-change-goal-skill`
   - 如果不存在 → 继续

2. **选择初始化模式**
   - 如果用户主要提供目标描述，进入 `new-goal-initialization`
   - 如果目标 repo 已有代码、文档、配置或治理规则，且用户要求 Harness 接管/接入这个 existing code project，进入 `existing-code-adoption`
   - 模式不明确时，先向用户确认；goal charter 的内容只能来自用户明示确认；把既有实现自动解释成用户目标的行为必须返回 blocked 并显式暴露待确认问题

3. **分析用户需求**
   - 读取用户提供的自然语言需求描述
   - 识别核心目标、范围边界、技术约束、成功标准
   - 识别可分解的子系统或阶段（供后续 worktrack 拆分参考）
   - **识别预期的工程节点类型**：分析需求中隐含的功能开发、重构、调研、修复等工程性质
   - **为每个节点类型定义基线策略**：commit 形式、merge 要求、gate 标准、中断处理策略
   - 将工程节点类型填入 `Engineering Node Map`

4. **Existing Code Project Adoption 事实采集（仅该模式）**
   - 读取目标 repo 中与初始化有关的现有代码、文档、配置、测试、脚本和治理说明
   - 生成 `.servo/repo/discovery-input.md`
   - `discovery-input.md` 只记录只读事实输入、候选目标信号、风险、不确定点和待确认问题
   - `discovery-input.md` 的内容仅限只读事实输入与候选信号；把 `discovery-input.md` 写成 goal truth 或把现有实现倒推成用户已批准的长期目标的行为必须返回 blocked
   - 当 repo 文档缺失、过期、互相矛盾或不足以确认长期目的时，同时生成 `.servo/repo/temporary-understanding.md`；使用 deploy helper 时需显式传入 `--weak-doc-onboarding`，普通 `existing-code-adoption` 不应自动生成该 artifact
   - `temporary-understanding.md` 必须显式区分 `lightweight` 与 `full` 两种理解模式：`lightweight` 是低 token、快速定向、只支撑窄小 safe first slice；`full` 是更深的只读发现，token 和时间成本更高，必要时应建议单独 discovery milestone 或 worktrack
   - `temporary-understanding.md` / `temporary_understanding` 必须包含 `observed_facts`、`inferred_purpose`、`operational_purpose`、`known_risks`、`unknowns`、`confirmation_questions`、`programmer_decisions_required`、`promotion_plan`、`truth_boundary`、`token_budget_note` 和 mode selection
   - `temporary-understanding.md` 是 runtime evidence, not Goal Charter truth；未经 programmer confirmation 或 verified evidence 的 `inferred_purpose`、owner boundary、maintenance rule 和 acceptance rule 不得写入 `goal-charter.md`、docs truth layer 或 repo snapshot
   - 当 weak-doc、large repo、多服务、迁移、部署、数据、安全、破坏性操作或 authority boundary 信号影响后续 Milestone 入口时，生成或引用 `complex_project_entry_gate`
   - repo-init trigger 条件包括 weak docs、large repo、多服务、多 package manager、compose / docker / CI / deploy signal、migration / data risk、secret-like path、破坏性操作或 ownership / authority boundary 不清；这些信号应进入 `.servo/repo/complex-project-entry-gate.md` 或结构化 handoff，而不是直接进入 Goal Charter truth
   - `complex_project_entry_gate` 是 Milestone-side blocking gate, not fixed heavy mode；小型低风险初始化可记录 `entry_verdict = not_applicable`
   - gate 必须记录 `scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 和结构化 `reinforcement_milestone_recommendation`
   - Worktrack execution modes `normal`、`autoreview`、`yolo` 是 user-owned safety policy，不替代 Milestone-side blocker
   - 生成的 `operator_safety_policy` 默认只能写 `pending_programmer_confirmation`，不得默认授权 `normal`、`autoreview` 或 `yolo`
   - 未确认的 `complex_project_entry_gate` 默认必须 `entry_verdict = blocked` 且 `milestone_blocking_decision = block_create, block_upsert, block_activate, block_derive_worktrack`
   - unresolved gate blocking default: missing, blank, placeholder, pending, or incomplete gate 不能解释为 `clear` 或 `not_applicable`
   - scanner output is evidence, not verdict；scanner 阈值只能作为 LLM 判定依据，不能单独写成 Goal Charter truth
   - 生成的 scanner command 必须引用随 skill payload 分发的 `scripts/complexity_signal_scanner.py`；Agents backend 路径为 `.agents/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py`，Claude backend 路径为 `.claude/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py`
   - 后续 `goal-charter.md` 可以引用 discovery 中的候选目标信号，但必须经用户确认
   - 后续 `repo/snapshot-status.md` 可以吸收 discovery 中的状态线索，但应按初始化时的当前状态重写
   - 后续 `control-state.md` 只能把 discovery / temporary understanding 作为 linked evidence / note，不能把其中字段提升为控制指令

5. **弱文档临时理解模式选择（仅 weak-doc adoption / onboarding）**
   - 默认先选择 `lightweight`，仅做足以安全初始化和表达首个窄小 slice 的低 token 发现
   - 当长期目的、核心目录、测试权威、高风险边界或 owner boundary 不清楚且会影响当前目标时，选择 `full`
   - 如果 `full` 超出当前轮次 token / 时间预算，返回 handback 或建议新增 discovery milestone / worktrack，不把未确认推断伪装成长期目标
   - 输出时展示 mode、token-cost tradeoff、哪些结论只是 inference、哪些问题需要 programmer decision

6. **生成 `goal-charter.md`**
   - 将分析结果填入标准 `Goal Charter` 格式
   - 包含：Project Vision、Core Product Goals、Technical Direction、Engineering Node Map、Success Criteria、System Invariants
   - **不**在 goal charter 中指定具体的 worktrack 拆分方式；worktrack 拆分属于 `init-worktrack-skill` 的职责

7. **生成 `control-state.md`**
   - 设置初始控制面状态：`repo_scope: active`、`worktrack_scope: closed`
   - 询问并写入用户可定义 Servo 控制变量：
     - `continuous_progression_permission`
     - `per_milestone_automatic_worktrack_budget`
     - `default_servo_work_branch`
     - `protected_branch_policy`
     - `branch_mutation_policy`
   - 不询问 Servo 自动维护的 runtime facts，并在 `auto_maintained_runtime_facts_not_asked` 中保留禁止提问清单：`active_milestone`、`active_worktrack`、`observed_git_hash`、`progress_counters`、`runtime_dispatch_profile`、`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint`、`milestone_pipeline_summary`
   - 设置合理的默认 `Continuation Authority`：
     - `post_contract_autonomy: delegated-minimal`
     - `autonomy_scope: current-goal-only`
     - `max_auto_new_worktracks: 1`
     - `stop_after_autonomous_slice: yes`
     - `subagent_dispatch_mode: auto`
     - `subagent_dispatch_mode_override_scope: worktrack-contract-primary`
     - `subagent_default_model:` 留空，除非运行环境或用户明确给出默认模型
   - 设置 `Handback Guard` 初始值：`handoff_state: none`

8. **生成 `repo/analysis.md`**
   - 基于目标与当前 repo 状态生成初始 RepoScope 分析骨架
   - 只记录事实 / 推断 / 未知项、主要矛盾、优先级和路由投影
   - `repo/analysis.md` 的内容仅限事实 / 推断 / 未知项、主要矛盾、优先级和路由投影；把 `repo/analysis.md` 写成 goal truth 或 worktrack queue 的行为必须返回 blocked

9. **生成 `repo/snapshot-status.md`**
   - 基于当前 repo 实际状态生成初始快照
   - 如果 repo 为空，如实记录"空仓库起步"
   - 在 `existing-code-adoption` 模式下，可以从 `.servo/repo/discovery-input.md` 提取已确认的状态线索，但 snapshot 是初始化后的慢变量状态，不是 discovery 的原文复制

10. **确认目录结构并复制模板资产**
   - 优先使用本技能自带的 `scripts/deploy_servo.js` 生成标准 Harness `.servo/` 基线；它会从本技能的 `assets/` 目录渲染/复制所需文件，确保目录结构完整：
     ```
     .servo/
     ├── control-state.md           ← 基于 assets/control-state.md 模板填充
     ├── goal-charter.md            ← 基于 assets/goal-charter.md 模板填充
     ├── repo/
     │   ├── discovery-input.md     ← existing-code-adoption 模式下基于 assets/repo/discovery-input.md 模板填充
     │   ├── complex-project-entry-gate.md ← complex-project trigger 或 weak-doc onboarding 场景下基于 assets/repo/complex-project-entry-gate.md 模板填充
     │   ├── temporary-understanding.md ← weak-doc adoption / onboarding 场景下基于 assets/repo/temporary-understanding.md 模板填充
     │   ├── analysis.md            ← 基于 assets/repo/analysis.md 模板填充
     │   └── snapshot-status.md     ← 基于 assets/repo/snapshot-status.md 模板填充
     ├── template/
     │   ├── README.md              ← 从 assets/template/README.md 复制
     │   └── goal-charter.template.md  ← 从 assets/template/goal-charter.template.md 复制
     └── worktrack/
         ├── README.md              ← 从 assets/worktrack/README.md 复制
         ├── contract.md            ← 从 assets/worktrack/contract.md 复制
         ├── gate-evidence.md       ← 从 assets/worktrack/gate-evidence.md 复制
         └── plan-task-queue.md     ← 从 assets/worktrack/plan-task-queue.md 复制
     ```
   - `assets/` 目录遵循 Codex Skills 标准，存放本技能所需的模板、资源和参考文档
   - `scripts/deploy_servo.js` 是本技能的标准 `.servo` deploy helper；它接收 `--deploy-path <目标 repo / worktree 根>`，并固定在 `<deploy-path>/.servo/` 下生成模板。在 canonical source 与 deployed target 中都应可直接读取本技能自带的 `assets/`
   - 如果目标 repo 需要给 Claude Code 暴露同一个初始化技能，可在生成时追加 `--install-claude-skill`，将本技能包复制到 `<deploy-path>/.claude/skills/servo-set-harness-goal-skill/`
   - 也可以单独运行 `node scripts/deploy_servo.js install-claude-skill --deploy-path <目标 repo / worktree 根>`；默认不覆盖已有 `.claude` skill 文件，只有显式传入 `--force` 才会覆盖本技能包内的对应文件
   - Claude helper 允许 `--claude-root` 指向 operator 管理的 symlink / mount 层；但拒绝 `set-harness-goal-skill/` 目标目录本身是 symlink，也拒绝该 skill 目录内部已有 symlink，保持 copy install 不依赖外部源码路径
   - 如果目标 skill 目录本身不是 symlink，但经允许的 root symlink / mount 解析后就是当前运行的技能包，安装视为已完成并 no-op
   - 复制时只复制模板骨架；内容字段（如 Project Vision、autonomy 参数等）由第 3~5 步的分析结果填充
   - 不覆盖已存在的文件；如果 `.servo/` 中已有同名文件，保留现有文件并报告冲突

11. **用户确认**
   - 向用户展示生成的 `Goal Charter` 摘要
   - 如果是 `existing-code-adoption`，同时展示 `Discovery Input` 摘要、Temporary Understanding 摘要、待确认问题，以及哪些 discovery / temporary-understanding 信号被纳入 goal 草案
   - 等待用户确认或修改
   - **在用户确认前不写入文件**

12. **写入并返回**
   - 用户确认后执行写入操作：
     - 将填充好的 `goal-charter.md`、`control-state.md`、`repo/analysis.md`、`repo/snapshot-status.md` 写入 `.servo/`
     - 在 `existing-code-adoption` 模式下，将填充好的 `repo/discovery-input.md` 写入 `.servo/repo/`
     - 在 weak-doc adoption / onboarding 场景下，将填充好的 `repo/temporary-understanding.md` 写入 `.servo/repo/`
     - 将 `assets/` 中的模板文件复制到 `.servo/` 的对应位置（template/ 和 worktrack/ 子目录）
   - 返回 `Harness 初始化结果`，包含：
     - 生成的组件清单
     - 建议的下一动作（进入 `RepoScope.Observe`）
     - 需要审批：`false`（如果用户已确认）

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

本技能特有约束：

- 本技能是**系统初始化**层；只在 `.servo/` 不存在或 `goal-charter.md` 缺失时运行。
- 唯一合法行为是仅在 `goal-charter.md` 不存在时创建新目标章程；当 `goal-charter.md` 已存在时，覆盖行为必须返回 blocked，且必须路由到 `repo-change-goal-skill`。
- 唯一合法行为是展示生成的 goal charter 摘要并等待用户确认后才写入；代替用户设定目标的行为必须返回 blocked。
- goal charter 的内容仅限目标定义与节点类型约束；指定具体 worktrack 拆分方式的行为必须返回 blocked 并路由到 `init-worktrack-skill`。
- **但必须在 goal charter 中定义 Engineering Node Map，为 worktrack 初始化提供类型化约束。**
- 唯一合法行为是仅基于用户明确说明的需求设定目标；猜测用户未明确说明的需求的行为必须返回 blocked；有歧义时必须显式暴露并请求用户确认。
- Existing Code Project Adoption 中，`discovery-input.md` 只能保存只读事实输入和候选信号；唯一合法行为是经用户确认后才将 discovery 信号纳入 `goal-charter.md`。
- Weak-doc adoption / onboarding 中，`temporary-understanding.md` 只能保存 temporary-inferred runtime evidence；唯一合法行为是经 programmer confirmation 或 verified evidence 后才将其中信号提升到 `goal-charter.md`、`repo/snapshot-status.md` 或 docs truth layer。
- Weak-doc adoption / onboarding 必须记录 `lightweight` / `full` mode selection 与 token-cost tradeoff；当 full discovery 明显超出当前预算时，必须 handback 或建议新增 discovery milestone / worktrack，而不是把薄弱理解伪装成已确认 goal truth。
- Weak-doc adoption / onboarding 命中 complex-project trigger 时，必须记录 `complex_project_entry_gate`、`scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 与结构化 `reinforcement_milestone_recommendation`；弱文档命中且安全理解不足时，建议 reinforcement documentation / project-understanding Milestone。
- 结构化 `reinforcement_milestone_recommendation` 至少包含 `needed`、`recommendation_status`、`recommendation_type`、`suggested_title` 或 `suggested_purpose`、`reason` 或 `recommendation_reason`、`temporary_understanding_ref`、`evidence_refs`、`confirmation_required` 与 `blocks_implementation_until_resolved`。`recommendation_status` 可为 `not_needed`、`recommended`、`required` 或 `pending_operator_review`。`needed = true` 或 `blocks_implementation_until_resolved = true` 时默认保持 `entry_verdict: blocked` / `needs_reinforcement_milestone` 和 `milestone_blocking_decision: block_create, block_upsert, block_activate, block_derive_worktrack`。
- `complex_project_entry_gate` 是 Milestone-side blocking gate, not fixed heavy mode；scanner output is evidence, not verdict。
- `complex_project_entry_gate` 的生成样例不得预授权高风险命令模式；未确认样例默认阻断 Worktrack derivation，直到 programmer confirmation 或 reinforcement evidence 写入。
- 设置默认 autonomy 参数时，优先选择"小步推进、逐层验证"的保守策略；`max_auto_new_worktracks` 默认值必须与 `Harness Control State` artifact 和 control-state 模板保持一致。
- 初始化问题必须只覆盖用户可定义 Servo 控制变量：continuous progression permission、per-Milestone automatic Worktrack budget、default Servo work branch、protected branch policy 和 branch mutation policy。不得把 `active_milestone`、`active_worktrack`、`observed_git_hash`、`progress_counters`、`runtime_dispatch_profile`、`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint` 或 `milestone_pipeline_summary` 作为用户问题；这些 runtime facts 由 Harness 控制回路自动维护。
- 用户在初始化或单轮执行中授予的一次性权限只能写入 evidence / handoff / Autonomy Ledger，不得伪装成长期默认。只有用户明确表达持久偏好时，才可更新 `User-Defined Servo Controls` 或长期 `Continuation Authority` 字段。
- 设置默认 SubAgent 分派参数时，必须把是否使用 SubAgent 表达为可开关字段：`subagent_dispatch_mode: auto | delegated | current-carrier`，并写入 `subagent_dispatch_mode_override_scope: worktrack-contract-primary`，使 worktrack 级 `runtime_dispatch_mode` 在默认 scaffold 中可生效；只有操作者显式改为 `global-override` 时，control-state 才压过 worktrack 合同。`auto` 是保守默认值，表示按 Dispatch Decision Policy 选择 SubAgent、专用 skill、generic worker 或 current-carrier；运行时在无安全分派壳层、权限边界阻断或 `dispatch package unsafe` 时显式记录 `runtime fallback`。
- **不依赖外部 scaffold 脚本**；所有模板来自本技能自带的 `assets/` 目录，遵循 Codex Skills 标准。
- 如果需要 repo-local operator 帮助脚本，唯一合法来源是本技能自带的 `scripts/deploy_servo.js`。
- 写入文件后，控制权返回 Harness；由 Harness 根据新的 control state 决定下一步。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `Harness 初始化结果`：

- `初始化决策`
- `需求摘要`
- `生成的组件清单`
- `Goal Charter 摘要`
- `默认控制策略`
- `建议下一动作`
- `返回 Harness`

结果中至少应包含以下字段或等价表达：

- `初始化状态`
- `goal_charter_created`
- `control_state_created`
- `repo_snapshot_created`
- `project_vision`
- `core_product_goals`
- `engineering_node_map`
- `node_type_registry`
- `this_goal_node_types`
- `default_baseline_policy`
- `success_criteria`
- `system_invariants`
- `post_contract_autonomy`
- `max_auto_new_worktracks`
- `stop_after_autonomous_slice`
- `subagent_dispatch_mode`
- `runtime_dispatch_mode`
- `建议代码仓库动作`
- `建议下一路由`
- `建议下一范围`
- `可继续`
- `需要审批`
- `如何审查`

## 模板资产

本技能遵循 Codex Skills 标准，在 `assets/` 目录下携带完整的 Harness 初始化模板资产：

| 资产路径 | 用途 | 复制目标 |
|---------|------|---------|
| `assets/control-state.md` | 控制状态模板骨架 | `.servo/control-state.md`（填充后写入） |
| `assets/goal-charter.md` | 目标章程模板骨架 | `.servo/goal-charter.md`（填充后写入） |
| `assets/repo/discovery-input.md` | Existing Code Project Adoption 只读事实输入模板骨架 | `.servo/repo/discovery-input.md`（仅 adoption 模式填充后写入） |
| `assets/repo/temporary-understanding.md` | 弱文档 adoption / onboarding 临时理解模板骨架，承接 lightweight / full mode、token-cost tradeoff、truth boundary 与 promotion plan | `.servo/repo/temporary-understanding.md`（weak-doc adoption / onboarding 场景填充后写入） |
| `assets/repo/complex-project-entry-gate.md` | Repo init / Existing Code Project Adoption 的 complex-project trigger 模板骨架，承接 `complex_project_entry_gate`、scanner evidence、operator safety policy、dialog review 和 blocking decision | `.servo/repo/complex-project-entry-gate.md`（`--complex-project-entry-gate` 或 `--weak-doc-onboarding` 场景填充后写入） |
| `assets/repo/analysis.md` | RepoScope 阶段性分析与优先级判断模板骨架 | `.servo/repo/analysis.md`（填充后写入） |
| `assets/repo/snapshot-status.md` | 仓库快照模板骨架 | `.servo/repo/snapshot-status.md`（填充后写入） |
| `assets/template/README.md` | 模板目录说明 | `.servo/template/README.md`（直接复制） |
| `assets/template/goal-charter.template.md` | 目标章程复用模板 | `.servo/template/goal-charter.template.md`（直接复制） |
| `assets/worktrack/README.md` | 工作追踪目录说明 | `.servo/worktrack/README.md`（直接复制） |
| `assets/worktrack/contract.md` | 工作追踪契约模板骨架 | `.servo/worktrack/contract.md`（直接复制） |
| `assets/worktrack/gate-evidence.md` | 关卡证据模板骨架 | `.servo/worktrack/gate-evidence.md`（直接复制） |
| `assets/worktrack/plan-task-queue.md` | 计划任务队列模板骨架 | `.servo/worktrack/plan-task-queue.md`（直接复制） |
| `scripts/deploy_servo.js` | `.servo` 初始化 deploy helper | 由操作者或测试直接运行，传入 `--deploy-path <repo/worktree 根>`，脚本在 `<deploy-path>/.servo/` 下生成/复制上述资产；可选安装本技能到 `<deploy-path>/.claude/skills/servo-set-harness-goal-skill/` |

这些资产在 deploy 阶段随本技能一并安装到宿主运行环境。执行时，本技能从自身的 `assets/` 目录读取模板；如需 repo-local operator 工具面，则直接运行本技能自带的 `scripts/deploy_servo.js`，把目标 worktree / repo 根通过 `--deploy-path` 传入。若需要让 Claude Code 在目标 repo 内发现同一技能，可使用 `--install-claude-skill` 或 `install-claude-skill` 子命令；`--claude-root` 可覆盖 `.claude/skills` root，并允许该 root 是 symlink / mount，但目标 skill 目录及其内部不能是 symlink；如果目标目录经允许的 root symlink / mount 解析后就是当前运行的技能包，则安装 no-op。唯一合法的 scaffold 来源是本技能自带的 `scripts/deploy_servo.js` 和 `assets/` 目录；依赖外部 scaffold 脚本或独立的 `.servo` 模板源码根的行为必须返回 blocked。

最小用法：

```bash
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --owner servo-kernel
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --adoption-mode existing-code-adoption
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --adoption-mode existing-code-adoption --weak-doc-onboarding
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --adoption-mode existing-code-adoption --complex-project-entry-gate
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --install-claude-skill
node scripts/deploy_servo.js install-claude-skill --deploy-path "$DEPLOY_PATH"
node scripts/deploy_servo.js generate --help
```

## 资源

使用当前用户需求文本、当前 repo 实际状态（文件、分支、提交历史），以及本技能 `assets/` 目录下的标准模板格式作为参考。唯一合法的 scaffold 来源是本技能自带的 `scripts/deploy_servo.js`；依赖外部 scaffold 脚本的行为必须返回 blocked；需要 operator 辅助时直接使用本技能自带的 `scripts/deploy_servo.js`，把目标路径通过 `--deploy-path` 传入，由本技能生成符合 Harness 运行协议的标准组件。
