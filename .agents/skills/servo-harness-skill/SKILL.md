---
name: harness-skill
description: 当需要运行 Harness 分层闭环控制系统时，使用这个技能。它是 Codex 中顶层监督控制器的入口，负责状态估计、算子选择、技能绑定、子代理分派、证据收集、裁决与状态更新，而不是直接执行编码。
---

# Harness 技能

## 一、本体定位

**Harness 是对 Repo 演进过程的分层闭环控制系统。**

它在 `Repo` 级维护长期基线与系统不变量，在 `Worktrack` 级约束局部状态转移，并通过 `Evidence + Gate` 决定状态是否允许推进为新的基线。

Harness 关注的不是"把任务做完"本身，而是：

- 给系统输入
- 观察系统输出
- 和目标状态对比
- 判断当前状态是否允许继续推进
- 在失败时阻断、恢复、重试、回滚或重新规划

### 它不是什么

- 不是直接执行编码的主体
- 不是已批准输入或工作追踪合同的替代物
- 不是某个 backend 的 repo-local runtime wrapper
- 不是把一组 skill 顺序串起来的 open-loop 流程图
- 不是可以在常规控制里随意改写目标的任务管理器

---

## 二、控制系统架构

Harness 的运行基于一条完整的控制回路：

```
状态估计 → 选择算子 → 绑定技能 → 打包任务/信息 → 分派子代理 → 收集证据 → 裁决 → 状态更新
    ↑                                                                            ↓
    └──────────────────────────── 反馈环 ────────────────────────────────────────┘
```

每个阶段的控制语义：

| 阶段 | Function 算子 | 职责 |
|------|--------------|------|
| **状态估计** | `Observe` | 通过传感器读取当前系统状态，与参考信号对比 |
| **选择算子** | `Decide` | 基于状态估计结果，选择合法的状态转移算子 |
| **绑定技能** | `Bind` | 将算子映射到具体的 Skill 实现 |
| **打包任务** | `Package` | 为 SubAgent 准备受约束的任务与信息包 |
| **分派子代理** | `Dispatch` | 将任务交给执行载体，而不是 Harness 自己执行 |
| **收集证据** | `Verify` | 通过多维度传感器收集证据，证明"当前状态是什么" |
| **裁决** | `Judge` | 通过 Gate 判断"当前状态是否允许推进" |
| **状态更新** | `Update` | 更新 Control State，闭合控制回路 |

**关键约束**：下游技能的轮次是本地控制步骤，不是隐式停止信号。Harness 应消费下游结构化输出持续推进，直到真正命中正式停止条件。

**执行载体选择**：当实现、审查或验证任务进入执行平面时，Harness 必须按 Dispatch Decision Policy 选择真实 `SubAgent`、专用 skill、通用执行载体、human executor 或明确的 current-carrier。`auto` 不表示"能委派就委派"；它表示根据任务耦合度、共享状态需求、并行价值、风险、权限边界和上下文预算选择载体。当前载体执行不是隐式失败，但必须显式记录 `carrier_decision`、`decision_inputs` 和回退原因。

**单入口分流**：`harness-skill` 是唯一闭环 supervisor。Operator-facing profile / mode 只能作为 `route hint`：根据 `user_input`、`repo_state`、`milestone_state`、`worktrack_state`、`risk_signals` 与 `approval_signals` 判断应进入 status-and-next、pre-milestone discussion、milestone-open discussion、worktrack execution、verify-and-close 或 release-sensitive 等 workflow path。Profile 不创建第二 controller、不创建第三 Scope、不拥有独立 Gate、不写长期 truth、不绕过 Worktrack Contract，也不得把 candidate milestone / candidate worktrack 解释成已批准执行范围。最终仍由 Harness 控制回路选择 Scope、Function、Skill / execution carrier，收集 Evidence，并执行 Gate。

**Operator mode matrix**：单入口的 operator mode matrix 是触发语义表，不是新状态机。它使用 hydrated control state 和 trigger signals 把输入投影到 status-and-next、pre-milestone discussion、milestone-open discussion、worktrack execution、verify-and-close 或 release-sensitive；每个 mode 只影响 route estimate 与 stop/approval semantics。candidate milestone、candidate worktrack、suggested task、profile 和 operator-facing mode 都属于 not approved scope，必须经过正式 artifact 与 programmer confirmation 后才能成为 live milestone、Worktrack Contract 或执行任务。多种 trigger signals 同时命中时，按更严格 authority boundary 选择：release-sensitive 优先于 verify-and-close，verify-and-close 优先于 worktrack execution，缺证据时 blocked / handback 优先于任何 mutating route。

---

## 三、系统组件

Harness 作为控制系统，包含以下系统组件：

### 3.1 传感器（Sensor）

**定义**：Harness 通过什么知道状态是真的？

**示例**：
- git / diff / branch metadata
- release/package/VCS version facts（package version、git commit/tag/branch、SVN revision 如适用、registry dist-tag）
- test results
- code review results
- diff impact analysis
- 文档 freshness 检查
- `Harness Control State` 中的控制面信号
- `Milestone` artifact（`.servo/milestone/`）中的聚合进度、验收状态和 handback 边界信号

没有这些，state 只是"自报状态"。

### 3.2 执行器（Executor）

**定义**：什么对象实际改变系统状态？

**示例**：
- human developer
- coding agent（SubAgent）
- review agent（SubAgent）
- merge / rebase / archive 操作
- 文档更新动作

执行器是被 Harness 调度的对象，不等于 Harness 本体。

### 3.3 扰动源（Noise）

**定义**：什么会让系统偏离？

**示例**：
- 需求变化
- agent 幻觉
- 隐式依赖
- branch 漂移
- review 漏检
- 文档过时

扰动必须显式写出来，否则控制律会过于理想化。

### 3.4 恢复策略（Recovery）

**定义**：gate fail 之后如何恢复控制？

**示例**：
- 回滚
- 重试
- 拆分 worktrack
- 降级目标
- 暂停并刷新 repo baseline

---

## 四、被控变量

Harness 控制的不是每一行代码，而是 **Repo 演进的偏差、风险、熵，以及状态转移的合法性**。

当前有 6 个被控变量：

| 被控变量 | 说明 |
|---|---|
| `目标偏差` | 当前 `Repo` / `Worktrack` 距离目标状态还有多远 |
| `范围漂移` | 实际改动是否越出了声明的 scope |
| `集成风险` | 当前改动是否破坏主线或引入不可接受问题 |
| `治理债务` | 文档、测试、结构、规则是否出现缺口 |
| `分支熵` | 活跃分支是否过多、过老、失去用途或偏离基线 |
| `证据完备度` | 当前 `review / test / rule-check` 是否足以支持放行 |

