---
title: "Pre-Milestone Intake Review — MS-R0-001"
artifact_type: "pre-milestone-intake-review"
proposed_milestone_id: "MS-R0-001"
created: "2026-06-22T15:00:00+08:00"
owner: "OceanEyeFF"
status: "pending-programmer-review"
---

# MS-R0-001 Pre-Milestone Intake Review

> 选股侧重构：铲平旧方法，只保留低控盘多维度评分作为唯一选股底座

## 1. 动机

当前 repo 的选股侧存在四套互不兼容的方法论——手动 quick8、行业板块分类、纯市值阈值、低控盘多维度评分。前三套没有完整的假设→指标→验证闭环，是历史遗留。只有第四套有方法论。

**决策：铲掉前三套，只保留第四套。从 0 重建选股侧。**

## 2. 铲的范围

### 2.1 移除

| 目标 | 原因 |
|---|---|
| `configs/stock_pools/custom_quick8_v1.toml` | 无选股方法论 |
| `configs/stock_pools/custom_liquid_large_proxy_v1.toml` | 单一规则，被多维度评分覆盖 |
| `configs/stock_pools/custom_low_control_proxy_candidate_v1.toml` | 两条规则，被多维度评分覆盖 |
| `data/symbols_lstm_quick8.csv` | 旧的符号列表 |
| `data/symbols_lstm_sectors_70.csv` | 行业分类凑数，无方法论 |
| 旧的行业/板块选股脚本和逻辑 | 粘连代码 |
| 旧的 registry 引用和过时文档中的池子引用 | 防止下游误用 |

### 2.2 保留

| 资产 | 处理 |
|---|---|
| TuShare 缓存（65+ 只，3 端点） | 保留，纯数据资产 |
| `scripts/score_low_manipulation.py` | 作为唯一选股入口，可能重构但保留核心方法论 |
| `configs/stock_pools/custom_low_manipulation_v1.toml` | 当前唯一有效的 registry 记录 |
| `src/ashare_lab/data/tushare_source.py` | 数据获取基础设施 |

### 2.3 重建

- 选股模块只暴露一个入口：多维度评分 → 阈值筛选 → registry 注册
- 清理 `configs/stock_pools/`，只保留方法论驱动的池子
- 更新所有引用旧池子的下游文档和脚本

## 3. Out of Scope

- 不改 pipeline（训练/评估/回测）——那是另一刀
- 不改评分系统的权重或指标——那是后续优化的事
- 不删除缓存数据——那是资产

## 4. 验收标准

- `configs/stock_pools/` 下只存在基于多维度评分方法论注册的池子
- 所有旧池子的 TOML、CSV、symbol lists 已移除
- 旧选股脚本和粘连代码已清理
- 现有测试不受影响
- `scripts/score_low_manipulation.py` 仍可正常运行

## 5. 风险

| 风险 | 缓解 |
|---|---|
| 下游脚本硬引用了旧池子 ID | 逐文件 grep 检查，替换或标记 |
| 删错了有用的东西 | 先 audit 再删，不在一个 commit 里做 |

---

## 决策请求

1. **是否立项 MS-R0-001？**
2. **重构后的选股模块叫什么？** 把 `score_low_manipulation` 重新命名，还是保留现有名字？
3. **Pipeline 重构要不要单独拆成一个 Milestone？** 还是顺手在这一轮一起做？
