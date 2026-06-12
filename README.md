# T1.AI / A-share Low-Frequency Lab

目标：在严格模拟 A 股约束的前提下，构建一套可复现、可审计、可迭代的中短周期研究与执行框架。

当前默认约束包括：

- 只做多，不对冲；
- 严格遵守 `T+1`、涨跌停、成交失败与最低手续费约束；
- 先保证研究口径与执行口径正确，再讨论模型复杂度扩展。

## 当前开发口径（2026-03-10）

当前代码与文档已经收敛到三条明确工作线：

1. **执行层主优先级**
   - 当前最核心工程任务不是继续堆新模型，而是补齐执行层；
   - 重点是换仓门槛、成本覆盖、风险禁买、成交阻断诊断与标准化日志。

2. **主线模型固定为 `3d/5d/10d`**
   - 这是当前默认主 alpha 研究线；
   - 后续主模型开发应围绕这条线推进；
   - 不应把 `1d` 旁路实验直接并入主线默认配置、默认损失或默认报告。
   - 当前推荐层默认先把 `pred_3d/pred_5d/pred_10d` 聚合为单一 `alpha_score`，再进入主线排序。

3. **`1d` 作为独立短周期研究线**
   - `1d` 只回答“是否值得独立存在”；
   - 当前不进入主线交易打分；
   - 实验顺序固定为“先基线、再增量、再换模型、再消融”。

这三条口径的详细说明分别见：

- 当前执行入口：[NEXT_STEPS.md](NEXT_STEPS.md)
- 长期路线入口：[ROADMAP.md](ROADMAP.md)
- 模型线边界：[docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md](docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md)
- 主线 I/O 与聚合输出：[docs/modules/system_io_and_architecture_spec.md](docs/modules/system_io_and_architecture_spec.md)
- `1d` 独立执行策略：[docs/research/1d_independent_model_execution_strategy_20260309.md](docs/research/1d_independent_model_execution_strategy_20260309.md)

## 快速开始

### 1. 安装依赖

```bash
conda env create -f environment.yml
conda activate py311-private
python -m pip install "torch>=2.0"
python -m pip install -e ".[dev]" --no-deps
python -c "import torch; print('cuda_available=', torch.cuda.is_available())"
```

### 2. 构建股票池快照

```bash
# 使用当前日期
python scripts/build_universe.py

# 指定日期
python scripts/build_universe.py --date 20241231
```

输出：

- 股票池快照保存到 `data/cache/universe/<date>.csv`
- 包含股票代码、名称等基础信息
- 已过滤 ST / 北交 / 科创 / 创业板

### 3. 跑一个最小回测

```bash
python scripts/run_backtest.py \
  --symbols 600519,000333,601318 \
  --start 20220101 --end 20241231 \
  --top-n 3
```

输出：

- 终端打印回测摘要（CAGR、最大回撤、换手、成本占比等）
- 若基准可用，打印超额统计（`excess_*`）
- 结果写入 `runs/<timestamp>/`

## 文档入口

建议阅读顺序：

1. [README.md](README.md)
2. [NEXT_STEPS.md](NEXT_STEPS.md)
3. [ROADMAP.md](ROADMAP.md)
4. [docs/README.md](docs/README.md)
5. [docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md](docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md)
6. [docs/modules/system_io_and_architecture_spec.md](docs/modules/system_io_and_architecture_spec.md)
7. [docs/research/多头输出和数据切分.md](docs/research/%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md)
8. [docs/research/1d_independent_model_execution_strategy_20260309.md](docs/research/1d_independent_model_execution_strategy_20260309.md)
9. [docs/interfaces/protocol.md](docs/interfaces/protocol.md)
10. [docs/interfaces/data_contract.md](docs/interfaces/data_contract.md)

分层导航：

- Overview：[docs/overview/README.md](docs/overview/README.md)
- Modules：[docs/modules/README.md](docs/modules/README.md)
- Interfaces：[docs/interfaces/README.md](docs/interfaces/README.md)
- Research：[docs/research/README.md](docs/research/README.md)

## 当前阶段不做的事情

- 不把 `1d` 直接并入默认主线头结构；
- 不让新闻 / 公告 / 外部插件阻塞执行层收敛；
- 不在入口文档继续保留已经过期的旧阶段任务清单。
