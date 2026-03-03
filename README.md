# A-share Low-Frequency Lab (A股低频高效交易实验仓库)

目标：用 **日频评估、低换手执行** 的方式，在严格模拟 A 股约束（T+1、涨跌停、成交失败、最低手续费）下，构建可复现的选股与仓位管理研究框架。

## 约束与目标

- 约束：见 `docs/constraints.md`
- 盈利/验收目标：见 `docs/objectives.md`
- 数据契约（内部统一 schema）：见 `docs/data_contract.md`
- 交易协议（信号/成交时点、持有周期、做T策略）：见 `docs/protocol.md`

## Quickstart（V0：先用 akshare 跑通链路）

1) 安装依赖

```bash
conda env create -f environment.yml
conda activate ashare-lab
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python -m pip install -e ".[dev]" --no-deps
python -c "import torch; print('cuda_available=', torch.cuda.is_available())"
```

2) 构建股票池快照（可选，用于全市场回测）

```bash
# 使用当前日期
python scripts/build_universe.py

# 指定日期
python scripts/build_universe.py --date 20241231
```

输出：
- 股票池快照保存到 `data/cache/universe/<date>.csv`
- 包含股票代码、名称等基础信息
- 已过滤 ST/北交/科创/创业板

3) 跑一个最小回测（默认 Top3 动量，日频评估，开盘撮合 + 沪深300超额）

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

- 交易协议：`docs/protocol.md`（信号/成交时点、持有周期、做T策略）
- 协议配置：`configs/protocol.yaml`（可配置参数）
- 数据来源：`docs/data_sources.md`
- 新闻/公告数据建议：`docs/news_sources.md`
- 开发路线图：`NEXT_STEPS.md`