---

## 五、控制平面与执行平面

### 控制平面（Harness 本体）

负责：
- 决定下一步做什么（选择算子）
- 决定谁来执行（绑定技能 + 分派子代理）
- 决定需要哪些证据（定义 Verify 维度）
- 决定当前状态能否继续推进（Gate 裁决）
- 在失败时安排恢复动作（Recover）

控制平面不应因为没有命中一个完全匹配的专用技能，就直接吸收执行责任。正确路径是先把任务压缩成受约束的执行包，再选择专用技能、通用 `SubAgent` 或明确的当前载体回退。

### 执行平面（SubAgent / Human）

负责：
- 实际编码
- 实际 review
- 实际测试
- 实际合并、回滚、清理

因此，Harness 内部的动作应使用控制语义命名：
- `dispatch-subtask`（分派子任务）
- `execute-via-agent`（通过代理执行）

这样才不会把控制器和执行器粘在一起。

---

## 六、三轴模型

Harness 文档与控制逻辑应按 3 个正交维度组织：

### 6.1 Scope 轴

回答"在什么层上控制"：
- `RepoScope` —— 慢变量，长期基线
- `WorktrackScope` —— 快变量，局部状态转移

### 6.2 Function 轴

回答"控制器此刻在做什么"：
- `Observe` —— 状态估计
- `Decide` —— 选择算子
- `Init` —— 初始化局部状态
- `Dispatch` —— 分派执行
- `Verify` —— 收集证据
- `Judge` —— 裁决
- `Recover` —— 恢复控制
- `Close` —— 关闭并交接
- `ChangeGoal` —— 目标变更
- `SetGoal` —— 初始化参考信号

**约束**：`Function` 不是 skill 名字，而是状态转移算子。`Skill` 是这些算子在 `Codex / Claude` 里的相对稳定实现。`SubAgent` 是被 Harness 调度的执行载体。

### 6.3 Artifact 轴

回答"控制器依赖什么正式对象"：
- `Goal / Charter` —— 长期目标，并承载 `Engineering Node Map`
- `Snapshot / Status` —— 当前状态
- `Contract` —— 局部状态转移合同，并绑定从 Goal 派生的 `Node Type`
- `Plan / Task Queue` —— 可执行子任务序列
- `Evidence` —— 状态转移证据
- `Cursor / Control State` —— 控制面当前模式
- `ChangeRequest` —— 目标变更请求

**关键约束**：`Control State` 只保存控制面状态，不承载业务真相。业务真相应分别保存在 `Repo` 与 `Worktrack` 的正式文档里。
`Engineering Node Map` 属于 Repo 级目标真相；`Node Type` 与 `baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy` 属于 Worktrack Contract 的执行约束。下游状态、调度、证据、关卡、恢复和收尾交接只能引用或携带这些字段，不应重新发明策略。

---

## 七、两层控制律

### 7.1 RepoScope 控制律

`RepoScope` 是对长期基线的控制模式。

```
参考信号设定（循环外，Goal 在循环中不可变）：
SetGoal (set-harness-goal-skill) ──→ 仅在 .servo/ 未初始化时
ChangeGoal (repo-change-goal-skill) ──→ 由外部目标变更请求触发
                                    ↓
                              设定/重设完成后启动常规循环

RepoScope 控制回路（Goal 在此回路中不可变）：
Observe (repo-status-skill)
    ↓
Decide (repo-whats-next-skill)
    ↓
    ├─→ 保持并观察 ───────────────────────────────→ 回到 Observe
    └─→ 准备进入 WorktrackScope ──────────────────→ [Scope 切换]
                                                       ↓
WorktrackScope 控制回路（局部状态转移）：               Init (init-worktrack-skill)
                                                       ↓
                                            Observe (worktrack-status-skill)
                                                       ↓
                                            Decide (schedule-worktrack-skill)
                                                       ↓
                                            Dispatch (dispatch-skills)
                                                       ↓
                                            Verify (review-evidence-skill + test-evidence-skill + rule-check-skill)
                                                       ↓
                                            Judge (gate-skill)
                                                       ↓
                                ┌──────────┼──────────┐
                                ↓          ↓          ↓
                              通过      失败/阻塞    恢复
                                ↓          ↓          ↓
                            Close      Recover    Recover
                                ↓          ↓          ↓
                        [Scope 切换]   回到 Observe/  回到 RepoScope
                                ↓          Decide       或等待审批
                        RepoScope.Refresh (repo-refresh-skill)
                                ↓
                            回到 Observe
                                ↓
                        [git hash 对比守卫：若 HEAD 未变则跳过刷新]
```

其中 `Close` 绑定到 `close-worktrack-skill`，`Recover` 绑定到 `recover-worktrack-skill`。

`Observe` 阶段的默认绑定为 `repo-status-skill`。当 `repo-status-skill` 输出 `active_milestone` 非空时，Harness 必须在 Observe→Decide 之间追加绑定 `milestone-status-skill`，获取 `milestone_acceptance_verdict`、`milestone_gate_verdict`、`proceed_blockers`、`handback_required`、`milestone_input_checkpoint` 等 Milestone 级裁决字段后再进入 `repo-whats-next-skill` 的 Decide 判定。收到 `milestone_input_checkpoint` 后应将其写回 control-state 的 `Baseline Traceability.milestone_input_checkpoint` 供下一轮幂等性对比。若无活跃 Milestone，跳过此额外绑定。

当存在活跃 goal-driven milestone 且仍有待执行 worktrack 时，Harness 以逐 worktrack 推进的方式运行当前 milestone：每次只派生一个当前 worktrack，为其建立独立 branch、contract、plan-task-queue、gate evidence、closeout 和 repo-refresh 追踪；完成当前 worktrack 的闭环后，再回到 RepoScope 选择下一个 current worktrack。

**控制目标**：维护 Repo 的长期基线稳定，判断是否需要进入局部执行。

### 7.2 完整状态闭环

```
RepoScope.SetGoal ──→ RepoScope.Observe ──→ RepoScope.Decide ──→ WorktrackScope.Init
                                                          ↓
                                               WorktrackScope.Observe
                                                          ↓
                                               WorktrackScope.Decide
                                                          ↓
                                               WorktrackScope.Dispatch
                                                          ↓
                                               WorktrackScope.Verify
                                                          ↓
                                               WorktrackScope.Judge
                                                          ↓
                                          ┌───────────────┼───────────────┐
                                          ↓               ↓               ↓
                                        通过            失败/阻塞        恢复
                                          ↓               ↓               ↓
                                      Worktrack       Worktrack      Worktrack
                                       .Close          .Recover       .Recover
                                          ↓               ↓               ↓
                                   RepoScope.Refresh (repo-refresh-skill)  回到 Observe/ 回到 RepoScope
                                                        Decide       或等待审批
                                          ↓
                                   RepoScope.Observe ──→ [循环]
                                          ↓
                                   [git hash 对比守卫：若 HEAD 未变则跳过刷新]
```

