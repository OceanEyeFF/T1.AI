# 目标变更分析报告模板

> 使用方式：在 `修改 Repo 目标技能` 需要整理一轮目标级变更分析报告时，使用本模板组织输出。它不进入 `.servo/` 路径。

## 元数据

- 请求编号：
- 提出时间：
- 分析时间：
- 变更幅度：minor / moderate / major

## 变更请求

- 请求变更：
- 变更理由：

## 目标差异

- 当前目标（摘要）：
- 请求后目标（摘要）：
- 核心差异：

## 影响分析

- 基准影响：
- 活跃工作追踪影响：
- Engineering Node Map 影响：
- 节点类型兼容性：
- 受威胁的不变条件：
- 证据或缺口：

## Engineering Node Map 差异

- 新增节点类型：
- 删除节点类型：
- 变更节点类型：
- Node Type Registry 差异：
- This Goal's Node Types 差异：
- Node Dependency Graph 差异：
- Default Baseline Policy 差异：

## 节点策略差异

- merge_required 变化：
- baseline_form 变化：
- gate_criteria 变化：
- if_interrupted_strategy 变化：
- 活跃 worktrack 需重新绑定节点类型：
- 需重新初始化 worktrack：

## 权限边界

- 需要审批：
- 审批范围：
- 审批理由：

## 建议决策

- 建议决策：接受 / 暂缓 / 拒绝 / 重定向
- 决策理由：

## 执行确认

- 是否获得用户确认：
- 确认时间：
- 实际改写的文件：
- 后续必要动作：
