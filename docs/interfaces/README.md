# Interfaces 文档

这一层放最细颗粒、最接近代码和回测边界的文档。

适合在这里回答的问题：

- 哪些字段必须有
- 时间对齐怎么定义
- 交易动作允许什么、不允许什么
- 环境和执行前置条件是什么

## 推荐阅读顺序

1. [setup.md](setup.md)
2. [constraints.md](constraints.md)
3. [objectives.md](objectives.md)
4. [data_contract.md](data_contract.md)
5. [protocol.md](protocol.md)

## 文档分组

- [setup.md](setup.md)：环境与运行前置
- [constraints.md](constraints.md)：策略和回测硬约束
- [objectives.md](objectives.md)：目标与验收标准
- [data_contract.md](data_contract.md)：数据字段与 schema 契约
- [protocol.md](protocol.md)：交易协议与时序边界

## 使用边界

- 这一层应尽量稳定，避免频繁夹杂临时实验结论。
- 任何研究结论要进入这里，必须先在 [../research/README.md](../research/README.md) 验证稳定。
