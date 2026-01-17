# 选股推荐系统设计文档

## 一、系统定位

**核心目标：** 每日自动推荐Top-N股票（预测次日相对沪深300超额收益最高的股票）

**非目标：**
- ❌ 不做自动交易执行
- ❌ 不做复杂的仓位管理
- ❌ 不需要精确的成本计算

**使用场景：**
- 每天下午收盘后（3:15 PM），系统自动运行
- 生成明日推荐榜单（Top 10股票）
- 用户参考榜单进行投资决策

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                 数据层 (Data Layer)                      │
│  • 日线行情数据（OHLCV）- akshare                         │
│  • 沪深300指数数据（基准）                                │
│  • 股票池过滤（排除ST/科创/创业/北交）                     │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│              特征工程层 (Feature Engineering)             │
│  • 价格特征：return_1d/5d/20d, 振幅                       │
│  • 量价特征：volume_ratio, VWAP                          │
│  • 技术指标：RSI, MACD                                    │
│  • 相对特征：超额收益 vs 沪深300                          │
│  ↓                                                       │
│  序列构造：滑动窗口(seq_len=30) → [batch, 30, n_feat]    │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│                 模型层 (Model Layer)                     │
│  LSTM/Transformer - 预测次日超额收益                      │
│  输入：[batch, seq_len=30, n_feat=8~15]                  │
│  输出：[batch] - 预测的次日超额收益（用于排序）            │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│              推荐引擎 (Recommendation Engine)             │
│  1. 打分排序：按预测超额收益降序排列                       │
│  2. Top-N选择：选取前N只股票（默认N=10）                  │
│  3. 推荐理由：提取关键特征（RSI/动量/成交量）             │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│               输出层 (Output Layer)                      │
│  • 每日推荐榜单（CSV/JSON格式）                           │
│  • 推荐历史记录（可追溯审计）                             │
│  • 推荐验证报告（次日实际涨跌对比）                        │
└─────────────────────────────────────────────────────────┘
```

### 2.1 MTL 架构说明（新增）

- **共享编码器**：单套 Transformer Encoder（4-6 层，seq_len≥30）抽取通用时序表征。
- **三任务回归头**：`head_3d/head_5d/head_10d` 独立线性→GELU→线性，输出对应跨度收益预测。
- **缺失标签掩码**：标签为 NaN 的样本在对应头的 L1 损失中被屏蔽，避免梯度污染。
- **加权损失**：`Loss = w3*L1_3d + w5*L1_5d + w10*L1_10d`，默认 1:1:1，可配置覆盖。
- **warm-start & 冻结**：每日增量训练先加载最近 checkpoint，可按需冻结前 K 层，降低分布漂移风险。

---

## 三、核心功能模块

### 3.1 推荐引擎（RecommendationEngine）

**职责：**
- 调用模型预测
- 按预测值排序
- 选择Top-N股票
- 生成推荐理由

**代码位置：** `src/ashare_lab/recommendation/engine.py`

**输出格式：**
```python
# data/recommendations/20250113.csv
{
    "date": "2025-01-13",
    "recommendations": [
        {
            "rank": 1,
            "symbol": "600519",
            "name": "贵州茅台",
            "predicted_return": 0.0234,  # 预测次日超额收益 2.34%
            "confidence": 0.85,           # 预测置信度
            "reason": "强势动量（20日涨幅18%），RSI=75（超买但仍强势），成交量放大"
        },
        {
            "rank": 2,
            "symbol": "000333",
            "name": "美的集团",
            "predicted_return": 0.0198,
            "confidence": 0.78,
            "reason": "技术面反弹信号，MACD金叉，相对沪深300超额收益显著"
        },
        # ... Top 10
    ]
}
```

### 3.2 推荐验证（RecommendationValidator）

**职责：**
- 次日收盘后，验证推荐准确性
- 计算实际涨跌幅
- 统计命中率、平均收益

**代码位置：** `src/ashare_lab/recommendation/validator.py`

**验证指标：**
```python
{
    "date": "2025-01-13",
    "validation": {
        "top_10_avg_return": 0.0156,      # Top 10平均收益 1.56%
        "benchmark_return": 0.0023,       # 沪深300收益 0.23%
        "excess_return": 0.0133,          # 超额收益 1.33%
        "hit_rate": 0.80,                 # 命中率 80%（10只中8只上涨）
        "top_1_return": 0.0245,           # Top 1实际收益 2.45%
        "top_3_avg_return": 0.0189,       # Top 3平均收益 1.89%
    }
}
```

### 3.3 推荐历史（RecommendationHistory）

**职责：**
- 持久化所有推荐记录
- 提供查询接口（按日期/股票查询）
- 生成历史统计报告

**代码位置：** `src/ashare_lab/recommendation/history.py`

**存储格式：**
```
data/recommendations/
├── history/
│   ├── 20250113.json  # 每日推荐记录
│   ├── 20250114.json
│   └── ...
├── validation/
│   ├── 20250113.json  # 每日验证结果
│   ├── 20250114.json
│   └── ...
└── summary/
    └── monthly_stats.csv  # 月度统计汇总
