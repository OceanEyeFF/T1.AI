---
name: close-worktrack-skill
description: 当 Harness 处于 WorktrackScope.closing，且需要一轮限定范围的收尾处理来处理合并请求、合并、清理与代码仓库刷新交接，同时不能悄悄越过审批边界时，使用这个技能。
---

# 关闭工作追踪技能

## 概览

本技能实现 `WorktrackScope.Close` 状态转移算子，对应 Harness 控制回路中的**关闭并交接**阶段。它负责处理工作追踪的收尾路径（PR → merge → cleanup → repo refresh 交接），完成验证过的状态到 repo 级真相层的回写，闭合控制回路。

当 `Harness` 已经持有一个可合并或已合并的 `Worktrack`，并且需要在 `WorktrackScope.closing` 内完成一轮限定范围收尾时，使用这个技能。

这个技能会为一次 `通用高能力模型` `SubAgent` 运行打包最小收尾上下文，判断当前收尾阶段，并返回结构化的收尾结果与明确的 `代码仓库刷新交接`，而不是静默推进合并、分支清理或代码仓库级回写。

## 何时使用

当当前问题不是"如何修复或裁决这个工作追踪"，而是"如何在不跨越权限边界的前提下完成它的收尾路径"时，使用这个技能：

- 当前 `Worktrack` 已经有允许进入收尾处理的 `关卡证据` 结果
- 系统需要判断本轮处于 `合并请求`、`合并`、`清理分支` 还是 `代码仓库刷新交接`
- 收尾状态可能只完成了一部分，例如 `合并请求已开但未合并` 或 `已合并但清理仍在等待`
- `Harness` 需要一份限定范围报告，说明哪些收尾动作已完成、哪些仍需审批、哪些应回交给 `代码仓库范围`
- 结果必须停留在收尾处理范围内，不能漂移回实现、关卡裁决或代码仓库刷新执行

## 工作流

1. 载入最小 `WorktrackScope` 产物，以及与收尾有关的当前分支、合并请求和合并状态证据。
2. 为一轮限定范围的 `通用高能力模型` `SubAgent` 构建一份 `关闭工作追踪任务简报` 和一份 `关闭工作追踪信息包`。
3. 从 `Worktrack Contract` 读取 closeout target 与 checkpoint 对比基准。`baseline_branch` 是 servo-managed final baseline；`branch_source_ref` 是本 Worktrack 分支来源；`integration_target_ref` / `closeout_target_ref` 是本轮 PR target、merge target 与 checkpoint 基准的唯一合法来源。Milestone-derived worktrack 默认合回 active Milestone branch，而不是直接合回 servo-managed baseline。PR target、merge target 和 checkpoint 基准不得从当前分支名或写死默认分支名推断。
4. 判断当前收尾阶段：
   - `准备合并请求`
   - `合并请求已开`
   - `准备合并`
   - `已合并`
   - `准备清理`
   - `基线固化 / checkpoint`
   - `准备代码仓库刷新`
   - `收尾被阻塞`
5. 将收尾结果拆分为：
   - 本轮已完成的动作
   - 仍在等待程序员审批或外部合并状态的动作
   - 只有在确认合并后才安全的清理项
   - 应交给 `代码仓库刷新技能` 的已验证材料
6. 在一轮限定范围收尾后停止，并返回一份固定格式的 `关闭工作追踪报告` 与一份 `代码仓库刷新交接`。

## 收尾约定

每次运行这个技能时，都使用同一套限定范围约定格式。

### 关闭工作追踪任务简报

- `触发条件`
- `目标`
- `当前工作追踪`
- `当前收尾阶段`
- `范围内`
- `范围外`
- `权限边界`
- `需要审批`
- `完成信号`

### 关闭工作追踪信息包

- `当前工作追踪状态`
- `工作追踪约定摘要`
- `baseline_branch`: 从 Worktrack Contract 读取的 servo-managed final baseline
- `branch_source_ref`: 从 Worktrack Contract 读取的 Worktrack branch 来源
- `worktrack_branch`: 从 Worktrack Contract 读取的 Worktrack 执行分支
- `integration_target_ref`: 从 Worktrack Contract 读取的集成目标
- `closeout_target_ref`: 从 Worktrack Contract 读取的 PR target / merge target / checkpoint 基准
- `checkpoint_base_ref`: 从 Worktrack Contract 读取的 checkpoint 对比基准
- `关卡判定摘要`
- `合并请求状态`
- `合并状态`
- `分支清理状态`
- `已接受变更摘要`
- `残留风险`
- `所需上下文`