其中 `Close` 绑定到 `close-worktrack-skill`，`Recover` 绑定到 `recover-worktrack-skill`。

**关键约束**：`PR` 不是闭环终点。完整的 closeout 是 `merge → refresh repo snapshot → cleanup → return RepoScope`。只有这样，Repo 的慢变量才会被真实更新，而不是停留在"PR 已发出"的半闭环状态。

对于 active milestone，这个闭环以当前 worktrack 为单位反复运行：一个 worktrack 完成一次完整闭环，milestone 才聚合一次已验证进度；下一次派生从新的 current worktrack 重新开始，持续形成清晰的逐项执行轨迹。

---

## 八、Gate 的三轴裁决模型

Harness 不能只有 `Gate`，必须同时有 `Evidence`。

- `Evidence` 负责证明"当前状态是什么"
- `Gate` 负责判断"当前状态是否允许推进"

二者必须分开。

Gate 应汇总**正交校验面**的裁决：

| 校验面 | 判定内容 | 对应 Verify 技能 |
|--------|---------|----------------|
| `implementation-gate` | 代码正确性、结构合理性 | review-evidence-skill |
| `validation-gate` | 测试、验收条件、运行结果 | test-evidence-skill |
| `policy-gate` | 规则、边界、不变量、治理要求 | rule-check-skill |

最后由汇总 `gate-skill` 生成最终 verdict。

对 milestone 而言，所有 worktrack 各自通过 closeout gate 后，还存在一个独立的 **Milestone Gate**。它是 goal-driven milestone 的 RepoScope 集成验收层，位于“全部 worktrack 关闭”之后、“`purpose_achieved` 判定”之前；必须同时覆盖 black-box、white-box、anti-cheat 和 composite acceptance lanes。`Milestone Gate` 以每个已闭环 worktrack 的 closeout record、gate evidence、repo-refresh 结果和 composite acceptance report 为聚合输入，在逐 worktrack 可追溯基础上形成 milestone 级集成放行条件。

---

## 九、何时使用

当任务不是"写代码"，而是"运行当前的 Harness 控制回路"时，使用这个技能：

- 判定当前处于哪个 `Scope` 和哪个 `Function`
- 在控制平面上推进状态估计→算子选择→技能绑定→子代理分派→证据收集→裁决→状态更新
- 为每一轮控制回路收集最小必要证据
- 从下游技能获得结构化输出（`允许的下一路由`、`建议下一路由`、`可继续`、`继续阻塞项`、审批字段），而不是在 Harness 内部自行推断
- 只要下一次状态迁移仍然合法，且没有命中正式停止条件，就继续推进
- 只有在审批、缺失证据、运行时缺口或其他停止条件阻断安全继续时，才向程序员汇报当前状态

---

## 十、控制回路运行规范

### 10.1 状态估计阶段

1. **现有 `.servo` 配置读取 / 恢复前置**：任何 Harness 轮次启动时，必须先读取既有 `.servo/control-state.md`，恢复控制面配置与上次交接边界，再进入状态估计。
   - 如果 `.servo/control-state.md` 或 `.servo/goal-charter.md` 缺失，说明 Harness 尚未初始化，应路由到 `SetGoal` / `set-harness-goal-skill`，不得凭当前对话临时假设长期配置。
   - 必读控制配置段包括 `Linked Formal Documents`、`Approval Boundary`、`Continuation Authority`、`Handback Guard`、`Baseline Traceability` 和 `Autonomy Ledger`。
   - 缺失控制字段按最保守默认值解释：权限/自动性为未授权，状态为 `unknown` / `missing` / `blocked` / `not ready`，列表为空，布尔值为 `false`；同时在状态估计中记录 `config_hydration_gaps`。缺失不能静默扩大权限或自动性。Source-side authoring trace: `docs/harness/artifact/control/control-state.md`。
   - 本轮用户若给出长期权限、自动性或分派策略变更，必须先判定是一次性审批还是持久配置变更。持久变更只能写入 `.servo/control-state.md` 的对应配置段；若改变 canonical 字段语义或默认值，还必须同步更新 source-side control-state contract 与初始化模板。
   - `.servo/control-state.md` 只保存控制配置、路径指针与控制面记忆，不得写入 Repo 目标、Worktrack 业务真相或未验证结论。
   - 入口分流必须在 hydration 之后发生；缺少 artifact 或审批信号时，profile / operator mode 只能降级为 observation / handback / blocked，不得扩大权限。
   - operator mode matrix 只消费 trigger signals 并选择 route estimate 与 stop/approval semantics；它不得创建新的 Scope、Gate、controller 或 not approved scope 的执行权限。
2. 读取 `Harness Control State`，确定当前 `Scope` 和 `Function`
3. **分支环境检查（Branch Environment Guard）**：
   - 从 `.servo/control-state.md` 的 `Baseline Branch` 段读取 `baseline_branch`（servo-managed final baseline），并读取 `active_milestone_branch` / `active_milestone_branch_sync_state`。
   - 若当前处于 WorktrackScope，还必须从当前 `Worktrack Contract` 读取 `branch_source_ref`、`worktrack_branch`、`closeout_target_ref`、`checkpoint_base_ref`。
   - 执行 `git branch --show-current` 获取当前检出的分支
   - 先判定当前 `branch_context`：
     - `baseline`: 当前分支等于 `baseline_branch`。
     - `milestone`: 当前分支等于 active Milestone 的 `active_milestone_branch`。
     - `worktrack`: 当前分支等于当前 Worktrack Contract 的 `worktrack_branch`。
     - `unknown`: 无法匹配上述任何上下文，或缺少必要合同字段。
   - 按 Scope / Function 应用合法变更上下文：
     - `RepoScope.Observe` / `RepoScope.Decide`: 只读，可在任一 branch_context 上继续，但必须记录 `branch_context_observed`；若上下文不是 baseline 或 milestone，进入会修改状态的下一步前必须先切回合法上下文。
     - `RepoScope.Init` 派生 Milestone branch 或激活/切换 Milestone: 必须在 `baseline` 上执行，除非唯一动作是将已验证 Worktrack closeout 写回现有 active Milestone branch 的 routing metadata。
     - `WorktrackScope.Init`: 若为 milestone-derived Worktrack，必须在 `milestone` 上执行并从 `active_milestone_branch` 创建 `worktrack_branch`；非 milestone-derived Worktrack 必须在 `baseline` 上执行。
     - `WorktrackScope.Dispatch` / `Implement` / `Verify` / `Judge`: 必须在 `worktrack` 上执行；只读 evidence collection 可记录 warning，但不得修改非合同 worktrack branch。
     - `WorktrackScope.Close`: 可以在 `worktrack` 上准备 closeout，也可以在 `closeout_target_ref` 指向的 `milestone` 或 `baseline` 上执行 merge/checkpoint；PR target、merge target 和 checkpoint target 必须来自 Worktrack Contract。
     - `RepoScope.Refresh`: 必须在刚完成 closeout 的 `closeout_target_ref` 上刷新；Milestone-derived Worktrack 的 direct refresh 是 `milestone`，Milestone final acceptance 后才刷新 `baseline`。
   - 若当前 branch_context 与预期上下文不一致：
     - 对只读 `Observe`：记录 `branch_context_warning` 和所需切换目标，允许继续收集状态。
     - 对任何会修改仓库状态的 Function：返回 `branch_context_blocked`，停止变更，并明确合法恢复路径是切换到 contract/control-state 指定的目标分支；不得猜测默认分支或从当前分支名反推目标。
   - 此检查必须在 `git rev-parse HEAD`（步骤 4）之前执行，确保后续的 hash 对比基于正确的分支上下文
   - 如果 `baseline_branch` 在 control-state 中缺失，按 `origin/HEAD` 动态解析（执行 `git remote show origin | grep 'HEAD branch' | awk '{print $NF}'`），并将解析结果写入 `config_hydration_gaps`。不得写死默认分支名
