# 分支任务文档索引

## 目的

本目录用于按分支维护任务文档，避免：

- 所有任务都堆在同一份总文档里；
- 分支状态、边界和后续动作混在一起；
- 入口文档承载过多执行细节。

当前按 4 条工作分支分别维护：

- [develop.md](develop.md)
- [feature_model_3d_5d_10d_head.md](feature_model_3d_5d_10d_head.md)
- [feature_model_d1_research.md](feature_model_d1_research.md)
- [feature_execution_layer_v2.md](feature_execution_layer_v2.md)

专项治理清单：

- [develop_governance_backlog_20260311.md](develop_governance_backlog_20260311.md) — develop 治理期 4 项核心专题总清单
- [g1_validation_plan_20260311.md](g1_validation_plan_20260311.md) — G1 Checklist 验证方案（验证 execution-layer-v2）

## 维护规则

- `develop`：只记录当前集成基线必须做的事情，重点放在架构基线、审核门禁和分支吸收规则，不承接细节研究主工作流。
- 功能/研究分支：只记录该分支自己的边界、待办和退出条件。
- 已经同步进 `develop` 的分支，不再继续追加长期任务，只保留：
  - 已完成事项；
  - 归档说明；
  - 若有遗留动作，明确迁移到 `develop`。

## 状态标记

- `[ ]` 未开始
- `[-]` 进行中
- `[x]` 已完成
