# 代码仓库 Overview Fallback 模式附录

只有当 `代码仓库下一步技能` 的默认 `下一步方向` 模式与 `优先级重构/矛盾分析` 模式都无法找到可信的可更新内容时，才使用这个 `overview fallback` 附录。

它借鉴 `project-dialectic-planning-skill` 的全局基本面分析方法，但范围更窄：本模式只为 Harness 提供未来 worktrack 候选建议，不创建工作追踪，不改变 Harness 控制状态，不改变目标，不把推断写成已验证事实。

## 触发条件

必须同时满足：

- 默认模式无法给出可信的 `进入工作追踪`、`刷新代码仓库状态` 或 `保持并观察` 之外的具体下一步。
- 优先级重构模式也只能得到空泛判断、重复旧结论，或缺少足够信息。
- 当前 repo truth 没有显式阻止继续分析。
- 本轮目标是提高未来可用 worktrack 的发现效率，而不是扩大当前 worktrack 范围。

## 最小输入

- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- 当前 `Harness Control State`
- 最近一次完成或阻塞的 worktrack 摘要
- 已知验证证据和治理检查结果
- 可选：当前 operator 约束、交付压力、发布窗口或试用反馈

缺失信息必须写入 `overview_missing_inputs`，不能靠猜测补齐。

## 分析步骤

1. 用一句话重述当前 repo 目标和当前阶段。
2. 区分 `Facts / Inferences / Unknowns`。
3. 从以下维度快速扫描 repo 基本面（优先按 Milestone 分组）：
   - 当前 active milestone 的剩余 worktrack（优先完成）
   - Pipeline 中下一个 planned milestone 的可激活条件
   - 产品/用户价值
   - Harness 控制闭环
   - deploy / installer / release
   - docs truth boundary
   - review / verify / governance
   - cross-platform operator experience
4. 找出当前最可能限制下一批 worktrack 价值的一个主要矛盾。
5. 给出最多 5 个未来 worktrack 候选，每个候选必须包含：
   - `candidate_id`
   - `title`
   - `why_now`
   - `served_contradiction`
   - `suggested_node_type`
   - `acceptance_hint`
   - `risk`
   - `first_small_slice`
5b. 候选 worktrack 应优先从 active milestone 的 `worktrack_list` 派生；若无 active milestone，从 pipeline 中下一个可激活的 planned milestone 派生。每个候选关联 `target_milestone_id`（如有）。
6. 从候选中只推荐一个 `top_candidate`。优先选择能推进当前 active milestone 完成的 worktrack；若无 active milestone，优先选择能激活 pipeline 中最高优先级 milestone 的 worktrack。
7. 将推荐折回正常 `代码仓库下一步判定`：通常是 `进入工作追踪` 或 `保持并观察`，而不是直接执行。

## 输出字段

- `mode: overview-fallback`
- `overview_trigger_reason`
- `repo_goal_restatement`
- `facts`
- `inferences`
- `unknowns`
- `overview_scan`
- `primary_contradiction`
- `candidate_worktracks`
- `top_candidate`
- `top_candidate_reason`
- `overview_missing_inputs`
- `recommended_repo_action`
- `recommended_next_route`
- `approval_required`
- `continuation_blockers`

## 约束

- 不要输出大型战略报告。
- 不要把候选 worktrack 写进 `.servo/worktrack/*`。
- 不要把 overview 候选当成已经批准的执行范围。
- 不要绕过 active route boundary；如果当前配置不允许 `进入工作追踪`，推荐必须降级为 `保持并观察` 并把候选作为建议返回。
- 每个候选必须能收敛到一个小的、可验证的第一切片。
