# 文档导航

本仓库文档的主导航按“颗粒度”组织，而不是按时间状态组织。

推荐的阅读和检索顺序是：

1. `overview/`：粗颗粒、抽象、项目级文档
2. `modules/`：中颗粒、系统/模块级文档
3. `interfaces/`：细颗粒、约束/协议/接口文档
4. `research/`：研究方法、评估流程、实验结论
5. `archive/`：历史资料与已下线文档说明

完整文件清单见 [INVENTORY.md](INVENTORY.md)。

## 1. 颗粒度规则

- `overview`：回答“项目是什么、要去哪里、有哪些总原则”。
- `modules`：回答“系统由哪些模块组成、模块怎么协同”。
- `interfaces`：回答“字段、协议、边界、约束具体是什么”。
- `research`：回答“为什么这样做、实验怎么验证、当前结论是什么”。
- `archive`：回答“哪些东西已经退场，为什么退场”。

时间属性仍然保留，但只作为文档元信息，不再作为主目录结构。

## 2. 推荐入口

1. [overview/README.md](overview/README.md)
2. [modules/README.md](modules/README.md)
3. [interfaces/README.md](interfaces/README.md)
4. [research/README.md](research/README.md)
5. [archive/README.md](archive/README.md)

## 3. 根目录文档定位

- [../README.md](../README.md)：项目总入口，属于 `overview`
- [../NEXT_STEPS.md](../NEXT_STEPS.md)：当前执行入口，属于 `overview`
- [../ROADMAP.md](../ROADMAP.md)：长期路线入口，属于 `overview`

## 4. 使用建议

- 需要理解项目目标、路线、治理规则时，从 `overview/` 开始。
- 需要按主题而不是按目录查找时，先看 [overview/topic_maps.md](overview/topic_maps.md)。
- 需要按主题看“大方向还缺什么”时，先看 [overview/topic_gaps.md](overview/topic_gaps.md)。
- 需要理解模块边界和系统分层时，从 `modules/` 开始。
- 需要确认具体字段、协议、交易约束时，从 `interfaces/` 开始。
- 需要确认评估口径、训练策略、实验依据时，从 `research/` 开始。

## 5. 维护约定

- 新文档先决定颗粒度，再决定时间属性。
- 同一主题优先保持“总览 -> 模块 -> 接口”三层递进，不要直接从总览跳到实现细节。
- 实验报告默认不进入主导航，除非它已经成为当前唯一基线。
