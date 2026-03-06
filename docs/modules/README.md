# Modules 文档

这一层放系统分层、模块边界、模块协同方式。

适合在这里回答的问题：

- 系统有哪些层
- 数据、训练、执行、调度这些模块怎么连接
- 某一类能力应该挂在哪个模块，而不是先写哪个字段

## 推荐阅读顺序

1. [system_io_and_architecture_spec.md](system_io_and_architecture_spec.md)
2. [production_scheduler.md](production_scheduler.md)
3. [data_sources.md](data_sources.md)
4. [news_sources.md](news_sources.md)

## 文档分组

- [system_io_and_architecture_spec.md](system_io_and_architecture_spec.md)：系统 I/O 与架构分层
- [production_scheduler.md](production_scheduler.md)：生产调度与运维流程
- [data_sources.md](data_sources.md)：主数据模块的来源与接入策略
- [news_sources.md](news_sources.md)：新闻/公告模块的数据来源与时间对齐要求

## 使用边界

- 这一层不替代交易协议和数据契约。
- 需要字段、时间边界、约束定义时，转到 [../interfaces/README.md](../interfaces/README.md)。