### 代码仓库刷新交接

- `已关闭工作追踪`
- `closeout_record`
  - `worktrack_id`
  - `branch`
  - `base_ref`
  - `head_ref`
  - `merge_commit`
  - `pr`
  - `files_changed`
  - `acceptance_result`
  - `gate_verdict`
  - `evidence_refs`
  - `decision_refs`
  - `docs_updated`
  - `snapshot_refreshed`
  - `backlog_updated`
  - `cleanup_done`
  - `remaining_risks`
  - `next_repo_scope_action`
- `基准分支`
- `baseline_branch`
- `branch_source_ref`
- `worktrack_branch`
- `integration_target_ref`
- `closeout_target_ref`
- `checkpoint_base_ref`
- `PR target`
- `merge target`
- `已接受变更摘要`
- `验证结果`
- `收尾状态`
- `可回写候选`
- **节点策略**
  - `node_type`: 从 Worktrack Contract 读取的节点类型
  - `expected_baseline_form`: Contract 中的 `baseline_form`
  - `merge_required`: Contract 中的 `merge_required`
  - `actual_baseline_form`: 本轮实际形成的 checkpoint 形式
  - `checkpoint_policy_match`: yes / no / deferred
- **基线追溯**
  - `checkpoint_type`: commit / tag / annotated-tag / stash / explicit-declaration
  - `checkpoint_ref`: SHA 或 tag 名称或 stash ref
  - `if_no_commit_reason`: 如果不形成 commit，必须显式说明原因
  - `alternative_traceability`: 替代追溯物（如 PR URL、diff patch 引用、报告路径）
- `残留风险`
- `推迟项`
- `审批请求`

### 基线固化策略（按节点类型）

根据 `Worktrack Contract` 中的 `Node Type` 选择基线固化方式：

优先级：`Worktrack Contract` 中显式填写的 `baseline_branch`、`branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref`、`checkpoint_base_ref`、`baseline_form`、`merge_required`、`if_interrupted_strategy` 优先；下表只作为节点类型默认值。若 PR target、merge target 或实际 checkpoint 与 contract policy 不一致，必须在代码仓库刷新交接中标记 `checkpoint_policy_match: no` 并请求审批。

| 节点类型 | 默认 baseline_form | 固化动作 |
|---------|-------------------|---------|
| `feature` | commit-on-feature-branch | PR → merge 到 `closeout_target_ref` → git commit 基线；Milestone final acceptance 再合回 `baseline_branch` |
| `refactor` | commit-on-refactor-branch | PR → merge 到 `closeout_target_ref` → git commit 基线；Milestone final acceptance 再合回 `baseline_branch` |
| `bugfix` | commit-on-bugfix-branch | PR → merge 到 `closeout_target_ref` → git commit 基线；Milestone final acceptance 再合回 `baseline_branch` |
| `docs` | commit-on-docs-branch | PR → merge 到 `closeout_target_ref` → git commit 基线；Milestone final acceptance 再合回 `baseline_branch` |
| `config` | commit-on-config-branch | PR → merge 到 `closeout_target_ref` → git commit 基线；Milestone final acceptance 再合回 `baseline_branch` |
| `test` | commit-on-test-branch | PR → merge 到 `closeout_target_ref` → git commit 基线；Milestone final acceptance 再合回 `baseline_branch` |
| `research` | annotated-tag-or-report | 不 merge → git annotated tag + 报告文件 → 标记替代追溯物 |

