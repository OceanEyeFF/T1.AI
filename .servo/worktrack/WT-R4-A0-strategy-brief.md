---
title: "WT-R4-A0 Strategy Brief — research_liquidity_quality"
artifact_type: "strategy-brief"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A0"
strategy_name: "research_liquidity_quality"
updated: "2026-07-15T09:42:00+08:00"
owner: "OceanEyeFF"
status: "draft_for_implementation"
---

# research_liquidity_quality — Strategy Brief（A0-T1）

> 本文件是 WT-R4-A0 的可审计准则草案。实现（T2）应以本文为准；权重数值为 **draft**，可在实现前微调，但不得改变命题、硬过滤、规模天花板与非目标。

## Control Signal

```yaml
strategy_name: research_liquidity_quality
strategy_folder: src/ashare_lab/stock_pool/research_liquidity_quality/
pool_id_hint: custom_research_liquidity_quality_v1
thesis: mainboard_research_tradability_hygiene
soft_target_size: 80
hard_cap: 100
old_pool_role: contrast_baseline_only
data_policy: cache_first_no_silent_live
weights_status: draft_for_T2
programmer_confirm_needed_before_registry_lock: true
```

## 1. 命题（Thesis）

为后续 TuShare 数据湖与研究管线提供一个 **可复现、可审计、主板可交易卫生** 的研究宇宙，而不是：

- 最优 alpha 选股；
- 「低控盘概率」真理标签；
- 全市场覆盖。

一句话：筛掉明显不适合日频研究底座的标的（流动性过差、卫生条件差、数据不足），保留足够规模的干净主板集合。

## 2. 规模

| 约束 | 值 | 备注 |
|---|---|---|
| 硬上限 | **100** | milestone C2；超限不得 registry 验收通过 |
| 软目标 | **≤80** | A0_Q1=T1；优先满足卫生阈值后再凑规模 |
| 下限建议 | ≥20 | 过小则湖灌装价值低；若 cache 不足以选出 20，记录缺口 defer A3，不强行放宽硬过滤 |

若候选超过软目标：按综合分降序截断到 80。  
若仍超过硬上限：视为实现 bug，必须修阈值/截断逻辑，不得导出。

## 3. Base Universe（输入侧）

### 3.1 默认输入宇宙

实现侧 `select(universe)` 仍接受外部传入的 `universe: list[str]`。A0 推荐调用方构造：

1. **优先**：现有 `inputs/data/cache/tushare_qfq/` 下有足够分区数据的 ts_code（cache-first）；  
2. 合并指数锚点 `510300.SH`（若策略需要市场对照；指数本身 **不计入** 池规模）；  
3. 可选对照：旧 `low_manipulation` 14 只仅用于 diff，不自动入选。

### 3.2 硬过滤（Fail → 剔除，不进评分）

| ID | 规则 | 理由 |
|---|---|---|
| H1 | 排除代码前缀 `300` / `301` / `688` / `8` / `4`（与现有 `UNIVERSE_EXCLUDE_PREFIXES` 对齐） | 创业板/科创/北交所等不进本湖底座默认宇宙 |
| H2 | 规范化为 `ts_code`（`XXXXXX.SH/SZ`）；无法规范化则剔除 | registry 合同一致性 |
| H3 | lookback 窗口内可用 qfq 交易日数 ≥ `min_data_days`（默认 **120**） | 避免短样本伪统计 |
| H4 | 同期 `daily_basic` 关键字段可得率 ≥ **80%**（至少 `circ_mv` / `turnover_rate` 之一完整覆盖 lookback 的 80%） | 基本面/换手卫生 |
| H5 | lookback 内平均日成交额 ≥ **阈值 A**（draft：5000 万元；config 可调） | 流动性下限 |
| H6 | lookback 内停牌或零成交日占比 ≤ **阈值 B**（draft：15%） | 可交易卫生 |
| H7 | lookback 内涨跌停触发次数 ≤ **阈值 C**（draft：8 次 / 60 交易日窗） | 极端交易卫生（非「控盘」断言） |

H5–H7 的 draft 数值可在 T2/config.toml 落地；变更须写入 metadata.notes，不得静默改语义。

## 4. 软评分维度（通过硬过滤后）

综合分 ∈ [0, 100]。**不声称**反映真实操控概率；仅作研究宇宙排序。