4. 根据当前 Scope 选择传感器组合：
   - `RepoScope`：读取 `Repo Goal/Charter`、`Repo Snapshot/Status`
   - `WorktrackScope`：读取 `Worktrack Contract`、`Plan/Task Queue`、当前 evidence
5. **Git Commit Hash 基线对比（幂等性守卫）**：
   - 读取 `.servo/control-state.md` 的 `Baseline Traceability` 段，获取 `latest_observed_checkpoint`（即上次刷新时记录的 git commit hash）
   - 执行 `git rev-parse HEAD` 获取当前 HEAD hash
   - 对比两个 hash：若一致，说明 repo 代码基线自上次刷新后未变化，跳过 `repo-refresh-skill` 绑定，仅在状态估计中标记 `repo_baseline_unchanged: true`
   - 若 hash 不一致（或 `latest_observed_checkpoint` 缺失），说明代码基线已变化，必须在本轮合适阶段绑定 `repo-refresh-skill` 刷新 Repo 级慢变量
   - 此检查确保不会对同一基线重复执行 repo-refresh，避免不必要的刷新开销
6. **文档 Freshness 基线对比**：如果发现本轮涉及 release、deploy、adapter、package、VCS baseline、CLI 版本或 operator-facing docs，且文档版本事实可能落后于代码/registry/VCS 证据，应标记 `doc_catch_up_needed: true`，并在合适阶段绑定 `doc-catch-up-worker-skill`；如果上次 `doc-catch-up` 执行时的 git hash 与当前 HEAD 一致且无新的文档变更，可跳过重复追平
7. 如果标准快照缺失、过期或明显不足，只收集解释缺口所需的最小探查证据
8. 产出结构化状态估计结果，而不是文字摘要

### 10.2 算子选择阶段

1. 基于状态估计结果，评估合法的状态转移算子集合
2. 在 `RepoScope` 下，评估是否需要：
   - `Observe`（继续观察）
   - `Init`（进入 WorktrackScope）

   **关键约束**：`ChangeGoal` 不由常规 Decide 选择。目标变更由外部请求触发，完成后系统重新进入 Observe。
   **work-collection 路由差异**：当 active milestone 为 work-collection 类型时，milestone achieved 后不触发 handback，自动推进 pipeline（标记 superseded → 选择下一 planned milestone 或清空 active_milestone → 继续 Observe）。
   **milestone brief 约束**：当 `repo-whats-next-skill` 建议 `create` / `activate` / `append_worktracks` 时，Harness 必须先把结构化 `milestone brief` 交给 programmer 确认；未确认前不得绑定 `init-milestone-skill` 去激活 goal-driven milestone，也不得把建议视为已获批自动继续。
   **complex-project entry gate 约束**：当 RepoScope.Decide、pre-milestone intake 或 init milestone 输出 `complex_project_entry_gate` 时，Harness 必须把它作为 Milestone-side blocking gate 处理，而不是固定 heavy mode；canonical guard term: not fixed heavy mode。scanner output is evidence, not verdict；`scanner_evidence_ref` 和 `complexity_signals` 不能单独清空阻断。若 `milestone_blocking_decision` 包含 `block_create`、`block_upsert`、`block_activate` 或 `block_derive_worktrack`，不得绑定对应 initializer。unresolved gate blocking default: missing, blank, placeholder, pending, or incomplete gate 与明确 block 等价，不得解释为 `clear` 或 `not_applicable`。缺失 `operator_safety_policy`、`dialog_review_questions`、`entry_verdict = needs_reinforcement_milestone`、`reinforcement_milestone_recommendation.needed = true`、`reinforcement_milestone_recommendation.recommendation_status = recommended|required|pending_operator_review` 或 `reinforcement_milestone_recommendation.blocks_implementation_until_resolved = true` 时，必须回到 RepoScope handback / reinforcement documentation / project-understanding Milestone 路径；`reinforcement_milestone_recommendation` 字段存在但 `needed = false` 且 `recommendation_status = not_needed` 不能单独阻断低风险 `clear` / `not_applicable` gate。temporary understanding 是 runtime evidence, not Goal Charter truth，未获 programmer confirmation 或 verified evidence 不得升格为长期 truth。WorktrackScope 内的 `normal`、`autoreview`、`yolo` 执行策略仍由 Worktrack 合同和用户安全策略决定，不替代 Milestone-side blocker。
   **Milestone Review Gate route guard**：当 `repo-whats-next-skill` 建议从 active goal-driven milestone 进入 WorktrackScope.Init 时，Harness 必须先检查 active milestone 的 `milestone_review_gate` 与 control-state 的 active review routing state。只有 `milestone_review_gate_ready = true`、`latest_review_status = effective_pass`、`milestone_review_count >= 1`、`effective_review_pass = true`、`latest_review_checkpoint` 非空，且不存在 `review_invalidated_by` 阻断项时，才允许绑定 `init-worktrack-skill`。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全必须阻断 Worktrack Init/Dispatch，并返回 `milestone_review_gate_not_ready`。不得把 skipped intake、questions-required intake 或 stale checkpoint 解释为 ready。
   **Conservative runtime backfill**：当 `.servo` runtime artifact 缺少新添加字段时，Harness 只能做 forward-only conservative runtime backfill：缺失值按 `false`、`unknown`、`missing`、`blocked`、`not ready`、`N/A` 或空 blockers 解释，并把 gap 记录为 evidence。缺失字段不得扩大权限、不得推断 programmer confirmation、不得增加 `milestone_review_count`、不得设置 `effective_review_pass = true`、不得把 `milestone_review_gate_ready` 设为 true，也不得允许 Worktrack Init/Dispatch；需要审批、dispatch、review pass 或 autonomy 的字段在 verified evidence 或 programmer confirmation 前一律 blocked/not ready。Guard terms: must not grant permissions, must not infer programmer confirmation, must not increment counters, must not enable Worktrack Init/Dispatch。
   **Worktrack intake review 约束**：当 `repo-whats-next-skill` 建议从 active milestone 进入 WorktrackScope.Init 时，Harness 必须消费结构化 `worktrack_intake_review`。只有 `intake_review_verdict = ready_for_worktrack_init` 且 `ready_for_worktrack_init = true`，并且其中包含 `repo_fundamentals`、`snapshot_freshness`、`milestone_purpose_alignment`、`historical_conflict_risk`、`worktrack_adjustment_recommendations` 与 `add_remove_worktrack_recommendations`，才允许绑定 `init-worktrack-skill`。`refresh_required`、`adjust_worktracks`、`blocked` 或 intake review 缺失时，必须停留在 RepoScope 的刷新/调整/观察路径，不得静默初始化 worktrack。