```

---

## 四、评估指标体系

### 4.0 指标定义（更新）

- **Top-N 命中率**：`hit_rate = count(pred > 0 且 actual > 0) / N`（默认 N=10）。
- **接近度评分**：`score = 1 - MAE(pred, actual)`，结果裁剪至 `[0,1]`，越接近 1 越好。
- **累计收益**：`cum_return = Π(1 + actual_return_i) - 1`，按 Top-N 等权计算。

### 4.1 预测准确性指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| **IC（信息系数）** | 预测值与实际收益的相关性 | > 0.05 |
| **Rank IC** | 预测排名与实际排名的相关性 | > 0.08 |
| **命中率** | 推荐的股票次日上涨的比例 | > 60% |
| **Top-N平均收益** | Top-N股票次日平均收益 | > 沪深300 + 1% |

### 4.2 推荐质量指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| **Top-1准确性** | 第1名股票的实际表现 | 排名前30% |
| **Top-3超额收益** | 前3只股票相对基准的超额收益 | > 2% |
| **尾部风险** | 推荐股票中大跌（<-5%）的比例 | < 10% |
| **稳定性** | 滚动30日命中率标准差 | < 0.15 |

### 4.3 长期表现指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| **月度胜率** | 月度平均收益 > 沪深300的月份占比 | > 70% |
| **累计超额收益** | 长期累计超额收益（vs 沪深300）| > 20%/年 |

### 4.4 增量训练流程图（新增）

```
每日 15:15 触发
   ↓
[Step1] TuShare 增量拉取（start=end=当日，去重写分区）
   ↓
[Step2] 滚动30日特征/标签重算（补齐缺口）
   ↓
[Step3] warm-start 增量训练（加载最近 ckpt，可冻结前 K 层，跑 1-2 epoch）
   ↓
[Step4] 推理生成 Top-10 推荐（过滤 ST/科创）
   ↓
[Step5] 评估前一日推荐（命中率、接近度、累计收益）→ CSV/JSON/HTML 报告
```

---

## 五、简化的回测验证

**目的：** 验证推荐系统的长期表现（不是真实交易回测）

**方法：**
```python
# 简化回测逻辑（不考虑交易细节）

def simple_backtest(recommendations_history):
    """简单回测：假设每天等权买入推荐的Top-10股票"""

    portfolio_values = []

    for date, recs in recommendations_history.items():
        # 假设等权买入Top-10
        top_10_symbols = [r['symbol'] for r in recs[:10]]

        # 获取次日实际收益
        next_day_returns = get_next_day_returns(top_10_symbols, date)

        # 计算当日组合收益（等权平均）
        portfolio_return = np.mean(next_day_returns)
        portfolio_values.append(portfolio_return)

    # 计算累计收益、Sharpe等
    cumulative_return = np.cumprod(1 + np.array(portfolio_values)) - 1
    sharpe = np.mean(portfolio_values) / np.std(portfolio_values) * np.sqrt(252)

    return {
        'cumulative_return': cumulative_return[-1],
        'sharpe_ratio': sharpe,
        'avg_daily_return': np.mean(portfolio_values),
    }
```

**简化点：**
- ❌ 不考虑T+1约束（假设每天都能买卖）
- ❌ 不考虑涨跌停（假设都能成交）
- ❌ 不考虑滑点成本（简化计算）
- ✅ 只关心"推荐准确性"和"长期收益趋势"

---

## 六、每日工作流程

```bash
# 每个交易日下午3:15（收盘后）自动运行

# Step 1: 更新数据
python scripts/update_daily_data.py

# Step 2: 生成推荐
python scripts/generate_daily_recommendations.py \
  --date 20250113 \
  --model-path models/lstm_v1_latest.pt \
  --top-n 10 \
  --output data/recommendations/20250113.json

# Step 3: 验证前一日推荐（如果有）
python scripts/validate_recommendations.py \
  --date 20250112 \
  --output data/recommendations/validation/20250112.json

# Step 4: 生成推荐报告（可选）
python scripts/generate_recommendation_report.py \
  --date 20250113 \
  --output reports/daily_report_20250113.html
