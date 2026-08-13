# 本地模拟交易盘使用指南

> 2026-07-16 | `ashare_lab.sim`

面向**小资金、低频、盘前锁计划**的本地限价模拟盘。不依赖 tick 数据，用日线 OHLCV 回放「挂单 → 成交 → 记账」全流程。

---

## 适用场景

| 适合 | 不适合 |
|------|--------|
| 开盘前定好买/卖价，盘中不改单 | 盘中追价、改单、高频 |
| 验证策略在 A 股规则下的可执行性 | 精确复现集合竞价排队顺序 |
| 小资金（佣金最低 5 元、整手）敏感度测试 | 需要 tick 级滑点建模 |

与现有 `BacktestEngine`（按目标权重、开盘价调仓）互补：研究回测用后者；**「明天挂什么限价单」**用本模块。

---

## 模块结构

```
src/ashare_lab/sim/
├── types.py        # LimitOrder, DailyBar, DayMatchResult
├── fill_model.py   # daily_ohlc_v1 纯撮合规则（无账户状态）
├── broker.py       # PaperBroker：现金、持仓、T+1、费用
└── replay.py       # ReplayEngine：按交易日回放 + PlanProvider 协议
```

生活类比：

- **LimitOrder** — 盘前写在小本子上的挂单
- **PaperBroker** — 模拟券商账户（钱、股、手续费）
- **ReplayEngine** — 用历史行情一天一天往前推，每天收盘对账

---

## 快速开始（CLI）

依赖已缓存的日线数据（与 `run_backtest.py` 同源，经 `DataLake` → TuShare）：

**缓存布局**（`--cache-dir`，默认 `inputs/data/cache`）：

| 类型 | 路径 |
|------|------|
| 指数（HS300 等） | `{cache_dir}/index_{code}_daily_{start}_{end}.csv` |
| TuShare 分区 | `{cache_dir}/tushare_qfq/{ts_code}/year=YYYY/part.parquet` |

```bash
conda activate py311-private

python scripts/run_sim_replay.py \
  --symbol 600519 \
  --start 20240101 \
  --end 20240630 \
  --cash 20000 \
  --shares 100
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--symbol` | （必填） | 6 位 A 股代码 |
| `--start` / `--end` | （必填） | `YYYYMMDD` |
| `--cash` | `20000` | 初始资金（建议用真实量级） |
| `--shares` | `100` | 演示策略每次买入手数 |
| `--cache-dir` | `inputs/data/cache` | 日线缓存目录 |
| `--out-dir` | `outputs/sim` | 回放结果输出根目录 |
| `--refresh` | off | 忽略缓存重新拉数 |

### 输出文件

每次运行在 `outputs/sim/replay_{symbol}_{timestamp}/`：

| 文件 | 内容 |
|------|------|
| `equity.csv` | 日终权益、现金（index = 交易日） |
| `fills.csv` | 成交明细（价、量、费用） |
| `rejects.csv` | 未成交及原因 |
| `diagnostics.csv` | 汇总计数（计划单数、成交数、拒单数） |

脚本内置 `PrevCloseLimitPlanner` 仅为**管道演示**（空仓按昨收挂买、有仓按昨收×1.01 挂卖），不是生产策略。

---

## Python API

### 1. 单日撮合（最小单元）

```python
from ashare_lab.sim import DailyBar, LimitOrder, PaperBroker, SimConfig, match_limit_daily_ohlc

# 纯规则：今天这根 K 线，我的限价单能不能成交？
bar = DailyBar(open=10.0, high=10.3, low=9.8, close=10.1, volume=1_000_000, prev_close=10.0)
order = LimitOrder(symbol="600519", side="BUY", shares=100, limit_price=10.0)
touch = match_limit_daily_ohlc(order, bar)
# touch.shares, touch.price, touch.reason_if_zero

# 带账户：提交 → 当日撮合
broker = PaperBroker(SimConfig(initial_cash=20_000))
broker.submit([order])
result = broker.match_day(date(2024, 1, 3), {"600519": bar})
```

### 2. 历史回放

```python
from datetime import date
import pandas as pd

from ashare_lab.sim import (
    LimitOrder,
    PaperBroker,
    ReplayConfig,
    ReplayEngine,
    ScriptedPlanner,
    SimConfig,
)

# data_by_symbol: {symbol: DataFrame}，index=date，列含 open/high/low/close/volume
planner = ScriptedPlanner({
    date(2024, 1, 3): [LimitOrder("600519", "BUY", 100, 10.0)],
    date(2024, 1, 4): [LimitOrder("600519", "SELL", 100, 10.2)],
})

broker = PaperBroker(SimConfig(initial_cash=20_000, max_participation=1.0))
result = ReplayEngine(ReplayConfig(sim=SimConfig(max_participation=1.0))).run(
    {"600519": df},
    planner=planner,
    broker=broker,
)

result.equity_curve   # 权益曲线
result.fills          # 全部成交
result.rejects        # 拒单明细
result.diagnostics    # 计数
```