3. 在 `WorktrackScope` 下，评估是否需要：
   - `Init`（初始化局部状态）
   - `Observe`（状态估计）
   - `Decide`（调度）
   - `Dispatch`（分派执行）
   - `Verify`（收集证据）
   - `Judge`（裁决）
   - `Recover`（恢复）
   - `Close`（收尾）
4. 只推荐一个算子，并投影成显式路由、阻塞项集合与审批状态

### 10.3 技能绑定阶段

1. 将选定的算子映射到具体的 Skill 实现
2. 检查当前部署配置是否支持该 Skill
3. 如果部署配置缩窄了路由空间，把该配置视为硬路由边界

### 10.4 子代理分派阶段

1. 为选定的 Skill 构建限定范围任务简报和信息包
2. 读取执行载体开关：先看 `.servo/control-state.md` 的 `subagent_dispatch_mode_override_scope`。默认 `worktrack-contract-primary` 表示当前 `Worktrack Contract` 的 `runtime_dispatch_mode` 优先；只有显式 `global-override` 才让 `.servo/control-state.md` 的 `subagent_dispatch_mode` 压过 worktrack。若 worktrack 未声明，再使用 control-state 作为 repo 级默认值，最终默认值为 `auto`
3. `runtime_dispatch_mode` / `subagent_dispatch_mode` 支持 `auto` / `delegated` / `current-carrier`
4. `auto` 表示按本包内 dispatch 决策规则选择 SubAgent、专用 skill、generic worker 或 current-carrier：综合 `task_coupling`、`state_sharing_need`、`parallel_value`、`risk_profile`、`context_budget_fit`、`runtime_supports_subagent`、`permission_allows_delegation` 与 `dispatch_package_safety`；高共享/低并行价值默认 current-carrier，低耦合/高并行价值且运行时允许时优先 SubAgent，高风险实现可保持当前载体但 review/test/policy evidence 应独立验证。运行时没有稳定分派壳层、权限边界禁止委派，或任务包不满足安全分派条件时，必须显式 fallback。Source-side authoring trace: `docs/harness/foundations/dispatch-decision-policy.md`
5. `delegated` 表示必须真实创建委派载体；如果无法委派，应返回运行时缺口或权限阻塞，而不是自动改为当前载体执行
6. `current-carrier` 表示本轮显式关闭 SubAgent 委派，允许当前载体在同一份限定范围约定内执行
7. 发生当前载体运行时回退时，必须显式记录回退原因、未委派原因和保持的任务/信息边界
8. 不要声称已经分派了子代理，除非宿主运行时真的创建了委派载体
9. 每轮 Dispatch 必须记录 `runtime_dispatch_profile`，至少包含 `backend_runtime`、`model_family`、`subagent_dispatch_shell`、`runtime_supports_subagent`、`subagent_permission_state`、`permission_allows_delegation`、`dispatch_package_safety`、`delegation_attempted`、`attempted_carrier`、`carrier_decision` 与 `fallback_reason`。在 ClaudeCodeCLI / Deepseek 兼容 lane 中，无法证明 SubAgent shell 可用时，不得静默 current-carrier；必须把 capability probe 与 fallback 证据写入 dispatch result 或 gate evidence。

### 10.5 证据收集阶段

1. 消费子代理返回的结构化输出
2. 在 `Verify` 阶段，收集三个正交维度的证据：
   - 审查维度（代码正确性、结构合理性）
   - 验证维度（测试、验收条件）
   - 策略维度（规则、边界、不变量）
3. 证据必须结构化，不能是文字摘要

### 10.6 裁决阶段

1. 基于收集到的证据，执行 Gate 裁决
2. 在三个校验面上分别判定
3. 汇总生成最终 verdict：
   - `通过`
   - `软失败`
   - `硬失败`
   - `阻塞`

### 10.7 状态更新阶段

1. 根据裁决结果更新 `Harness Control State`
2. 如果是 `通过` → 进入 `Close` → 然后 `RepoScope.Refresh`：
   - **显式绑定 `repo-refresh-skill`**，从已验证 `关卡证据` 刷新 `Repo Snapshot/Status`
   - 刷新完成后，执行 `git rev-parse HEAD` 获取当前 HEAD hash，将其写入 `.servo/control-state.md` 的 `Baseline Traceability.latest_observed_checkpoint` 字段，作为下次状态估计时 git hash 对比的锚点
   - 此 hash 存储确保下次 Harness 轮次启动时能正确判断是否需要重新刷新
