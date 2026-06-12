---
name: review-evidence-skill
description: 当 Harness 处于工作追踪范围.验证中，且需要一轮限定范围的审查证据流程来收集并综合审查发现、但不输出最终关卡判定结果时，使用这个技能。
---

# 审查证据技能

## 概览

本技能实现 `WorktrackScope.Verify` 算子的 `implementation` lane（实现校验面），对应 Harness 控制回路中的**收集证据**阶段。它负责收集代码审查维度的证据，为 `gate-skill` 的 implementation-gate 提供输入。它与 `test-evidence-skill`（validation lane）和 `rule-check-skill`（policy lane）共同构成 Verify 的三个正交校验面。

当 `Harness` 需要当前 `工作追踪` 的 `关卡证据` 中的审查维度，但还不需要最终关卡判定时，使用这个技能。

这个技能会使用专用 `通用高能力模型` `子代理` 执行一轮限定范围审查证据，打包本轮最小审查上下文，收集代码审查与结构风险信号，并返回一个供后续关卡综合使用的标准化审查维度封套。

本技能按 `review_profile` 选择审查 lanes，而不是所有变更固定四路。运行时 profile 规则随本技能分发如下：

- `light`：`static-semantic-review`
- `standard`：`static-semantic-review` + `test-review`
- `risky`：`static-semantic-review` + `test-review` + `project-security-review`
- `deep`：四路完整覆盖

默认选择：docs-only 小修用 `light`；普通 canonical skill/docs/test 修改用 `standard`；dispatch、authority、path governance、adapter/deploy 安全边界用 `risky`；control-state、gate、installer/publish、destructive action 用 `deep`。Source-side authoring trace: `docs/harness/artifact/worktrack/gate-evidence.md`。

四个可用审查 SubAgent lanes 为：

- `static-semantic-review`：静态语义解释 review，解释 diff 的真实语义、状态转移、边界语义和 operator-facing 行为变化。
- `test-review`：测试 review，审查验收覆盖、回归覆盖、测试可信度、验证命令与缺失测试风险。
- `project-security-review`：符合项目情景的 security review，结合本仓库 deploy / adapter / Harness 权限边界，审查凭据、发布、路径、外部输入、破坏性动作和安全默认值。
- `complexity-performance-review`：代码复杂度和性能 review，审查复杂度、重复工作、I/O、缓存、资源使用、跨平台成本和可维护性风险。

如果运行时不能真实并行委派，必须显式记录 `runtime fallback`、`permission blocked` 或 `dispatch package unsafe`，并在同一份审查证据中保留所选 lanes 的覆盖状态；唯一合法行为是在当前载体内完成所选 lane 的覆盖并显式记录 fallback 原因；把当前载体内的串行分析伪装成已创建 SubAgent 的行为必须显式暴露为 `runtime fallback`。

它会在最终 `通过/软失败/硬失败/阻塞` 关卡判定之前停止，并应用噪声控制边界，避免低严重度的审查残留持续膨胀为新的伪阻塞项。

## 何时使用

当当前问题不是"整个工作追踪是否应该通过关卡"，而是"这次变更当前掌握了哪些审查证据"时，使用这个技能：

- 收集当前 `工作追踪范围.验证中` 轮次的审查维度
- 根据限定范围 `工作追踪约定` 总结代码审查发现
- 把差异、结构和静态审查信号综合成一份审查证据切片
- 在问题扩散前，把可执行发现与低严重度残留风险分开
- 把重复出现或由边界驱动的症状标记为可能的上游约束问题
- 明确说明已有的审查覆盖、仍然缺失的部分，以及所需后续动作
- 为 `关卡技能`、`恢复工作追踪技能` 或程序员审查返回审查证据

## 工作流

1. 确认这是一轮限定范围审查证据，而不是最终关卡判定、调度或执行分派。
2. 载入本轮所需的最小 `工作追踪范围` 产物和当前审查输入。
3. 读取或推导 `review_profile`，并记录选择理由。若缺失，按变更类型保守选择：docs-only 小修 `light`，普通 skill/docs/test 修改 `standard`，dispatch/authority/path safety `risky`，control-state/gate/installer/publish/destructive action `deep`。
4. 为所选 review lanes 构建同源但 lane-specific 的 `审查证据任务简报` 和 `审查证据信息包`。
5. 若运行时支持真实委派且权限边界允许，则并行分派所选审查 SubAgent；否则记录明确 fallback 原因，并用同一 lane 结构在当前载体内完成覆盖。
6. 在综合之前，先归类当前审查输入与所选 review 输出的时效性：
   - `新鲜`
   - `复用但新鲜`
   - `混合`
   - `过期`
   - `未知`
