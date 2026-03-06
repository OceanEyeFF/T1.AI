# 下一步工作安排（Next Steps）

**文档颗粒度：** `overview`  
**时间属性：** `current` / `short_term`  
**作用：** 当前阶段执行入口；任务完成后应归档或把稳定结论并入更高层级文档。  
**配套导航：** `docs/overview/README.md`

**当前仓库目标：** 在严格模拟 A 股约束（T+1、涨跌停/一字板、成交失败、总摩擦成本 `max(5元, 成交额*0.001)`、单日亏损阈值 2%）下，做"**日频评估、低换手执行**"的选股与仓位管理研究；模型（LSTM/Transformer）作为第二层增值组件，优先保证回测与风控口径正确。

**📋 项目规划文档：**
- **长期规划（V0.5 ~ V3.0+）：** [ROADMAP.md](ROADMAP.md) - 2026-2028+ 完整演进路线
- **当前任务（V0.5 阶段）：** 本文档 - 详细执行计划与验收标准

**相关基线文档：**
- 约束：`docs/interfaces/constraints.md`
- 目标/验收口径：`docs/interfaces/objectives.md`
- 数据契约：`docs/interfaces/data_contract.md`
- 数据来源/新闻建议：`docs/modules/data_sources.md`、`docs/modules/news_sources.md`

---

## 0. 明确交易协议（先定口径，避免模型返工）✅

**状态：已完成（2025-12-29）**

目标：把"什么时候产生信号、什么时候成交、持有周期、调仓频率、做T范围"写成可配置协议（V1 先用日线，V2 再扩分钟线做T）。

已完成：
- [x] 信号时点：默认收盘后计算（t 日 close 可用）
- [x] 成交时点：默认次日开盘成交（t+1 open）
- [x] 持有周期：默认持有到下一次调仓
- [x] 做T（V1 日线版）：先不做真实日内T；只保留"先卖后买回"的撮合能力
- [x] 做T（V2 分钟线版）：引入分钟线后再实现"盘中卖出→盘中/尾盘买回"的策略规划

交付物：
- ✅ `docs/interfaces/protocol.md`（交易协议与可用信息集合）
- ✅ `configs/protocol.yaml`（可配置）
- ✅ README.md 已更新（添加协议文档引用）

---

## 1. 股票池与可交易性（让"每天评估"变得可控）✅

**状态：已完成（2025-12-29）**

目标：从 akshare 拉取全市场列表，按硬约束过滤，并给出可复现的"每日股票池快照"。

已完成：
- [x] 新增 `scripts/build_universe.py`：拉取 A 股列表并过滤（排除 ST/北交/科创/创业）
- [x] 增强过滤函数：添加 6 位数字长度验证
- [x] 保存快照：`data/cache/universe/<date>.csv`
- [x] 单元测试：`tests/test_universe.py`（验证过滤规则正确性）

交付物：
- ✅ `scripts/build_universe.py`（股票池构建脚本）
- ✅ `src/ashare_lab/universe.py`（增强的过滤函数）
- ✅ `tests/test_universe.py`（单元测试，12 个测试全部通过）
- ✅ README.md 已更新（添加使用说明）

---

## 2. 特征与标签（先做简单、严格防穿越）✅

**状态：已完成（2025-12-30）**

目标：搭建 dataset builder（特征/标签/对齐规则），为规则策略与深度模型共用。

### 快速迭代计划（4 轮）

#### 第一轮：基础架构 + 价格动量特征
- [x] 创建 `src/ashare_lab/features/` 目录结构
- [x] 实现 `BaseFeature` 基础类（定义接口规范）
- [x] 实现价格动量特征：
  - `return_1d`：1 日收益率（严格滞后对齐）
  - `return_5d`：5 日收益率
  - `return_20d`：20 日收益率
- [x] 编写单元测试 `tests/test_features_momentum.py`（验证时间对齐，防穿越）
- [x] Gate 验证：pytest 全绿

#### 第二轮：量价特征
- [x] 实现量价特征：
  - `volume_ratio`：量比（今日成交量 / N 日均量）
  - `amount_change`：成交额变化
  - `volume_change`：成交量变化
  - （可选）`turnover_rate`：换手率（依赖流通股本数据，留到 V1.1）