3. 如果是 `失败/阻塞` → 进入 `Recover`
4. **文档追平收口**：在 Close、handback 或 release/post-smoke 收口前，如果本轮改变了代码版本、package/release 事实、git/SVN baseline、deploy/adapter 行为、验证命令或 operator-facing 文档，必须调用或显式安排 `doc-catch-up-worker-skill`；版本事实场景使用 `version fact sync`，并记录 source version、published version、VCS tracking facts 与未更新文档理由。如果 `doc-catch-up` 成功执行，将当前 git hash 写入 `.servo/control-state.md` 的 `Baseline Traceability.last_doc_catch_up_checkpoint`，作为下次文档 freshness 检查的对比锚点
5. **长期权限配置写回**：如果本轮经程序员明确批准了持久权限、自动性或分派策略变更，必须把配置事实写回 `.servo/control-state.md` 的 `Approval Boundary`、`Continuation Authority` 或 `Autonomy Ledger`，并记录审批理由；一次性审批只能写入本轮 evidence / handoff，不得伪装成长期默认配置。
   - 连续执行或低风险 Worktrack 自批必须同时满足 Control State 的 `Low-Risk Default-Flow Autonomy Policy`：`allowed` 命中、`forbidden` 未命中、`stop_condition` 未命中、`evidence_required` 已能满足或已安排。
   - `allowed` 仅覆盖已批准 milestone / worktrack 边界内的只读观察、artifact hydration、状态一致性检查、Worktrack 内队列调度、非破坏性 docs/template/test 编辑、匹配范围本地验证、通过 Gate 后 repo-refresh 写回、无外部副作用 scaffold validation。
   - `forbidden` 包括 goal change、scope expansion、milestone final acceptance、release / publish / package version / tag / dist-tag、GitHub Release、publish workflow、protected branch mutation、force push、大量文件删除、destructive cleanup、secret/security/privacy、deploy/network/database migration、跨 repo 副作用、外部付费/配额消耗。
   - `stop_condition` 包括 evidence missing or conflicting、branch mismatch、Gate soft-fail / hard-fail / blocked、context noise / prompt forgetting、需要 programmer 判断、权限边界不清、Worktrack Contract 外扩、protected branch policy 命中、destructive operation 命中、release-sensitive 信号命中、Milestone final acceptance 边界命中。
   - `evidence_required` 至少包括 route decision、Worktrack Contract / scope boundary、selected task / dispatch packet、runtime dispatch profile、validation / governance / policy evidence、Gate verdict、closeout record、repo-refresh checkpoint。任一 forbidden 或 stop_condition 命中时，不得静默推进，必须 handback、审批或 recover。
6. **Milestone 状态写回**：收到 `milestone-status-skill` 输出后，`harness-skill` 必须执行以下写回动作（按 `milestone_kind` 分化）：
   - **Final Acceptance 事务边界**：
     - `milestone_acceptance_verdict == "achieved"` 与 `milestone_gate_verdict == "pass"` 只表示 milestone 达到可交接验收状态；goal-driven milestone 的最终验收仍由 programmer 决定。
     - goal-driven milestone handback 前必须存在 composite acceptance report，或存在逐 lane 记录的合法 fallback evidence。报告必须覆盖 code-review、feature-completeness、related-influence、intent-completeness、operator-simulation 和 professional-review。任一 lane 为 `blocked`、任一 high severity finding、或未被 programmer 接受为后续范围的 `needs_followup_worktrack`，均不得进入 final acceptance ready。
     - programmer 明确接受 goal-driven milestone 后，acceptance writeback 必须作为一个逻辑事务处理：预先校验 milestone artifact、milestone-backlog、control-state、handback guard、baseline traceability 与 worktrack status 输入；再写入所有相关 artifact；最后做提交后校验。
     - 该事务的最小写入集合为 `.servo/milestone/{milestone_id}.md`、`.servo/repo/milestone-backlog.md`、`.servo/repo/milestone-history.md`、`.servo/control-state.md`，以及必要时 `.servo/repo/worktrack-backlog.md` 中对应 worktrack 的状态归一化。
     - 对 goal-driven milestone，programmer final acceptance 后 backlog 中该 milestone 的所有已闭环 worktrack 不得继续标记为 `(planned)` 或 `(active)`；必须归一化为 `(done)`、`(deferred)`、`(blocked)` 或等价已决状态。
     - 写回后必须校验：同一时刻最多一个 active milestone；control-state 的 `active_milestone` 与 live backlog 唯一 active 条目一致；`milestone_status` 与 active milestone 状态一致；`milestone_pipeline_summary` 与 live backlog + milestone history aggregate 计数一致；completed/accepted history milestone 不含未完成 worktrack 标记。
     - 任一写入或提交后校验失败时，不得伪装成已完成验收；必须标记 `writeback_incomplete` / `milestone_pipeline_stale`，返回 `proceed_blockers`，并停在 RepoScope.Observe 或 handback，等待恢复或 programmer 决策。
   - **Milestone Artifact 更新**（`.servo/milestone/{milestone_id}.md`）：
     - 将 `progress_counter` 更新为 milestone-status-skill 计算的值（total/completed/blocked/deferred）
     - goal-driven 且 `milestone_acceptance_verdict == "achieved"`、`milestone_gate_verdict == "pass"` 且双重验收通过：将 `status` 从 `active` 更新为 `completed`
     - work-collection 且 `milestone_acceptance_verdict == "achieved"`（worktrack_list_finished == true）：将 `status` 从 `active` 更新为 `completed`，随后自动标记为 `superseded`
     - 更新 `updated` 时间戳
     - 不修改 `progress_counter` 以外的派生字段
   - **Control State 更新**：
     - 写入 `milestone_input_checkpoint` 到 `Baseline Traceability`
     - 若 milestone 状态变更（active→completed）：更新 `milestone_status`、`milestone_pipeline_summary` 和 milestone-history
     - 若 `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct` 在本轮被上游修改：必须使旧的 milestone 完成结论失效，并强制重新进入下一轮 `milestone-status-skill` 观察
   - **Pipeline 推进**（仅在 milestone achieved 后，按 `milestone_kind` 分化）：
     - goal-driven：handback 等 programmer 验收，不自动推进
     - work-collection：不触发 handback，自动推进 pipeline
     - 读取 `milestone-status-skill` 输出的 `pipeline_advancement`
     - 若存在符合条件的下一 planned milestone：更新其 status 为 `active`，更新 control-state 的 `active_milestone`
     - 若不存在：清空 control-state 的 `active_milestone`
   - **Milestone Backlog / History 更新**：planned/active 条目同步 upsert 到 `.servo/repo/milestone-backlog.md`；completed/superseded 条目从 live backlog 移入 `.servo/repo/milestone-history.md`；work-collection milestone 完成时写入 history `status: superseded`
   - 若 `milestone_gate_verdict != "pass"`：不得把 Milestone 标记为完成，不得自动推进 pipeline，必须返回 `handback_required = true` 并暴露阻断原因
   - 不得跳过 milestone progress writeback；不得在 `milestone_acceptance_verdict` 未达成时变更 milestone status
7. 如果命中正式停止条件 → 向程序员返回控制权
8. 不要直接把子代理的返回结果当成状态更新的唯一依据；必须经过 Gate 裁决