7. 只收集并综合审查维度：
   - 差异与变更摘要审查信号
   - 结构或架构审查信号
   - 现有代码审查评论或内联发现
   - 对审查质量重要的静态审查发现
   - 代码性能 review 信号，包括明显的复杂度、重复工作、I/O 或资源使用风险
   - Repo 架构 review 信号，包括层级边界、模块归属、依赖方向和长期演进风险
   - 代码安全 review 信号，包括权限边界、注入面、敏感数据、外部输入和破坏性动作风险
   - 代码质量 review 信号，包括可维护性、可读性、错误处理、恢复路径和 operator-facing 语义
   - 测试 review 信号，包括验收覆盖、回归覆盖、验证可信度和缺失测试风险
8. 在打包结果前应用审查分诊：
   - 让可执行发现聚焦于验收、验证可信度、约定完整性、恢复路径风险，或面向操作员的语义漂移
   - 让低严重度残留作为代表性项目加 `残留风险`，而不是一个无限制的动作队列
   - 把重复或边界驱动的症状标记为 `可能存在上游约束问题`
9. 将所选 lane 输出综合成一份 `审查证据报告`，并附带一份供关卡接收使用的审查维度封套。
10. 在输出最终关卡判定结果前停止。

## 审查分诊规则

- 只有当某个审查项威胁到验收、验证可信度、约定完整性、恢复路径安全，或面向操作员的语义时，才把它提升进 `发现`。
- 对于不触发上述条件、也没有可信放大链路的低严重度项，包括 `P2/P3`，`发现` 中最多保留三个代表项，其余折叠进 `残留风险`。
- 仅当某个动作是恢复验收覆盖、恢复路径安全、面向操作员的语义，或修复破损约定边界所必需时，为低严重度残留创建新的 `后续动作` 才合法；否则必须将该项折叠进 `残留风险`。
- 如果相同的审查模式在多个文件、轮次或评论中重复出现，或者明显依赖尚未解决的约定、范围或边界定义，就把代表性发现标记为 `可能存在上游约束问题：真`，并在 `上游约束信号` 下总结。
- `后续动作` 只用于能解除关卡综合阻塞的限定范围下一步动作，而不是装下所有审查偏好或清理想法的桶。

## 审查证据约定

每次运行这个技能时，都使用同一套限定范围约定格式。

### 审查证据任务简报

- `维度编号`
- `证据轮次`
- `review_lane_id`
- `review_lane_goal`
- `审查目标`
- `目标`
- `范围内`
- `范围外`
- `审查重点`
- `审查维度覆盖`
- `节点类型`
- `适用 gate_criteria`
- `约束`
- `验收参考`
- `完成信号`

### 审查证据信息包

- `输入产物`
- `时效性`
- `review_profile`
- `selected_review_lanes`
- `四路 SubAgent lane`（仅 `deep` 或需要完整覆盖时）
- `当前工作追踪状态`
- `工作追踪约定摘要`
- `节点策略`
- `变更摘要`
- `差异或补丁引用`
- `现有审查输入`
- `静态或结构信号`
- `性能/架构/安全/质量/测试审查信号`
- `已知风险`
- `所需上下文`
- `缺失证据`

### 审查证据维度

- `维度编号`
- `证据轮次`
- `review_profile`
- `selected_review_lanes`
- `四路 SubAgent 覆盖`（仅 `deep` 或需要完整覆盖时）
- `四路 SubAgent 输出摘要`
- `输入产物`
- `时效性`
- `维度判定结果`
- `置信度`
- `置信度理由`
- `发现`
- `严重度映射`
- `覆盖评估`
- `五类审查覆盖`
- `残留风险`
- `已应用低严重度吸收`
- `低严重度吸收理由`
- `上游约束信号`
- `缺失证据`
- `后续动作`
- `已准备好进入关卡`

