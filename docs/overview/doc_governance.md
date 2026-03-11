# 文档命名与落盘规则

本文档定义仓库文档的创建、命名、归类和清理规则。

主原则：先按颗粒度归类，再按时间属性标记。

## 1. 落盘前先判定颗粒度

新文档创建前，必须先回答：

1. 它属于 `overview` / `modules` / `interfaces` / `research` / `archive` / `branch_tasks` 哪一层。
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

### 2.6 Branch Tasks

适合放入 `branch_tasks` 的文档：

- 分支级别的任务清单与状态追踪
- 分支的角色定义、边界约束和退出条件
- 治理专题的拆解清单
- 分支合入/归档的过程记录

典型位置：

- `docs/branch_tasks/`
- 由 `docs/branch_tasks/README.md` 索引

**特殊规则：**

- 每个活跃分支对应一个任务文档，不做跨分支合并文档
- 新分支创建时必须从模板创建任务文档（模板见 [doc_lifecycle_rules_20260311.md](doc_lifecycle_rules_20260311.md) § 6）
- 已归档分支的任务文档保留原位，但在文档内标注"已归档"
- 治理专题清单（如 `develop_governance_backlog_*.md`）也归入此层

**与其他层的区别：**

- `overview` 回答"项目在做什么"，`branch_tasks` 回答"这条分支在做什么"
- `branch_tasks` 是执行追踪工具，不是项目级规划文档
- 任务文档可以引用 overview/modules/research 的基线文档，但不替代它们

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

详细的归档流程、文档状态管理和维护责任矩阵，见 [doc_lifecycle_rules_20260311.md](doc_lifecycle_rules_20260311.md)。

## 7. 最低维护动作

每次新增、移动或删除文档时，至少同步更新：

- `docs/README.md`
- `docs/INVENTORY.md`
- 对应层级目录下的 `README.md`

详细的维护职责分配和分支间权限规则，见 [doc_lifecycle_rules_20260311.md](doc_lifecycle_rules_20260311.md) § 4-5。
