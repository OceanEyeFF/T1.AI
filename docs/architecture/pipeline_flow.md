# 流水线全链路架构

> MS-R2-001 | 2026-06-23

## 流程概览

```
inputs/                         workspace/                  outputs/
───────                         ──────────                  ────────
inputs/data/cache (TuShare日K+资金流) ──┐
inputs/data/derived (高阶特征) ─┤
pools/ (X:选股策略→股票集合) ───┤
configs/profiles/ (Z:输入维度) ─┤
configs/experiments/ (X×Y×Z) ──┼──→ 训练 ──→ checkpoint ──→ IC报告 ──→ reports/
src/models/ (Y:模型代码) ───────┘         │
                                           ├──→ 筛选 ──→ registry/certified.json
                                           │                 │
                                           └──→ 重训 ←──────┘  (每周滚动)
                                                 │
                                                 └──→ 推理 ──→ predictions/
                                                                   │
                                                           交易策略层 (Layer 2)
```

## 两层模型

### Layer 1：模型验证层（当前）

```
TuShare数据 → 选股池 → 滚动窗口训练 → IC时间序列评估

例：Train(2024全年) → IC(2025W1)
    Fine-tune(2024W2-2025W1) → IC(2025W2)
    持续滚动...

考察：模型在持续重训下，IC能否长期稳定 → 作为选模依据
```

### Layer 2：交易策略层（后续）

```
predictions → 仓位管理 → 模拟盘回测 → 收益归因 → 实盘记录
```

## 日频流水线（5 阶段）

`src/ashare_lab/pipeline/orchestrator/core.py`

| 阶段 | 内容 | 输入 | 输出 |
|------|------|------|------|
| 1. data_refresh | 拉取最新日K数据 | TuShare API | `inputs/data/cache/` |
| 2. recommendation | 模型推理生成 Top-N | checkpoint + 当日数据 | `outputs/predictions/` |
| 3. persistence | 推荐结果持久化 | 推理输出 | `outputs/recommendations.db` |
| 4. validation | 验证前一日预测 vs 实际 | 历史推荐 + 实际行情 | `outputs/reports/` |
| 5. record_metadata | 记录运行元数据 | 全部阶段结果 | `workspace/runs/pipeline_runs.jsonl` |

## 数据流

```
TuShare API ──→ tushare_source.py ──→ inputs/data/cache/ (parquet, 按symbol+year分区)
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     ↓                      ↓                      ↓
              dataset/builder.py    features/ (技术指标)    labels/ (forward return)
                     │                      │                      │
                     └──────────────────────┼──────────────────────┘
                                            ↓
                              training/trainer.py (TrainerConfig + StockDataset)
                                            │
                              ┌─────────────┼─────────────┐
                              ↓             ↓             ↓
                         Transformer     LSTM         XGBoost
                              │             │             │
                              └─────────────┼─────────────┘
                                            ↓
                              evaluation/metrics.py (IC / RankIC / hit rate)
                                            ↓
                              outputs/reports/ (IC时间序列)
```