- [x] 编写单元测试 `tests/test_features_volume.py`
- [x] Gate 验证：pytest 全绿

#### 第三轮：标签定义
- [x] 创建 `src/ashare_lab/labels/` 目录
- [x] 实现 `ExcessReturnLabel` 类：
  - 计算次日收益率
  - 计算基准（沪深300）次日收益率
  - 计算超额收益（股票收益 - 基准收益）
- [x] 编写单元测试 `tests/test_labels.py`（验证标签时间对齐）
- [x] Gate 验证：pytest 全绿

#### 第四轮：数据集构建器
- [x] 创建 `src/ashare_lab/dataset/` 目录
- [x] 实现 `DatasetBuilder` 类：
  - 加载股票池快照
  - 加载行情数据（复用 `ashare_lab.data.akshare_source`）
  - 计算特征和标签
  - walk-forward 切分（训练/验证/测试）
- [x] 创建 `scripts/build_dataset.py` 脚本
- [x] 编写集成测试 `tests/test_dataset_builder.py`
- [x] Gate 验证：pytest 全绿 + 生成示例数据集

### 验收标准（DoD）

- ✅ 特征计算严格滞后对齐（t 日特征仅使用 t-1 及之前数据）
- ✅ 标签定义清晰（次日相对沪深300超额收益）
- ✅ dataset builder 支持 walk-forward 切分（训练/验证/测试）
- ✅ 所有单元测试和集成测试通过（pytest 全绿）
- ✅ 输出格式清晰（CSV 或 Parquet，包含元数据）
- ✅ 文档完善（代码注释 + docstring）

### 技术细节

**时间对齐规则（严格防穿越）：**
- 特征 `t` 仅使用数据 `[0, t-1]`（不包含 t 日）
- 标签 `t` 对应的是 `t+1` 日的收益（基于 t+1 日的 close）
- 示例：2024-01-15 的特征使用 2024-01-14 及之前的数据，标签是 2024-01-16 的收益

**数据依赖：**
- 行情数据：`ashare_lab.data.akshare_source.load_or_fetch_daily_bars`
- 基准数据：`ashare_lab.data.index_source.load_or_fetch_index_daily`（沪深300）
- 股票池快照：`data/cache/universe/<date>.csv`

**输出格式：**
```
data/datasets/<name>/
├── metadata.yaml          # 数据集元信息（特征列表、时间范围、切分规则）
├── train.parquet          # 训练集（带时间戳 + 特征 + 标签）
├── valid.parquet          # 验证集
└── test.parquet           # 测试集
```

备注：
- V1 不接基本面；V1.1 再加"按披露日对齐"的财务特征。

---

## 3. 策略层（低换手执行：阈值、门槛、风控联动）⭐ **进行中**

**状态：** 下一步任务（预计工作量 1.5 天）

**目标：** 把"每天都评估"变成"只有优势足够大才交易"，并且与单日亏损阈值联动。

### 详细计划

#### 阶段 1：架构拆分（0.5 天）✅ **已完成**
- [x] 创建 `src/ashare_lab/strategy/__init__.py`（模块初始化）
- [x] 创建 `src/ashare_lab/strategy/signal.py`
  - 定义 `SignalGenerator` 基类（接口规范）
  - 实现 `compute_scores()` 方法（返回股票打分）
  - 实现 `rank_stocks()` 方法（按分数排序）
  - 实现 `MomentumSignalGenerator`（从现有 MomentumTopNStrategy 迁移）
- [x] 创建 `src/ashare_lab/strategy/portfolio.py`
  - 定义 `PortfolioManager` 类
  - 实现 `compute_target_weights()` 方法（信号 → 目标权重）
  - 实现换仓门槛逻辑（优势不足时保持现有持仓，阶段2实现）
- [x] 编写单元测试 `tests/test_strategy_signal.py` 和 `tests/test_strategy_portfolio.py`
- [x] 所有测试通过（pytest 67 passed）
- [x] 代码质量检查通过（ruff check 全绿）
- [x] 代码格式检查通过（ruff format 全绿）

