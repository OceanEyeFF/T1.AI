# Modules 文档

这一层放系统分层、模块边界与模块协同方式。

适合在这里回答的问题：

- 系统有哪些层
- 数据、训练、执行、调度这些模块怎么连接
- 哪些代码应该共用，哪些必须按模型线拆开

## 推荐阅读顺序

1. [model_line_boundaries_1d_vs_3510d_20260309.md](model_line_boundaries_1d_vs_3510d_20260309.md)
2. [system_io_and_architecture_spec.md](system_io_and_architecture_spec.md)
3. [stock_pool_module_baseline_20260311.md](stock_pool_module_baseline_20260311.md)
4. [stock_pool_registry_baseline_20260311.md](stock_pool_registry_baseline_20260311.md)
5. [stock_pool_module_development_plan_20260311.md](stock_pool_module_development_plan_20260311.md)
6. [production_scheduler.md](production_scheduler.md)
7. [data_sources.md](data_sources.md)
8. [news_sources.md](news_sources.md)

## 文档分组

### 模型线边界

- [model_line_boundaries_1d_vs_3510d_20260309.md](model_line_boundaries_1d_vs_3510d_20260309.md)：`1d` 独立线与 `3d/5d/10d` 主线的代码边界
- [system_io_and_architecture_spec.md](system_io_and_architecture_spec.md)：系统 I/O、主线 `alpha_score` 聚合输出与架构分层

### 股票池模组

- [stock_pool_module_baseline_20260311.md](stock_pool_module_baseline_20260311.md)：股票池模组基线与预留位置
- [stock_pool_registry_baseline_20260311.md](stock_pool_registry_baseline_20260311.md)：股票池 Registry 基线
- [stock_pool_module_development_plan_20260311.md](stock_pool_module_development_plan_20260311.md)：股票池模组开发计划

### 基础设施

- [production_scheduler.md](production_scheduler.md)：生产调度与运维流程
- [data_sources.md](data_sources.md)：主数据模块的来源与接入策略
- [news_sources.md](news_sources.md)：新闻/公告模块的数据来源与时间对齐要求

## 当前使用边界

- 任何涉及模型开发的改动，先判断是“共用基础设施”还是“模型线专用逻辑”。
- 当前主线开发默认服务 `3d/5d/10d`，`1d` 变更不得顺手改写主线默认入口。
- 主线推荐默认消费聚合后的 `alpha_score`，若要改写聚合逻辑，应同步更新模块规范与研究口径。
- 需要字段、时间边界和协议定义时，转到 [../interfaces/README.md](../interfaces/README.md)。