### 10.8 Git Commit Hash 幂等性守卫

Harness 使用 git commit hash 作为幂等性锚点，避免对同一代码基线重复执行 `repo-refresh-skill` 和 `doc-catch-up-worker-skill`。

**存储位置**：`.servo/control-state.md` 的 `Baseline Traceability` 段。

**字段定义**：

| 字段 | 含义 | 更新时机 |
|------|------|---------|
| `latest_observed_checkpoint` | 上次 `repo-refresh-skill` 执行后记录的 git HEAD hash | `RepoScope.Refresh` 完成后写入 |
| `last_doc_catch_up_checkpoint` | 上次 `doc-catch-up-worker-skill` 执行后记录的 git HEAD hash | 文档追平完成后写入 |
| `verified_at` | 最近一次 checkpoint 验证时间 | 每次检查更新 |

**工作逻辑**：

```text
Harness 启动 → 状态估计阶段
  ├─ git rev-parse HEAD → 当前 hash
  ├─ 读取 latest_observed_checkpoint
  │   ├─ hash 一致 → repo_baseline_unchanged: true → 跳过 repo-refresh-skill
  │   └─ hash 不一致/缺失 → repo_baseline_changed: true → 绑定 repo-refresh-skill
  ├─ 读取 last_doc_catch_up_checkpoint
  │   ├─ hash 一致且本轮无文档变更 → 跳过 doc-catch-up-worker-skill
  │   └─ hash 不一致或有文档变更 → doc_catch_up_needed: true → 绑定 doc-catch-up-worker-skill
  └─ 继续正常控制回路

Close/Refresh 完成 → 状态更新阶段
  ├─ repo-refresh-skill 执行成功 → 写入 latest_observed_checkpoint = HEAD hash
  └─ doc-catch-up-worker-skill 执行成功 → 写入 last_doc_catch_up_checkpoint = HEAD hash
```

**硬约束**：

- git hash 对比仅作为"跳过重复刷新"的条件，不得作为"跳过首次验证"的借口
- `doc-catch-up` 的 hash 对比只能跳过"代码未变且文档未变"的重复追平；如果本轮明确修改了文档，即使 hash 未变也必须触发文档追平检查

---

## 十一、正式停止条件

只有在以下至少一个条件成立时才停止并返回控制权：

- **`审批门控`**：目标变更、范围扩张、破坏性动作或其他权限边界把 `需要审批` 置为 `真`
- **`证据门控`**：所需产物或证据缺失、过期或互相矛盾，已经无法安全继续
- **`路由阻塞`**：当前路由命中 `软失败`、`硬失败`、`阻塞`，或抛出了显式 `继续阻塞项`
- **`运行时缺口`**：宿主运行时缺少供下一个执行载体使用的安全分派壳层
- **`约定边界`**：下一步动作将越出已批准的代码仓库或工作追踪约定
- **`稳定交接`**：同一个交接边界在连续无变化轮次中再次被确认，因此再做一次完整重读只会重复相同的停止判定结果

---

## 十二、恢复策略

当 Gate 裁决为失败或阻塞时，Harness 必须进入恢复模式。合法恢复算子：

| 恢复算子 | 适用条件 | 限制 |
|---------|---------|------|
| `重试` | 当前目标、排除目标与基准仍然有效 | 不得扩大范围或重定义验收 |
| `回滚` | 当前状态已不可安全继续 | 除非程序员明确批准，否则执行破坏性变更前必须停止 |
| `拆分 Worktrack` | 当前范围过宽或包含多个独立验收切片 | 不得静默创建新 Worktrack；必须明确验收标准分配 |
| `刷新基准` | 上游真相变化使当前分支比较失效 | 不得改写 Repo Snapshot/Status 或目标/章程 |
| `重新规划` | 当前路径整体不可行 | 必须回到 RepoScope 重新 Decide |

以上恢复策略由 `recover-worktrack-skill` 实现。Gate 裁决为失败或阻塞时，应绑定 `recover-worktrack-skill` 执行恢复动作；恢复成功后的收尾由 `close-worktrack-skill` 负责。`close-worktrack-skill` 同时负责 WorktrackScope 的正常收尾（Gate 通过后的 Close 路径）。

### Milestone Pipeline 恢复

当 Milestone Pipeline 出现不一致时，`harness-skill` 在 Observe 阶段应检测并执行以下恢复动作：

| 恢复动作 | 触发条件 | 操作 |
|---------|---------|------|
| `rebuild-pipeline` | milestone-backlog 损坏或与 `.servo/milestone/` 目录不一致 | 重新扫描 `.servo/milestone/` 目录，从 artifact 文件重建 milestone-backlog |
| `reconcile-active` | control-state `active_milestone` 指向不存在的 milestone | 清空 `active_milestone`，标记 `milestone_pipeline_stale: true`，触发 pipeline 重新评估 |
| `repair-binding` | worktrack-backlog 中存在 milestone_id 但对应 milestone 不存在 | 标记为 orphan binding，在 milestone-status-skill 输出中暴露，等待 programmer 决策 |
| `clear-stale-reference` | milestone artifact 文件存在但不在 backlog 中 | 按 artifact 文件重建 backlog 条目（保留原始 created_at/created_by） |

检测到以上任一情况时，`harness-skill` 应标记为 `pipeline_corruption_detected` 并执行相应恢复动作。恢复后重新绑定 `milestone-status-skill` 做完整状态评估。若自动恢复失败（如 artifact 文件本身损坏），必须 handback 等待 programmer 介入。

### Work-Collection 专属恢复

work-collection milestone（`milestone_kind == "work-collection"`）在以下场景有专属恢复路径：

| 恢复动作 | 触发条件 | 操作 |
|---------|---------|------|
| `defer-and-close` | work-collection 内单个 worktrack 阻塞且无法推进 | 将该 worktrack 标记为 deferred，完成剩余 worktrack 后正常关闭 milestone（标记 superseded）；被 defer 的 worktrack 由 programmer 决定重新归入或放弃 |
| `dissolve-collection` | work-collection 内所有 worktrack 均阻塞或 deferred | 关闭 milestone（标记 superseded），将所有 worktrack 释放为未归属状态，等待 programmer 重新分配 |

---

## 十三、预期输出

使用这个技能时，产出一份 `Harness 控制回路报告`，至少包含：

### 控制面章节

- `当前 Scope`
- `当前 Function`
- `控制状态评估`
- `本轮已执行控制动作`
- `已审阅的产物与证据`
- `已运行的下游轮次`

### 状态转移章节

- `状态估计结果`
- `所选算子`
- `绑定技能`
- `分派模式`
- `收集的证据摘要`
- `Gate 裁决结果`

### 路由决策章节