**交付成果：**
- ✅ `src/ashare_lab/strategy/signal.py` - 信号生成器（134行，包含完整文档）
- ✅ `src/ashare_lab/strategy/portfolio.py` - 仓位管理器（106行，包含完整文档）
- ✅ `tests/test_strategy_signal.py` - 8个单元测试（202行）
- ✅ `tests/test_strategy_portfolio.py` - 8个单元测试（165行）
- ✅ Gate 状态：绿色（2026-01-08 01:00:39）

#### 阶段 2：换仓门槛与成本覆盖（0.5 天）
- [ ] 引入换仓门槛配置：`configs/protocol.yaml` 添加参数
  ```yaml
  strategy:
    rebalance_threshold: 0.05  # 新候选优势必须 > 5% 才换仓
    cost_coverage_ratio: 3.0    # 预期收益必须覆盖 3 倍成本
  ```
- [ ] 实现换仓逻辑：
  - 计算新候选相对当前持仓的预期超额收益
  - 仅当 `预期超额 > 阈值 AND 预期超额 > N * 预期成本` 时才执行换仓
- [ ] 编写测试验证：低换手策略成本占比 < 规则策略

#### 阶段 3：风控行为明确化（0.3 天）
- [ ] 增强风控逻辑（`src/ashare_lab/backtest/engine.py`）
  - 触发单日亏损 -2% 后：
    - 禁止开新仓（allow_buy = False）
    - 仅允许平仓降低风险
    - 记录风控触发次数到 `diagnostics['risk_buy_disabled']`
  - 记录成交失败原因：
    - `sell_blocked_limit_down`：跌停导致卖出失败
    - `sell_blocked_tplus1`：T+1 约束导致卖出失败
    - `buy_blocked_limit_up`：涨停导致买入失败
- [ ] 回测报告增强：显示风控触发统计

#### 阶段 4：集成与验证（0.2 天）
- [ ] 修改 `BacktestEngine` 调用策略层新接口
- [ ] 更新 `scripts/run_backtest.py` 使用新策略层
- [ ] Gate 验证：pytest 全绿 + 回测成功运行

### 验收标准（DoD）

- ✅ 策略层拆分为 `signal` + `portfolio` 两层（架构清晰）
- ✅ 换仓门槛与成本覆盖阈值可配置（`configs/protocol.yaml`）
- ✅ 风控行为明确化（回测报告显示成交失败原因统计）
- ✅ 低换手策略年化换手率 < 200%（相比现有动量策略）
- ✅ 通过所有单元测试和集成测试（pytest 全绿）
- ✅ 回测报告增强：新增风控触发次数、成交阻断统计

### 交付物

- `src/ashare_lab/strategy/signal.py` - 信号生成器
- `src/ashare_lab/strategy/portfolio.py` - 仓位管理器
- `tests/test_strategy_*.py` - 单元测试
- `configs/protocol.yaml` - 更新配置参数
- 回测报告示例：展示低换手策略效果

---

## 4. 回测与报告（用一致口径评估：收益、风险、成本、可执行）

**状态：** 待启动（前置依赖：任务 3）

**目标：** 让每次实验都自动产出对照一致的报告，避免"回测口径漂移"。

### 详细计划

#### 阶段 1：报告增强（0.5 天）
- [ ] 月度超额收益统计（`src/ashare_lab/reporting.py`）
  - 按月分组计算：策略收益、基准收益、超额收益
  - 输出月度胜率（超额 > 0 的月份占比）
  - 生成 `monthly_excess.csv`
- [ ] 滚动 12 个月胜率分析
  - 计算滚动窗口（12 月）内的胜率
  - 输出时间序列图：胜率变化趋势
- [ ] 成本占毛利润统计
  - 计算总成本、总毛利润（未扣成本前）
  - 输出成本侵蚀比例：`总成本 / 总毛利润`

#### 阶段 2：诊断信息增强（0.3 天）
- [ ] 成交失败原因统计（`diagnostics` 字典）
  - `buy_blocked_limit_up`：涨停导致买入失败
  - `sell_blocked_limit_down`：跌停导致卖出失败
  - `sell_blocked_tplus1`：T+1 约束导致卖出失败
  - `risk_buy_disabled`：风控触发禁止开仓
- [ ] 输出 `diagnostics_summary.csv`：每种失败原因的次数与占比

