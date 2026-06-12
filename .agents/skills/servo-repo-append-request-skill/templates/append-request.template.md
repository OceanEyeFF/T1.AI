# Append Request 路由结果模板

> 使用方式：在 `repo-append-request-skill` 需要整理 append-feature / append-design / append-milestone 分类与路由结果时，使用本模板组织输出。它不进入 `.servo/` 路径，除非后续 Harness 明确把本次 intake 结果持久化为控制 artifact。

## 元数据

- 请求编号：
- 提出时间：
- 分析时间：
- mode：append-feature / append-design / append-milestone
- 分类结果：goal change / new milestone / new worktrack / scope expansion / design-only / design-then-implementation
- 分类置信度：high / medium / low

## 原始追加请求

- 请求文本：
- 请求来源：
- 用户显式授权：

## 分类理由

- 命中规则：
- 未命中规则：
- 关键事实：
- 关键推断：
- 未知项：

## 目标影响

- 是否改变 Goal Charter：
- Engineering Node Map 影响：
- 系统不变量影响：
- 是否需要 goal change control：

## 活跃 worktrack 影响

- 是否存在活跃 worktrack：
- 当前 worktrack 范围摘要：
- 是否越过当前范围：
- 是否属于验收缺口：
- scope expansion 风险：

## Milestone Pipeline 影响

- 是否属于 milestone 级追加：
- suggested_milestone_action：create / activate / append_worktracks / upsert / N/A
- 目标 milestone_id：
- milestone brief boundary：
- 是否需要 init-milestone-skill：
- milestone approval boundary：

## 路由判定

- 建议下一路由：
- 建议下一范围：
- suggested_node_type：
- suggested_node_type_reason：
- 路由边界来源：

## 设计 / 实现阶段

- design_phase：
- implementation_phase：
- 阶段 gate：
- 后续进入实现条件：

## 权限边界

- approval_required：
- approval_scope：
- approval_reason：
- programmer_authority_needed：

## 最小缺失信息

- 缺失信息：
- 缺失信息阻塞的判断：

## 返回 Harness

- continuation_ready：
- continuation_blockers：
- recommended_next_route：
- recommended_next_scope：
- suggested_milestone_action：
- 不执行声明：

填写规则：

- 如果 `approval_required` 为 true 且输入事实没有明确审批结果，`continuation_ready` 填 false，并在 `continuation_blockers` 写明待审批项。
- 如果存在阻塞性缺失信息，`continuation_ready` 填 false，并在 `continuation_blockers` 写明缺失信息。
- 只有无待审批项、无阻塞性缺失信息时，`continuation_ready` 才可填 true；即便如此，本结果也只返回路由，不执行后续 route。