### Review lanes

每次 review evidence 轮次应明确记录所选 lane 的执行状态、输入范围、输出摘要、发现和缺失证据；`deep` profile 必须保留四路 lane：

- `static-semantic-review`
  - 关注：diff 语义、状态转移、隐式行为变化、边界语义、operator-facing 语义。
  - 输出：语义解释、行为风险、架构或合同漂移信号。
- `test-review`
  - 关注：验收覆盖、回归覆盖、测试可信度、验证命令、缺失测试风险。
  - 输出：测试覆盖判断、缺失验证、测试证据可信度。
- `project-security-review`
  - 关注：仓库上下文内的权限边界、路径写入、发布准入、凭据、外部输入、破坏性动作和安全默认值。
  - 输出：情景化安全发现、安全非适用说明、残留安全风险。
- `complexity-performance-review`
  - 关注：复杂度、重复工作、I/O、缓存、资源使用、跨平台行为和维护成本。
  - 输出：复杂度/性能发现、可维护性风险、必要的简化建议。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- 必须先确定 `review_profile`，再选择 review lanes；不得对低风险小改默认强制四路 review。
- 当 `review_profile: deep` 且运行时支持真实 SubAgent 委派、权限边界允许时，必须并行分派四个 review SubAgent；降级成单个泛化 review 的行为必须显式暴露为 `runtime fallback`。
- 所选 review lane 必须分别保留输入范围、输出摘要、覆盖状态和缺失证据；把结果压成无法追溯的一段综合意见的行为必须显式暴露并标记为覆盖不足。
- 审查证据至少应显式覆盖五类 review 面：代码性能、Repo 架构、代码安全、代码质量、测试。若某一类不适用于当前 docs-only 或 policy-only 变更，应写明 `不适用` 与理由，而不是静默省略。
- 输出只能分别呈现原始发现、综合后的审查判定与后续动作三个独立段落；把三者混成一段模糊摘要的行为禁止出现在审查证据的输出中。
- 仅当低严重度发现已经实质威胁验收、恢复、面向操作员的语义或约定完整性时，将其扩展成新的 `后续动作` 才合法；否则必须将其折叠进 `残留风险`。
- 唯一合法行为是 `发现` 中最多保留三个低严重度代表项；超过三个时必须将其余项聚合进 `残留风险`。
- 唯一合法行为是将重复或边界驱动的症状标记为 `可能存在上游约束问题` 并在 `上游约束信号` 中显式暴露；未标记状态必须返回 blocked。
- 证据时效性标签必须与实际验证时间一致；过期输入仅可作为过期证据出现在输出中。
- 唯一合法行为是输出 `置信度` 时附带具体的 `置信度理由`；缺少 `置信度理由` 时 `置信度` 字段必须留空或标记为 `未评估`。
- 低严重度吸收机制的输出只能是代表性风险摘要；后续动作列表的行为禁止出现在低严重度吸收的输出中。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `审查证据报告`：

- `审查目标`
- `审查证据摘要`
- `发现与严重度`
- `时效性与置信度`
- `覆盖与置信度`
- `关卡证据审查切片`
- `返回 Harness`

结果中至少应包含以下字段或等价表达：

- `子代理模型`
- `review_profile`
- `selected_review_lanes`
- `四路 SubAgent 覆盖`
- `static-semantic-review`
- `test-review`
- `project-security-review`
- `complexity-performance-review`
- `维度编号`
- `证据轮次`
- `审查目标`
- `审查重点`
- `五类审查覆盖`
- `变更摘要`
- `使用的审查输入`
- `输入产物`
- `时效性`
- `维度判定结果`
- `审查判定结果`
- `发现`
- `严重度映射`
- `覆盖评估`
- `置信度`
- `置信度理由`
- `残留风险`
- `已应用低严重度吸收`
- `低严重度吸收理由`
- `上游约束信号`
- `缺失证据`
- `后续动作`
- `已应用低严重度截断`
- `已准备好进入关卡`
- `已准备好进入关卡综合`
- `需要额外审查`
- `如何审查`

## 资源

使用限定范围差异、当前 `工作追踪约定`、当前审查输入及其时效性依据，以及回答审查问题所需的最小额外相邻系统上下文。