#### 阶段 3：输出格式统一（0.2 天）
- [ ] 规范化输出目录结构：`runs/<timestamp>/`
  ```
  runs/20260108_143022/
  ├── equity.csv              # 权益曲线（日度）
  ├── benchmark.csv           # 基准曲线（沪深300）
  ├── excess.csv              # 超额收益（策略 - 基准）
  ├── monthly_excess.csv      # 月度超额统计
  ├── fills.csv               # 成交明细
  ├── stats.csv               # 总体统计（CAGR/Sharpe/最大回撤）
  ├── diagnostics.csv         # 诊断信息（成交阻断统计）
  └── config.yaml             # 运行时配置快照
  ```
- [ ] 自动生成可视化报告（可选，使用 matplotlib）
  - 权益曲线对比图（策略 vs 基准）
  - 月度超额收益柱状图
  - 回撤曲线图

### 验收标准（DoD）

- ✅ 每次回测自动生成完整报告（equity/benchmark/excess/fills/stats/diagnostics）
- ✅ 月度超额收益统计准确（与手工计算对照）
- ✅ 成本占毛利润比例清晰展示（用于评估策略有效性）
- ✅ 诊断信息完整（所有成交失败原因都有记录）
- ✅ 输出格式统一（方便脚本化分析）

### 交付物

- `src/ashare_lab/reporting.py` - 报告生成器（增强版）
- `runs/<timestamp>/` - 标准化输出目录
- `scripts/analyze_results.py` - 批量分析脚本（可选）

---

## 5. 模型架构（LSTM/Transformer 放在"增值层"，先定义接口）

**状态：** 待启动（前置依赖：任务 2 已完成，任务 3 建议完成）

**目标：** 先定义"模型插槽"，让策略层只依赖统一的 `score` 输出；随后逐步替换为深度模型。

### 详细计划

#### 阶段 1：模型接口定义（0.5 天）
- [ ] 创建 `src/ashare_lab/models/base.py`
  - 定义 `BaseModel` 抽象类
    ```python
    class BaseModel(ABC):
        @abstractmethod
        def fit(self, X_train, y_train, X_valid=None, y_valid=None):
            """训练模型"""
            pass

        @abstractmethod
        def predict(self, X):
            """预测打分（用于排序）"""
            pass

        @property
        @abstractmethod
        def feature_schema(self) -> List[str]:
            """返回所需特征列表"""
            pass

        @abstractmethod
        def save(self, path: str):
            """保存模型"""
            pass

        @abstractmethod
        def load(self, path: str):
            """加载模型"""
            pass
    ```
- [ ] 文档：明确模型输入/输出规范、walk-forward 验证要求

#### 阶段 2：Baseline 模型实现（1 天）
- [ ] 创建 `src/ashare_lab/models/linear_model.py`
  - 使用 Ridge Regression / Lasso（L1/L2 正则化）
  - 特征：动量特征 + 量价特征（来自任务 2）
  - 目标：预测次日相对沪深300超额收益
- [ ] 创建 `src/ashare_lab/models/tree_model.py`（可选）
  - 使用 LightGBM / XGBoost
  - 超参数：max_depth, learning_rate, num_leaves
- [ ] Walk-forward 验证脚本：`scripts/train_baseline.py`
  - 训练集：2020-2023
  - 验证集：2024-01 ~ 2024-06
  - 测试集：2024-07 ~ 2024-12（盲测）
- [ ] 评估指标：IC（信息系数）、Rank IC、Sharpe

#### 阶段 3：LSTM/Transformer 接口预留（0.5 天）
- [ ] 创建 `src/ashare_lab/models/lstm.py`（空实现，留待 V1.0）
  - 定义类结构，继承 `BaseModel`
  - 添加 TODO 注释：架构设计、训练策略
- [ ] 创建 `src/ashare_lab/models/transformer.py`（空实现）
- [ ] 文档：记录 V1.0 实现计划（序列长度、网络架构、正则化方案）

### 关键约束（必须遵守）

- **训练/验证切分：** 严格 walk-forward（避免未来信息泄露）
- **目标变量：** 以"相对沪深300超额收益"为主（与回测口径一致）
- **模型职责：** 模型输出只做排序/打分，不直接决定下单（下单由策略层门槛与风控控制）
- **过拟合防护：** 验证集/测试集收益差异 < 2%（否则需调整正则化）

