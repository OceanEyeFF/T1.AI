---
title: "WT-EXPAND-001 Intake Review — 股票池扩展至 sectors_70"
artifact_type: "worktrack-intake-review"
proposed_worktrack_id: "WT-EXPAND-001"
milestone_context: "post-MS-S2-001 expansion"
created: "2026-06-22T13:00:00+08:00"
owner: "OceanEyeFF"
status: "pending-programmer-review"
---

# WT-EXPAND-001 Intake Review

> 股票池扩展至 sectors_70 + 现有缓存合并，用于低控盘概率综合评分。

## 1. 动机

MS-S2-001 完成了股票池分层的 registry 契约和 pipeline 验证，但实际缓存仅覆盖 8 只股票（quick8）。四个 SubAgent 给出的综合评分系统已就绪（`scripts/score_low_manipulation.py`），但 7 只主板的样本量不足以支撑有统计意义的筛选结论。

本 Worktrack 的目标：**将缓存扩展到 ~63 只股票，重新运行综合评分，产出第一份有实际区分度的低控盘概率排名。**

## 2. Scope

### In Scope

- 从 `data/symbols_lstm_sectors_70.csv` 读取 70 只跨行业股票
- 通过 A 股主板过滤（排除 688/300/301/8/4 前缀），剩余 ~57 只需获取
- 对每只新股拉取三个端点：
  - `daily`（日线 OHLCV，qfq 复权）
  - `daily_basic`（市值、换手率、PE/PB 等）
  - `moneyflow`（资金流向，可选——若某只股票的 moneyflow 拉取失败不阻断）
- 全部 cache-first：已缓存的 8 只跳过，不重复请求
- 数据存入与现有相同的分区 parquet 缓存结构（`data/cache/tushare_*/{ts_code}/year=YYYY/part.parquet`）
- 拉取完成后运行 `scripts/score_low_manipulation.py` 产出全量排名
- 按排名前 N 筛选，注册为新股票池（如 `custom_low_manipulation_topN_v1`）

### Out Of Scope

- 修改评分系统逻辑（已在 MS-S2-001 A3 中完成）
- 重新训练或验证预测模型
- 3/5/10d 复验
- 信号晋级
- 实盘数据刷新或生产调度

## 3. Task Breakdown

| # | 任务 | 类型 | 预计耗时 |
|---|---|---|---|
| T1 | 解析 sectors_70 符号列表，生成 ts_code 映射，标记已缓存/需获取 | prep | < 5 min |
| T2 | 运行 `plan_tushare_fetch_manifest` dry-run，输出精确请求预算 | prep | < 5 min |
| T3 | 拉取 57 只新股的 daily_basic | fetch | ~40 min |
| T4 | 拉取 57 只新股的 daily qfq | fetch | ~40 min |
| T5 | 拉取 57 只新股的 moneyflow（可选，失败不阻断） | fetch | ~40 min |
| T6 | 验证缓存完整性（每只股票至少 daily_basic + daily 齐全） | verify | < 5 min |
| T7 | 运行综合评分，产出全量排名 | compute | < 5 min |
| T8 | 注册 Top-N 股票池 + 导出 smoke | registry | < 10 min |

**总预计耗时：~2 小时**（含 1H 频率墙等待）

## 4. TuShare 获取预算

### 4.1 端点与请求数

| 端点 | 新增股票数 | 请求数/股 | 总请求 | 备注 |
|---|---|---|---|---|
| daily | 57 | 1 | 57 | qfq 复权，覆盖 2023-01 ~ 至今 |
| daily_basic | 57 | 1 | 57 | 市值、换手率、PE/PB |
| moneyflow | 57 | 1 | 57 | 可选，失败不阻断 |
| **合计** | | | **≤ 171** | |

### 4.2 频率墙策略

- TuShare 免费用户：≤ 200 次/小时
- 1H 频率墙：连续请求间隔 ≥ 18 秒（`sleep_seconds = 20`，留余量）
- 三个端点的频率墙共享同一小时预算
- 使用 A2 已验证的 `TushareSource` resume 逻辑

### 4.3 断点续跑

- 每个端点独立分区存储（`year=YYYY/part.parquet`）
- 中断后扫描已有分区，从第一个缺失年份恢复
- 每个符号的每个端点独立 checkpoint

### 4.4 缓存命中

- 已有缓存的 8 只 + 2 只 sectors_70 重叠 = 自动跳过
- 不会重复消耗 quota

## 5. 预期产出

| 产出 | 说明 |
|---|---|
| 扩展后的缓存 | 3 个端点 × ~65 只股票的分区 parquet |
| 综合评分排名 | `scripts/score_low_manipulation.py` 全量输出 |
| 新股票池 | 如 `custom_low_manipulation_top10_v1`（Top-N 按综合评分） |
| 各维度明细 | 每只股票的 6 维度子分和 15+ 原始指标 |

## 6. 风险

| 风险 | 缓解 |
|---|---|
| TuShare token 过期或无效 | 拉取前验证 token，失败立即停止 |
| 部分股票数据缺失（如退市、停牌） | 记录缺失符号，不阻断整体流程 |
| 频率墙触发导致拉取中断 | resume 逻辑自动从断点恢复 |
| 小时配额耗尽 | 记录未完成的符号列表，下次续跑 |
| 拉取到的股票在评分中因数据不足被排除 | 预期行为——评分脚本本身有 MIN_DATA_DAYS 门槛 |

## 7. Acceptance Criteria

- [ ] 至少 50 只新股成功获取 daily_basic + daily qfq 数据
- [ ] 所有新增缓存通过 `py_compile` 和 schema 检查
- [ ] `score_low_manipulation.py` 在完整数据集上成功运行
- [ ] 产出按综合评分排名的股票列表（含各维度明细）
- [ ] 全程无模型训练、无信号晋级、无生产调用

## 8. 审批要点

| 审批项 | 状态 |
|---|---|
| TuShare quota 调用 | ⏳ 需 programmer 批准 |
| 数据写入 `data/cache/` | ⏳ 需 programmer 批准（本地文件，无外部影响） |
| Git commit | 不需要（缓存文件已在 .gitignore 中） |
| 新 registry pool 注册 | 拉取完成后单独审批 |

---

## 决策请求

请确认以下三个问题：

1. **是否批准 TuShare quota 调用**（≤ 171 次，约 1-2 小时）？
2. **目标股票池规模**：sectors_70（~63 只合并后）够用，还是需要更大的范围（如 CSI300 + 中证500）？
3. **moneyflow 端点**：是否必须拉取（增加 57 次请求），还是作为可选（缺失不阻断）？
