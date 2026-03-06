# 文档命名与落盘规则

本文档定义仓库文档的创建、命名、归类和清理规则。

主原则：先按颗粒度归类，再按时间属性标记。

## 1. 落盘前先判定颗粒度

新文档创建前，必须先回答：

1. 它属于 `overview` / `modules` / `interfaces` / `research` / `archive` 哪一层。
2. 它的时间属性是 `current` / `future` / `historical` 中的哪一类。

如果第一问答不出来，就先不要写。

## 2. 颗粒度规则

### 2.1 Overview

适合放入 `overview` 的文档：

- 项目目标、蓝图、路线、治理规则
- 项目级计划和阶段性总览
- 不依赖具体字段和接口的抽象描述

典型位置：

- `docs/overview/`
- 根目录 `README.md` / `NEXT_STEPS.md` / `ROADMAP.md`

### 2.2 Modules

适合放入 `modules` 的文档：

- 系统分层
- 模块职责与协同方式
- 数据源、调度、服务化、运维模块说明

典型位置：

- `docs/modules/`
- 由 `docs/modules/README.md` 索引到具体模块文档

### 2.3 Interfaces

适合放入 `interfaces` 的文档：

- 数据字段定义
- 交易协议与时间边界
- 约束、目标、运行前置

典型位置：

- `docs/interfaces/`
- 顶层接口文档由 `docs/interfaces/README.md` 索引

### 2.4 Research

适合放入 `research` 的文档：

- 研究方法
- 评估工作流
- 训练策略与实验结论
- 研究专项改造任务

典型位置：

- `docs/research/`

### 2.5 Archive

适合放入 `archive` 的文档：

- 已退出主流程的历史材料
- 已删除文档的说明
- 外部参考稿

## 3. 时间属性只作为辅标签

- `current`：当前仍在使用
- `future`：未来规划或蓝图
- `historical`：历史资料

时间属性可以写在文档头部，但不再决定目录结构。

## 4. 命名规则

### 4.1 长期稳定文档

- 文件名描述主题，不带日期。
- 示例：
  - `protocol.md`
  - `data_contract.md`
  - `future_state_blueprint.md`

### 4.2 短期任务或专项文档

- 文件名需要带时效线索。
- 推荐：
  - `topic_2026Q1.md`
  - `topic_yyyymmdd.md`

### 4.3 实验报告

- 统一使用 `topic_yyyymmdd.md`
- 默认放到 `research`，但不自动进入主导航
- 结论稳定后，提炼进 `overview`、`modules` 或 `interfaces`

## 5. 根目录例外

根目录只保留项目级入口：

- `README.md`
- `NEXT_STEPS.md`
- `ROADMAP.md`

其余文档原则上不再直接落到根目录。

## 6. 清理规则

- 研究结论一旦稳定，应从 `research` 提炼到更高层级文档。
- 过细的未来文档先抽象为 `overview`，再决定是否保留细稿。
- 已无导航价值的短期文档可直接删除，只保留必要说明。

## 7. 最低维护动作

每次新增、移动或删除文档时，至少同步更新：

- `docs/README.md`
- `docs/INVENTORY.md`
- 对应层级目录下的 `README.md`