### 验收标准（DoD）

- ✅ `BaseModel` 接口定义清晰（所有子类必须实现）
- ✅ Baseline 模型（线性/树模型）训练成功
- ✅ Walk-forward 验证通过（测试集 IC > 0.02）
- ✅ 模型可持久化（save/load 方法正常工作）
- ✅ 文档完善（模型使用指南 + V1.0 实现计划）

### 交付物

- `src/ashare_lab/models/base.py` - 模型接口
- `src/ashare_lab/models/linear_model.py` - Baseline 线性模型
- `src/ashare_lab/models/tree_model.py` - Baseline 树模型（可选）
- `scripts/train_baseline.py` - 训练脚本
- `docs/model_design.md` - 模型设计文档（V1.0 LSTM/Transformer 规划）

---

## 6. 新闻/公告插件（后置，但先把接口留好）

**状态：** 待启动（优先级较低，可并行或延后）

**目标：** 先把"文本事件 schema + 存档 + 抽取 JSON"做成可插拔，不影响主链路。

### 详细计划

#### 阶段 1：Schema 定义（1 天）
- [ ] 创建 `src/ashare_lab/text_events/schema.py`
  - 定义事件数据结构：
    ```python
    @dataclass
    class TextEvent:
        event_id: str           # 唯一标识
        symbol: str             # 股票代码
        event_type: str         # 事件类型（业绩预告/重组/处罚）
        sentiment: str          # 情感（利好/利空/中性）
        strength: float         # 强度 0-1
        publish_date: datetime  # 发布日期
        raw_text: str           # 原始文本（必须存档）
        source: str             # 来源（东方财富/巨潮资讯）
    ```
- [ ] 创建存储规范：
  - 原文存档：`data/text_events/raw/{date}/{symbol}_{event_id}.txt`
  - 结构化数据：`data/text_events/parsed/{date}.csv`

#### 阶段 2：数据源适配器（1.5 天）
- [ ] 创建 `src/ashare_lab/text_events/fetcher.py`
  - akshare 公告爬取（默认禁用，需手动开启）
  - 东方财富公告接口（备选）
  - 合规检查：遵守 robots.txt + 请求频率限制（1 req/s）
- [ ] 错误处理：网络超时、数据缺失、解析失败
- [ ] 日志记录：爬取成功/失败统计

#### 阶段 3：LLM 事件抽取器（可选，留待 V2.0）
- [ ] 创建 `src/ashare_lab/text_events/extractor.py`（空实现）
  - 定义接口：`extract_event(raw_text: str) -> TextEvent`
  - 文档：记录 V2.0 实现计划（LLM 选型、Prompt 设计）
- [ ] 备注：V0.5 阶段仅做 schema 定义与存档，不做真实抽取

### 关键约束

- **默认禁用：** 新闻/公告插件默认不启用，避免影响主链路稳定性
- **原文存档：** 所有原始文本必须存档（防止数据源变更导致回测不可复现）
- **合规风险：** 仅用于学术研究，避免违反数据源 ToS
- **时间对齐：** 事件发布时间必须严格对齐（避免未来信息泄露）

### 验收标准（DoD）

- ✅ `TextEvent` schema 定义清晰
- ✅ 数据存储规范完善（原文 + 结构化数据）
- ✅ akshare 公告爬取脚本可用（默认禁用）
- ✅ 文档记录 V2.0 实现计划（LLM 抽取、事件驱动策略）

### 交付物

- `src/ashare_lab/text_events/schema.py` - 事件数据结构
- `src/ashare_lab/text_events/fetcher.py` - 数据爬取器（可选）
- `data/text_events/` - 数据存储目录
- `docs/text_events_design.md` - 设计文档（V2.0 规划）

---

## 7. V0.5 版本工作规划（2026-01-08 更新）

### 📊 当前进度总览

**V0.5 版本（2026-01-08 ~ 2026-02-15）：核心链路打通**