- `允许的下一路由`
- `建议下一路由`
- `建议下一 Scope`
- `建议下一 Function`
- `可继续`
- `继续阻塞项`

### 权限与交接章节

- `需要审批`
- `审批范围`
- `审批理由`
- `待审批`
- `如何审查`

### 控制回路元数据

- `约定后自动性`
- `已使用自动继续`
- `检测到稳定交接`
- `交接状态`
- `交接锁激活`
- `检测到解锁信号`
- `交接解锁条件`
- `继续决策`
- `命中停止条件`

---

## 十四、Artifact Output Protocol

所有 skill 产出的 artifact 必须遵守以下全局协议：

1. **先完整生成，再做压缩**：每个 skill 先生成尽可能长且完整的原始内容，确保信息不丢失；然后通过压缩步骤提取 `Control Signal` 层。
2. **控制结论优先**：影响下一动作决策的信息放在 `Control Signal` 层；完整证据、日志、原始输出放在 `Supporting Detail` 层。
3. **禁止平铺重复**：已在其他 artifact 中记录的信息，使用引用（文件路径 + section）而不是内联全文复制。
4. **空值压缩**：无实质内容的字段使用 `N/A`，删除占位符行（如 `- ` 或 `待填写`）。
5. **引用格式**：引用其他 artifact 时使用 `[artifact-path#section]` 格式，例如 `[.servo/worktrack/contract.md#Task Goal]`。
6. **压缩不是省略**：`Supporting Detail` 层必须保留完整内容，只是不纳入传递/决策上下文；后续如需查阅细节，可直接读取。

## 十五、硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

本技能特有约束：

- **Harness 输出只能是控制决策结构体**（Scope/Function/Route/Verdict/Evidence 引用）；代码块和直接执行指令禁止出现在 Harness 输出中。
- **Function 算子必须在控制面上显性化**为 `Observe → Decide → Dispatch → Verify → Judge → Recover → Close → ChangeGoal` 的控制语义；禁止仅通过技能名称隐式传达当前算子。
- **Harness 仅负责选择算子、绑定技能和裁决 Gate**；具体代码仓库动作、任务列表内容和执行任务的细节由下游技能的算子实现负责。
- **SubAgent 使用必须是可开关参数，而不是硬编码行为。** 控制态字段 `subagent_dispatch_mode` 与工作追踪约定字段 `runtime_dispatch_mode` 支持 `auto` / `delegated` / `current-carrier`；控制态字段 `subagent_dispatch_mode_override_scope` 默认是 `worktrack-contract-primary`，只有显式 `global-override` 才是全局覆盖；默认 `auto` 表示按 Dispatch Decision Policy 选择载体，不得把运行时支持 SubAgent 单独当成默认委派理由。未委派时必须将原因记录为 `runtime fallback`、`permission blocked` 或 `dispatch package unsafe`。
- **现有 `.servo` 控制配置必须先 hydration 再决策。** Harness 不得忽略上一轮 `.servo/control-state.md` 中的 linked artifact、approval boundary、continuation authority、handback guard、baseline traceability 或 autonomy ledger；缺失字段只能按 artifact 合同默认值降级解释，不能静默扩大权限。
- **长期权限变更必须写回控制配置。** 程序员授予的持久自动性、分派模式、审批边界或预算变更必须写入 `.servo/control-state.md` 的配置段；若只是本轮一次性批准，必须保留为本轮 evidence / handoff，不得改变长期默认值。
- **约定后自动工作追踪仅当 `Harness Control State` 明确授予 `约定后自动性：最小委派` 时才可开启**；否则必须保持手动交接模式。
- **自动继续推进的边界严格等于当前 `Worktrack Contract` 的 scope**；超出 scope 的改动、目标重定义或预算超支必须触发审批门控。
- **自动切片仅可在当前切片未收束时串接**；一旦切片收束且 `要求自动切片后停止` 为真，必须停止执行并重新交接。
- **稳定交接达成后，运行时唯一合法状态是 `等待交接`**；仅当观测到显式解锁信号时方可退出此状态。
- **解锁信号必须是程序员显式发出的新指令或实质性新信息**；裸 `重试`、裸 `继续工作` 或重复文字摘要不构成解锁信号。
- **交接锁激活时，所有控制回路阶段的进入必须被阻断**；仅当有效解锁信号出现后控制回路方可恢复。
- **技能轮次返回结构化输出是正常控制回路产物**；停止条件仅由 [十一、正式停止条件] 定义的六种正式条件触发。
- **Evidence、Verdict 和 NextAction 必须在输出中分节独立呈现**；每节仅包含对应类型的内容，禁止将三者合并为一段叙述。
- **相邻系统的引用仅当本轮证据确实消费了其输出时才可包含**；否则 `adjacent_system_referenced` 必须为 `false`。
- **Control State 仅保存控制面位置信息**（Scope/Function/Route）；业务真相必须保存在 `Repo` 与 `Worktrack` 的正式文档中，禁止写入 Control State。
- **git hash 一致仅授权跳过重复刷新和重复文档追平**；首次验证和 Gate 裁决在任何情况下都不可跳过。
- **分支环境守卫（Branch Environment Guard）**：任何会改变代码状态的 Function 必须先匹配合法 `branch_context`。RepoScope baseline mutation 在 `baseline_branch`；Milestone-derived Worktrack 初始化在 `active_milestone_branch`；Worktrack 实施在 `worktrack_branch`；close/refresh 使用 Worktrack Contract 的 `closeout_target_ref` / `checkpoint_base_ref`。只读 Observe 可在不匹配上下文继续但必须标记 warning；会改变状态的 Function 在不匹配上下文必须阻断。合法恢复路径只能切换到 control-state 或 Worktrack Contract 指定的目标分支，不得写死默认值或从当前分支名推断。

---

## 十六、资源

使用当前 `Harness Control State`、当前 Scope 所需的正式产物，以及下游技能的结构化输出作为本轮的权威依据。

判断下一次合法继续推进是否被允许时，应优先使用下游结构化输出，而不是本地叙述性摘要。

三轴参考：
- `Scope` 回答"在什么层上控制"
- `Function` 回答"控制器此刻在做什么"
- `Artifact` 回答"控制器依赖什么正式对象"

---

## 十七、结构化输出字段约定

Inside the result, include at least these fields or equivalents:

- `current_scope`
- `artifacts_read`
- `status_or_verdict`
- `allowed_next_routes`
- `recommended_next_route`
- `continuation_ready`
- `recommended_next_scope`
- `recommended_next_action`
- `continuation_decision`
- `stop_conditions_hit`
- `approval_required`
- `needs_approval`
- `config_hydration_gaps`
- `persistent_authority_updates`