如果 `Node Type` 未定义，fallback 到最保守策略：要求 commit 基线，否则显式声明替代追溯物。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- `关卡通过` 的唯一合法含义是允许进入收尾阶段。合并、删除分支或更新代码仓库真相的授权必须通过显式审批获得，`关卡通过` 不是这些操作的隐式授权。
- 仅当审批和状态确认已完整获得时，执行 `合并`、`清理分支` 或代码仓库回写才合法；否则必须保持等待并暴露缺失的审批项。
- `合并请求已开`、`已合并` 和 `代码仓库刷新已完成` 是三个独立且递进的状态。`合并请求已开` 不能等同于 `已合并`，`已合并` 也不能等同于 `代码仓库刷新已完成`——每个状态必须独立验证。
- 仅当合并状态与回退路径安全性已明确后，清理分支才合法；否则必须保持分支等待确认。
- 在返回代码仓库刷新交接前，必须确认当前工作树是否已形成可追溯基线。
- 如果工作成果未形成 git commit（或 tag、annotated stash），必须显式记录不 commit 的原因及替代追溯物。
- 可安全回写的状态的判定条件是具备完整的基线追溯信息。缺少基线追溯信息的交接不能被视为可安全回写的状态。
- 已完成动作、待审批项和代码仓库刷新交接的唯一合法呈现形式是结构化字段。压缩成模糊收尾叙述的行为必须被阻断。
- Worktrack Close 后回到 RepoScope 观察的唯一合法路径是经过 `repo-refresh-skill`。跳过 `repo-refresh-skill` 直接返回的行为必须被阻断。Repo 慢变量必须通过 `repo-refresh-skill` 从已验证证据刷新；repo snapshot 在 merge 后自动更新的假设禁止作为跳过刷新步骤的依据。
- 仅当文档追平检查已完成或已显式安排时，结束涉及版本、release、deploy 或 VCS baseline 的轮次才合法；否则必须调用或显式安排 `doc-catch-up-worker-skill`。
- hash 存储的唯一合法时机是刷新/追平成功完成后。在刷新前或刷新失败时写入 hash 的行为必须被阻断。
- 闭环终点的判定条件是 `merge → refresh repo snapshot → cleanup → return RepoScope` 全部完成。`PR 已发出` 只是中间状态，不能被视为闭环终点。

## 输出协议

- 先生成尽可能长且完整的 `关闭工作追踪报告`，确保所有收尾信息被记录
- 然后从完整报告中提取 `Control Signal` 层（影响下一动作决策的关键结论）
- `代码仓库刷新交接` 的基线追溯字段必须显式填充。省略基线追溯字段的行为必须被阻断
- `closeout_record` 不单独写入新的长期 Worktrack artifact；它必须作为 `关闭工作追踪报告` 与 `代码仓库刷新交接` 的结构化 section 输出，并由 repo-refresh 后续写入 repo 级 backlog / snapshot。省略 `decision_refs` 或闭环状态字段的行为必须显式说明原因
- `代码仓库刷新交接` 必须同时填充节点策略字段，并说明 expected baseline 与 actual checkpoint 是否匹配
- 重复性上下文（如 worktrack contract 摘要）的唯一合法呈现形式是文件路径引用 `[.servo/worktrack/contract.md#section]`。内联全文的行为禁止发生
- 如果某个字段无实质内容，唯一合法行为是使用 `N/A` 或省略。用占位符填充的行为必须被阻断
- `Supporting Detail` 保留完整内容，只用于后续查阅，不纳入传递上下文

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `关闭工作追踪报告`：

- `收尾触发条件`
- `当前收尾阶段`
- `已执行的收尾动作`
- `权限检查与待审批项`
- `代码仓库刷新交接`
- `建议下一范围`
- `程序员审查请求`

结果中至少应包含以下字段或等价表达：

- `子代理模型`
- `收尾触发条件`
- `当前工作追踪`
- `收尾前阶段`
- `收尾后阶段`
- `关卡判定`
- `合并请求状态`
- `baseline_branch`
- `branch_source_ref`
- `worktrack_branch`
- `integration_target_ref`
- `closeout_target_ref`
- `checkpoint_base_ref`
- `PR target`
- `merge target`
- `合并状态`
- `清理状态`
- `已执行动作`
- `待审批动作`
- `决定性证据`
- `残留风险`
- `代码仓库刷新就绪`
- `代码仓库刷新交接`
- `closeout_record`
- `节点类型`
- `基线策略`
- `checkpoint_policy_match`
- `建议下一范围`
- `建议下一动作`
- `需要程序员审批`
- `如何审查`

## 资源

使用本轮收尾所需的最小 `WorktrackScope` 产物，以及当前分支、合并请求、合并状态和代码仓库刷新交接上下文。