| 任务 | 状态 | 工作量 | 优先级 | 完成日期 |
|------|------|--------|--------|---------|
| **任务 0**：交易协议定义 | ✅ 已完成 | - | - | 2025-12-29 |
| **任务 1**：股票池与可交易性 | ✅ 已完成 | - | - | 2025-12-29 |
| **任务 2**：特征/标签 pipeline | ✅ 已完成 | - | - | 2025-12-30 |
| **任务 3**：低换手策略层 | 🚧 进行中（阶段1✅） | 1.5 天 | 最高 | 阶段1: 2026-01-08 |
| **任务 4**：回测与报告增强 | 🔲 待启动 | 1 天 | 高 | - |
| **任务 5**：模型架构接口定义 | 🔲 待启动 | 2 天 | 中 | - |
| **任务 6**：新闻/公告插件 | 🔲 待启动 | 3 天 | 低 | - |

**进度：** 3/7 任务完成（43%），任务3进行中（阶段1/4 已完成）

**任务3详细进度：**
- ✅ 阶段1：架构拆分（0.5天）- 已完成 2026-01-08
- 🔲 阶段2：换仓门槛与成本覆盖（0.5天）- 待启动
- 🔲 阶段3：风控行为明确化（0.3天）- 待启动
- 🔲 阶段4：集成与验证（0.2天）- 待启动

---

### ✅ 已完成任务

#### 任务 0：交易协议定义（2025-12-29 完成）
- ✅ 创建 `docs/interfaces/protocol.md` 和 `configs/protocol.yaml`
- ✅ 明确信号/成交时点、持有周期、做T策略等核心协议
- ✅ 定义信号时点：收盘后计算（t 日 close 可用）
- ✅ 定义成交时点：次日开盘成交（t+1 open）
- ✅ 定义持有周期：持有到下一次调仓
- ✅ 定义做T策略：V1 日线版（先卖后买）、V2 分钟线版（盘中做T）

#### 任务 1：股票池与可交易性（2025-12-29 完成）
- ✅ 创建 `scripts/build_universe.py` 股票池构建脚本
- ✅ 增强 `src/ashare_lab/universe.py` 过滤函数（6位数字验证）
- ✅ 添加单元测试 `tests/test_universe.py`（12 个测试全部通过）
- ✅ 更新 README.md 添加使用说明
- ✅ 保存快照：`data/cache/universe/<date>.csv`

#### 任务 2：特征/标签 pipeline（2025-12-30 完成）
- ✅ 特征：`src/ashare_lab/features/`（严格滞后对齐）
  - 价格动量特征：return_1d/5d/20d
  - 量价特征：volume_ratio、amount_change、volume_change
- ✅ 标签：`src/ashare_lab/labels/`（次日收益 / 次日相对沪深300超额收益）
- ✅ 数据集：`src/ashare_lab/dataset/`（DatasetBuilder + Parquet 输出 + `metadata.yaml`）
- ✅ 脚本：`scripts/build_dataset*.py`、`scripts/train_model.py`、`scripts/evaluate_model.py`
- ✅ 测试：`tests/test_features_*.py`、`tests/test_labels.py`、`tests/test_dataset_builder.py`（pytest 全绿）

**备注：** `turnover_rate` 依赖流通股本数据，留到 V1.1 再实现

---

### ⭐ 当前任务：任务 3 - 低换手策略层

**整体目标：** 把"每天都评估"变成"只有优势足够大才交易"，并且与单日亏损阈值联动。

**当前状态：** 阶段1 ✅ 已完成（2026-01-08），阶段2-4 待启动

**已完成成果（阶段1）：**
- ✅ [src/ashare_lab/strategy/signal.py](src/ashare_lab/strategy/signal.py) - 信号生成器（134行）
- ✅ [src/ashare_lab/strategy/portfolio.py](src/ashare_lab/strategy/portfolio.py) - 仓位管理器（106行）
- ✅ [tests/test_strategy_signal.py](tests/test_strategy_signal.py) - 8个单元测试（202行）
- ✅ [tests/test_strategy_portfolio.py](tests/test_strategy_portfolio.py) - 8个单元测试（165行）
- ✅ 所有测试通过（67 passed），Gate 绿色

**下一步（阶段2）：**
实现换仓门槛与成本覆盖逻辑，详见下方"任务 3"章节。

**详细计划：** 见上方"任务 3"章节

