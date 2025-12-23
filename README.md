# A-share Low-Frequency Lab (A股低频高效交易实验仓库)

目标：用 **日频评估、低换手执行** 的方式，在严格模拟 A 股约束（T+1、涨跌停、成交失败、最低手续费）下，构建可复现的选股与仓位管理研究框架。

## 约束与目标

- 约束：见 `docs/constraints.md`
- 盈利/验收目标：见 `docs/objectives.md`
- 数据契约（内部统一 schema）：见 `docs/data_contract.md`

## Quickstart（V0：先用 akshare 跑通链路）

1) 安装依赖

```bash
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

2) 跑一个最小回测（默认 Top3 动量，日频评估，开盘撮合 + 沪深300超额）

```bash
python scripts/run_backtest.py \
  --symbols 600519,000333,601318 \
  --start 20220101 --end 20241231 \
  --top-n 3
```

输出：
- 终端打印回测摘要（CAGR、最大回撤、换手、成本占比等）
- 若基准可用，打印超额统计（`excess_*`）
- 结果写入 `runs/<timestamp>/`（权益曲线、交易明细）

## 重要说明（新手必读）

- 本仓库默认 **只做多**、**不对冲**、**不做 ST/北交/科创/创业板**。
- 成本使用保守口径：`max(5元, 成交额 * 0.001)`（总摩擦成本），并在回测中逐笔扣除。
- 日频策略不等于每天都大量交易：默认会加入“换仓门槛/触发阈值”，避免小优势被成本吞掉。

## 文档入口

- 数据来源：`docs/data_sources.md`
- 新闻/公告数据建议：`docs/news_sources.md`
