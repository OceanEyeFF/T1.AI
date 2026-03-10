# 文档导航

本仓库文档按“颗粒度”组织，而不是按时间状态组织。

## 当前建议阅读顺序（2026-03）

如果目标是接着当前主线继续开发，建议按下面顺序进入：

1. [../README.md](../README.md)
2. [../NEXT_STEPS.md](../NEXT_STEPS.md)
3. [../ROADMAP.md](../ROADMAP.md)
4. [modules/model_line_boundaries_1d_vs_3510d_20260309.md](modules/model_line_boundaries_1d_vs_3510d_20260309.md)
5. [research/1d_independent_model_execution_strategy_20260309.md](research/1d_independent_model_execution_strategy_20260309.md)
6. [interfaces/README.md](interfaces/README.md)

原因是当前真正需要先读清楚的，不只是目录结构，而是：

- 主线模型固定为 `3d/5d/10d`
- 主线推荐层默认把 `3d/5d/10d` 三头聚合为单一 `alpha_score`
- `1d` 只作为独立研究线
- 执行层是当前第一优先级

## 颗粒度规则

- `overview`：回答“项目现在在做什么、未来要去哪里”。
- `modules`：回答“系统如何分层、模块如何协同、模型线边界怎么划”。
- `interfaces`：回答“字段、协议、约束、边界具体是什么”。
- `research`：回答“为什么这样做、实验怎么验证、当前结论是什么”。
- `archive`：回答“哪些内容已经退场，以及为什么退场”。

完整文件清单见 [INVENTORY.md](INVENTORY.md)。

## 推荐入口

1. [overview/README.md](overview/README.md)
2. [modules/README.md](modules/README.md)
3. [interfaces/README.md](interfaces/README.md)
4. [research/README.md](research/README.md)
5. [archive/README.md](archive/README.md)

## 根目录文档定位

- [../README.md](../README.md)：项目总入口
- [../NEXT_STEPS.md](../NEXT_STEPS.md)：当前执行入口
- [../ROADMAP.md](../ROADMAP.md)：长期路线入口

## 使用建议

- 需要确认当前开发优先级时，从 [../NEXT_STEPS.md](../NEXT_STEPS.md) 开始。
- 需要做主线模型开发前，先读 [modules/model_line_boundaries_1d_vs_3510d_20260309.md](modules/model_line_boundaries_1d_vs_3510d_20260309.md)。
- 需要确认主线聚合输出与推荐接口时，补读 [modules/system_io_and_architecture_spec.md](modules/system_io_and_architecture_spec.md) 和 [research/多头输出和数据切分.md](research/%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md)。
- 需要推进 `1d` 研究前，先读 [research/1d_independent_model_execution_strategy_20260309.md](research/1d_independent_model_execution_strategy_20260309.md)。
- 需要确认协议、字段和交易约束时，转到 [interfaces/README.md](interfaces/README.md)。

## 维护约定

- 新文档先决定颗粒度，再决定时间属性。
- 当前主线发生变化时，应先更新根目录入口文档，再更新对应分层导航。
- 研究结论如果已成为默认口径，必须同步回 `overview` / `modules` / `interfaces` 层，而不是只停留在研究层。