**关键交付物：**
- 阶段1 ✅：`signal.py` + `portfolio.py` + 单元测试
- 阶段2 🔲：换仓门槛配置 + 成本覆盖逻辑
- 阶段3 🔲：风控行为明确化
- 阶段4 🔲：BacktestEngine 集成

**预计总工作量：** 1.5 天（阶段1 已完成 0.5 天，剩余 1.0 天）

**前置依赖：** ✅ 任务 2 已完成

---

### 🗓️ 后续任务规划

#### 任务 4：回测与报告增强（预计 1 天）
- 前置依赖：任务 3 完成
- 详细计划：见上方"任务 4"章节
- 关键交付物：月度超额统计、成本占比分析、诊断信息增强

#### 任务 5：模型架构接口定义（预计 2 天）
- 前置依赖：任务 2 已完成，任务 3 建议完成
- 详细计划：见上方"任务 5"章节
- 关键交付物：BaseModel 接口、Baseline 线性/树模型、V1.0 实现计划

#### 任务 6：新闻/公告插件（预计 3 天，优先级低）
- 前置依赖：无（可并行）
- 详细计划：见上方"任务 6"章节
- 关键交付物：TextEvent schema、数据存储规范、V2.0 实现计划

---

### 🎯 V0.5 验收标准（DoD）

**必须全部满足：**
- ✅ 完整跑通"数据→特征→策略→回测→报告"链路
- ✅ 回测报告包含：超额收益、成本占比、成交阻断统计
- ✅ 支持低换手策略（换仓门槛可配置）
- ✅ 所有测试 100% 通过（pytest 全绿）
- ✅ 文档齐全（每个模块有 docstring + README）
- ✅ 基线性能：年化收益 > 8%、最大回撤 < 25%（动量策略 Baseline）

---

### 📋 后续版本规划（参见 ROADMAP.md）

**V1.0 版本（2026-02-15 ~ 2026-06-30）：深度学习增值层**
- 基本面数据接入（按 `announce_date` 对齐）
- LSTM/Transformer 模型实现与回测验证
- 完整的 walk-forward 验证流程
- 生产环境部署准备（监控、告警、日志）

**V1.5 版本（2026-07-01 ~ 2026-12-31）：分钟线做T + 风控强化**
- 分钟线数据基础设施
- 盘中做T策略实现
- 多因子融合与因子正交化
- 风控系统升级（Kelly 公式、回撤控制）

**详细规划：** 见 [ROADMAP.md](ROADMAP.md)

---

### 💡 下一步行动建议

#### 立即执行（本周内）

1. **✅ 任务 3 阶段1 已完成（2026-01-08）**
   - ✅ 创建了 `signal.py` 和 `portfolio.py` 模块
   - ✅ 编写了完整的单元测试（16个测试）
   - ✅ Gate 状态：绿色（67 passed）

2. **🚀 继续任务 3 阶段2：换仓门槛与成本覆盖（推荐）**
   ```bash
   # 查看当前配置
   cat configs/protocol.yaml

   # 开始实现阶段2逻辑
   # 1. 在 protocol.yaml 中添加换仓门槛配置
   # 2. 实现 PortfolioManager 的换仓门槛逻辑
   # 3. 编写测试验证低换手效果
   ```

3. **验证当前实现（可选）**
   ```bash
   # 查看新模块的代码
   cat src/ashare_lab/strategy/signal.py
   cat src/ashare_lab/strategy/portfolio.py

   # 运行策略层测试
   pytest tests/test_strategy_signal.py tests/test_strategy_portfolio.py -v
   ```

#### 短期规划（2 周内）

4. 完成任务 3 全部4个阶段（预计剩余1天）
   - 阶段2：换仓门槛与成本覆盖（0.5天）
   - 阶段3：风控行为明确化（0.3天）
   - 阶段4：集成与验证（0.2天）

5. 启动任务 4（回测报告增强）或任务 5（模型接口定义）
   - 两者可以并行进行

#### 中期目标（1-2 月）

6. 完成 V0.5 全部任务（任务 0-6）
7. 整体验收测试 + 文档完善
8. 开始 V1.0 基本面数据调研

---

**最后更新：** 2026-01-08（任务3阶段1完成）
**维护者：** A-share Low-Frequency Lab Team
**长期规划：** 见 [ROADMAP.md](ROADMAP.md)