```

**Cron配置：**
```bash
# 每个交易日下午3点15分
15 15 * * 1-5 cd /path/to/agents && bash scripts/daily_recommendation_pipeline.sh
```

---

## 七、与现有代码库的关系

### 可以保留的模块 ✅

```
src/ashare_lab/
├── data/                    ✅ 保留（数据获取）
│   ├── akshare_source.py
│   └── index_source.py
├── features/                ✅ 保留（特征工程）
│   ├── momentum.py
│   ├── volume.py
│   └── technical.py (新增)
├── labels/                  ✅ 保留（标签定义）
│   └── excess_return.py
├── dataset/                 ✅ 保留（数据集构建）
│   └── builder.py
├── models/                  ✅ 保留（模型层）
│   ├── base.py
│   ├── lstm_v1.py
│   └── transformer_v2.py
├── training/                ✅ 保留（训练器）
│   └── trainer_v2.py
├── evaluation/              ✅ 保留（评估指标）
│   └── metrics.py
└── universe.py              ✅ 保留（股票池过滤）
```

### 可以简化/替换的模块 🔄

```
src/ashare_lab/
├── backtest/                🔄 简化为简单验证
│   ├── engine.py           → recommendation/validator.py
│   └── book.py             → 不需要（无持仓管理）
├── strategy/                🔄 简化为推荐引擎
│   ├── signal.py           → recommendation/engine.py
│   └── portfolio.py        → 不需要（无仓位管理）
└── reporting.py             🔄 简化为推荐报告
                            → recommendation/report.py
```

### 新增模块 ✨

```
src/ashare_lab/recommendation/  ✨ 新增（推荐系统核心）
├── __init__.py
├── engine.py               # 推荐引擎
├── validator.py            # 推荐验证
├── history.py              # 推荐历史管理
└── report.py               # 推荐报告生成
```

---

## 八、开发优先级

### Phase 1: MVP核心功能（3天）⭐⭐⭐

```
Day 1: 数据 + 特征工程
  - 新增技术指标特征（RSI, MACD）
  - 序列数据集构建（seq_len=30）

Day 2: 模型训练
  - 实现LSTM模型
  - 训练并评估（目标IC > 0.05）

Day 3: 推荐引擎
  - 实现RecommendationEngine
  - 生成首个推荐榜单
```

### Phase 2: 验证与历史（2天）⭐⭐

```
Day 4: 推荐验证
  - 实现RecommendationValidator
  - 验证历史推荐准确性

Day 5: 历史管理
  - 推荐历史持久化
  - 月度统计报告
```

### Phase 3: 自动化与优化（2天）⭐

```
Day 6: 自动化流程
  - 每日推荐Pipeline
  - Cron定时任务

Day 7: 增量训练 + 监控
  - 模型增量训练
  - 性能监控（IC衰减检测）
```

---

## 九、示例输出

### 每日推荐榜单（Markdown格式）

```markdown
# 📊 2025-01-13 选股推荐榜单

**生成时间：** 2025-01-13 15:15:30
**基准指数：** 沪深300
**推荐数量：** Top 10

---

## 🏆 推荐股票列表

| 排名 | 股票代码 | 股票名称 | 预测超额收益 | 置信度 | 推荐理由 |
|------|---------|---------|-------------|--------|---------|
| 1️⃣ | 600519 | 贵州茅台 | +2.34% | 85% | 强势动量（20日涨幅18%），RSI=75，成交量放大 |
| 2️⃣ | 000333 | 美的集团 | +1.98% | 78% | 技术反弹信号，MACD金叉，相对超额收益显著 |
| 3️⃣ | 601318 | 中国平安 | +1.87% | 81% | 估值修复（PB=1.2），成交量温和放大 |
| ... | ... | ... | ... | ... | ... |

---

## 📈 市场环境

- **沪深300今日收盘：** 3,800点 (+0.5%)
- **市场情绪：** 偏强（上涨家数占比65%）
- **北向资金：** 净流入50亿元

---

## ⚠️ 风险提示

1. 本推荐仅供参考，不构成投资建议
2. 股市有风险，投资需谨慎
3. 历史表现不代表未来收益
```

---

## 十、总结

**选股推荐系统 vs 交易回测系统：**

| 维度 | 推荐系统 | 交易系统 |
|------|---------|---------|
| **核心目标** | 预测哪些股票会涨 | 模拟真实交易盈亏 |
| **输出** | 每日推荐榜单 | 权益曲线、Sharpe |
| **复杂度** | 低（只需预测+排序） | 高（T+1/成本/风控） |
| **评估指标** | IC、命中率、Top-N收益 | CAGR、最大回撤、Sharpe |
| **适用场景** | 辅助决策 | 实盘准备 |

**推荐系统的优势：**
- ✅ 开发速度快（3-7天）
- ✅ 功能聚焦（只做预测）
- ✅ 易于理解和使用
- ✅ 避免过度工程化

---

**文档版本：** v1.0
**最后更新：** 2025-01-14
**维护者：** A-share Lab Team