### 3. 自定义盘前计划（PlanProvider）

实现 `plans(today, prev_date, history, broker) -> list[LimitOrder]`：

- `today`：当前回放交易日
- `prev_date`：上一交易日（首日为 `None`）
- `history`：各标的 **截至 prev_date（含）** 的 K 线 — **严禁使用 today 的 bar**
- `broker`：当前模拟账户（可读现金、持仓）

```python
class MyPlanner:
    def plans(self, today, prev_date, history, broker):
        if prev_date is None:
            return []
        # 只用 history 里截至昨天的数据做决策
        ...
        return [LimitOrder(...)]
```

回放引擎每个交易日顺序：**plans → submit → match_day → 日终按收盘价估值**。

---

## 成交模型 `daily_ohlc_v1`

无 tick、无排队，用当日 OHLC 近似「限价有没有被碰到」。

| 规则 | 说明 |
|------|------|
| 买入触及 | `low <= limit_price` |
| 卖出触及 | `high >= limit_price` |
| 成交价（跳空） | 买：`min(limit, open)`；卖：`max(limit, open)` |
| 涨停开盘 | 买入拒单 `buy_blocked_limit_up` |
| 跌停开盘 | 卖出拒单 `sell_blocked_limit_down` |
| T+1 | 当日买入不可当日卖出 |
| 整手 | 100 股向下取整 |
| 费用 | `max(5元, 成交额 × 0.1%)`，默认费率见 `SimConfig` |
| 量能上限 | 默认最多成交当日成交量的 5%（`max_participation`） |
| 当日未成交 | 订单作废，**不自动顺延**到下一日 |

`ReplayConfig.volume_in_lots=True`（默认）时，将 TuShare 日线 `volume` 从「手」换算为「股」（×100）。

### 拒单原因一览

`missing_bar` · `invalid_bar` · `not_touched` · `buy_blocked_limit_up` · `sell_blocked_limit_down` · `sell_blocked_tplus1` · `insufficient_cash` · `insufficient_volume` · `zero_lot`

---

## SimConfig 默认值

```python
SimConfig(
    initial_cash=20_000.0,
    lot_size=100,
    total_friction_rate=0.001,   # 0.1%
    min_cost_rmb=5.0,
    max_participation=0.05,      # 5% 日成交量
    board_limit_pct=0.10,        # 主板涨跌停 10%
)
```

小资金回测务必用真实初始资金；`min_cost_rmb=5` 对万元级账户影响显著。

---

## 与数据湖 / 回测的关系

```
inputs/data/cache/
  index_*.csv        ← 指数日线
  tushare_qfq/       ← TuShare 分区湖（canonical）
        ↓ DataLake
ReplayEngine + PlanProvider
        ↓
outputs/sim/           ← 模拟账户流水（fills / equity / rejects）
```

- **数据输入**：`dict[str, pd.DataFrame]`，与 `BacktestEngine.run()` 相同形状
- **输出区**：遵守三区模型，模拟结果放 `outputs/sim/`，不放 `workspace/`
- **研究层**：Layer 1 模型产出信号后，可由 PlanProvider 消费并生成限价单（后续接入点）

---

## 测试

```bash
pytest tests/unit/sim/ -q
```

覆盖：触及/未触及、跳空、涨跌停、T+1、最低佣金、回放防偷看、量能换算。

---

## 已知局限

1. **无集合竞价排队**：开盘价仅用于跳空成交价与涨跌停判断，不模拟 9:15–9:25 委托队列。
2. **无分钟路径**：无法区分「先触买价再触卖价」的日内顺序；若同日买卖，引擎先卖后买（与 `PaperBroker.match_day` 一致）。
3. **首日无 prev_close**：日历第一个交易日无法构造 `DailyBar`，当日计划会 `missing_bar`。
4. **停牌**：未单独建模；缺 bar 视为不可成交。

有分钟线后可新增 `fill_model` 版本，回放接口不变。

---

## 相关文档

- [daily_pipeline_ops.md](daily_pipeline_ops.md) — 日频研究流水线
- [../reference/data_contract.md](../reference/data_contract.md) — 数据字段契约
- [../architecture/repo_structure_guide.md](../architecture/repo_structure_guide.md) — `outputs/` 输出区规范