| 维度 ID | 名称 | Draft 权重 | 主要输入 | 高分方向（摘要） |
|---|---|---|---:|---|
| D1 | liquidity_depth | 0.30 | amount / circ_mv / Illiq | 更深流动性、更低冲击成本迹象 |
| D2 | turnover_health | 0.25 | turnover_rate | 落在可配置甜蜜区间，波动不过大 |
| D3 | data_completeness | 0.20 | qfq + daily_basic + moneyflow 可得率 | 三表齐全且缺口少 |
| D4 | trading_hygiene | 0.15 | 涨跌停次数、零量日、隔夜/日内比 | 极端更少、更「常规」 |
| D5 | market_synchronicity | 0.10 | vs 510300 的 β / R²（可选） | 有合理同步、非完全噪声；缺指数则维度中性 50 |

权重和为 1.0。入选阈值 draft：`score_threshold = 55`（低于阈值不入选，再按分排序截断到软目标）。

### 4.1 与 low_manipulation 的差异（刻意）

| | low_manipulation | research_liquidity_quality |
|---|---|---|
| 命题 | 低控盘概率 proxy | 研究可交易卫生 / 数据完备 |
| 权重叙事 | 规模壁垒 35% 等 6 维控盘代理 | 流动性 + 完备性为主，弱化「操控」叙事 |
| 资金流 | 独立 5% 权重 | **不作为独立维度**；moneyflow 仅贡献 data_completeness |
| 目标规模 | 历史 14（阈值 60） | 软 80 / 硬 100 |
| 旧池角色 | 生产叙事候选 | **仅对照基线** |

## 5. 数据与执行政策（A0）

```yaml
data_sources:
  - inputs/data/cache/tushare_qfq/
  - inputs/data/cache/tushare_daily_basic/
  - inputs/data/cache/tushare_moneyflow/   # 完备性；非独立打分维
lookback_days: 60          # draft；与 min_data_days=120 同时满足「至少 120 日可用」
cache_policy: cache_first
live_pull: forbidden_by_default   # L2 允许有限 live，但 A0-T1/T2/T3 默认不做；缺口列表化 → A3
token_policy: env_only_never_commit
```

缺 cache 的 symbol：记入 `WT-R4-A0-data-gaps.md`（T3 产出），**不得**为凑规模静默 live。

## 6. Registry 合同（T4 目标）

| 字段 | 拟填值 |
|---|---|
| stock_pool_id | `custom_research_liquidity_quality_v1` |
| stock_pool_version | `1` |
| pool_family | `custom` |
| pool_label | `研究流动性卫生池 v1` |
| construction_method | `hard-filters + 5-dimension hygiene score; cache-first` |
| base_universe | `main board A-shares (excl. 300/688/8/4); cache-available first` |
| symbols_count | ≤80 目标；硬 ≤100 |
| rebalance_frequency | `monthly`（文档口径；A0 不实现调度器） |
| effective_start | `2023-01-01` |
| is_research_only | `true`（milestone Gate 前） |
| owner | `stock_pool/research_liquidity_quality` |

必须经 `export_stock_pool_artifacts()`；禁止手改 toml 冒充注册。

## 7. 实现边界（供 T2–T6）

### In scope

- `strategy.py` + `config.toml` + 策略包导出
- cache-first `select(universe)`
- registry 三件套
- 相对 `custom_low_manipulation_v1` / `inputs/pools/low_manipulation` 的 diff 报告
- 聚焦单测（继承 ABC、幂等、硬过滤、截断上限）

### Out of scope

- A1 日/RPM 数值批准与湖合同终稿
- A3 limited-live 补洞战役
- A4 derived / QA 终稿
- 训练、回测、信号晋升
- 删除 AkShare；覆写 `low_manipulation/` 目录

## 8. Programmer 确认点（非阻断 T2 开工，但阻断「池终态锁定」）

实现前默认采用本文 draft 阈值/权重。若你要改，请在 T2 前明示；否则 T2 按 draft 编码，registry 导出前再确认一次：

1. H5 日均成交额下限（draft 5000 万）  
2. `score_threshold`（draft 55）  
3. 软目标 80 是否保持  

（答「按 draft」或列出修改即可。）

## 9. 验收映射

| A0 验收项 | 本文对应 |
|---|---|
| 可审计准则文档 | 本 brief |
| Strategy + config | §3–§4 → T2 |
| registry ≤100 / 目标≤80 | §2 / §6 → T4 |
| 旧池差异报告 | §4.1 → T5 |
| 缺口列表 | §5 → T3 |
| 无 token / 无未批 live | §5 |

## 10. References

- Intake: `.servo/worktrack/MS-R4-001-WT-R4-A0-intake-review.md`
- Contract: `.servo/worktrack/WT-R4-A0-contract.md`
- Guide: `docs/guides/stock_pool_maintenance_guide.md`
- Contrast: `src/ashare_lab/stock_pool/low_manipulation/`
