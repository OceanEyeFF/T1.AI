# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**A-share Low-Frequency Lab (A股低频高效交易实验仓库)**

这是一个严格模拟 A 股市场约束的量化回测研究框架，专注于**日频评估、低换手执行**的选股与仓位管理策略。

**核心特点：**
- 严格模拟 A 股交易规则（T+1、涨跌停、成交失败、最低手续费）
- 只做多、不对冲、不做 ST/北交/科创/创业板
- 保守成本模型：`max(5元, 成交额 * 0.001)`

## 开发环境设置

### 安装依赖

```bash
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

### 运行回测

最小回测示例（Top3 动量策略 + 沪深300基准对比）：

```bash
python scripts/run_backtest.py \
  --symbols 600519,000333,601318 \
  --start 20220101 --end 20241231 \
  --top-n 3
```

**关键参数：**
- `--symbols`: 逗号分隔的股票代码
- `--start` / `--end`: YYYYMMDD 格式的日期
- `--top-n`: 动量策略选取前 N 只股票
- `--lookback`: 动量计算回溯天数（默认20）
- `--refresh`: 强制重新下载数据（忽略缓存）
- `--benchmark`: 基准指数代码（默认000300沪深300）

**输出位置：** `runs/<timestamp>/`
- `equity.csv` - 权益曲线
- `fills.csv` - 交易明细
- `stats.csv` - 回测统计（CAGR、最大回撤、换手等）
- `diagnostics.csv` - 诊断信息（涨跌停阻断次数、风控触发等）
- `excess.csv` - 超额收益统计

### 运行测试

```bash
pytest tests/
```

单个测试文件：
```bash
pytest tests/test_engine_rules.py -v
```

### 代码质量检查

```bash
ruff check src/ tests/
```

自动修复：
```bash
ruff check --fix src/ tests/
```

## 架构设计

### 核心分层架构

```
src/ashare_lab/
├── types.py              # 核心数据类型：Order, Fill, Side
├── backtest/
│   ├── engine.py        # BacktestEngine - 主回测引擎
│   └── book.py          # PositionBook - 持仓账簿（T+1 可卖管理）
├── strategies/
│   └── momentum.py      # MomentumTopNStrategy - 动量选股策略
├── data/
│   ├── akshare_source.py   # akshare 数据适配器
│   └── index_source.py     # 指数数据适配器
├── universe.py          # 股票池过滤规则（排除ST/科创/北交等）
├── reporting.py         # 超额收益计算与报告生成
└── utils.py            # 价格取整、手数取整等工具函数
```

### 关键设计模式

#### 1. 数据契约（Data Contract）

**所有策略和回测只依赖统一的内部 schema**，与外部数据源解耦。详见 `docs/data_contract.md`。

**必须字段：**
- DataFrame 索引：`date`（datetime64[ns]，升序）
- 列：`open`, `high`, `low`, `close`, `volume`, `amount`
- 复权口径：统一使用前复权（qfq）

#### 2. 策略协议（Strategy Protocol）

所有策略必须实现 `target_weights` 方法：

```python
def target_weights(
    self,
    today: pd.Timestamp,
    history: dict[str, pd.DataFrame],
) -> dict[str, float]:
    """
    Args:
        today: 当前交易日时间戳
        history: {symbol: DataFrame} - 截至 today 之前的历史数据

    Returns:
        {symbol: weight} - 目标权重（sum 应 ≤ 1.0）
    """
```

**重要约束：**
- `history` 仅包含 `today` **之前**的数据（避免未来信息泄露）
- 返回的权重会被转换为目标股数（按 `lot_size=100` 取整）

#### 3. 回测引擎核心流程

`BacktestEngine.run()` 的执行顺序：

```python
for 每个交易日 today:
    # 1. 风控检查
    open_equity = mark_to_market(today, book, cash, price_col="open")
    day_ret = open_equity / prev_close_equity - 1.0
    allow_buy = day_ret > -max_daily_loss  # 单日亏损 > 2% 禁止开新仓

    # 2. 策略信号生成
    targets = strategy.target_weights(today, history_before_today)
    target_shares = weights_to_shares(targets, open_equity)

    # 3. 订单生成与执行
    orders = diff_to_orders(book, target_shares)

    # 先执行卖单（释放资金）
    for sell_order in sell_orders:
        可卖数量 = book.sellable_shares(symbol)  # T+1 约束
        if 跌停或停牌: 阻断成交

    # 后执行买单
    for buy_order in buy_orders:
        if not allow_buy: 跳过（风控触发）
        if 涨停或停牌: 阻断成交

    # 4. 成本计算
    cost = max(5.0, turnover * 0.001)
    cash -= turnover + cost
```

#### 4. T+1 可卖管理（PositionBook）

`PositionBook` 维护两层持仓：
- `sellable: dict[str, int]` - 可卖持仓（前一日及更早买入）
- `today_buys: dict[str, int]` - 当日新买入（T+1 不可卖）

**关键方法：**
- `sellable_shares(symbol)` - 返回当前可卖数量
- `apply_fill(fill)` - 应用成交（买入计入 today_buys，卖出扣减 sellable）
- `new_day()` - 日终结算（today_buys 合并到 sellable）

### 硬约束与验证

#### 股票池过滤规则（`universe.py`）

```python
def is_allowed_a_share_symbol(symbol: str) -> bool:
    # 排除：688*（科创）、300*/301*（创业）、8*/4*（北交）
```

**在所有入口强制验证** - 见 `scripts/run_backtest.py:35`

#### 成交阻断诊断

`diagnostics` 字典记录：
- `buy_blocked_limit_up` - 涨停导致买入失败次数
- `sell_blocked_limit_down` - 跌停导致卖出失败次数
- `sell_blocked_tplus1` - T+1 约束导致卖出失败次数
- `risk_buy_disabled` - 风控触发禁止开仓次数

**这些指标必须在回测报告中显示** - 见 `docs/constraints.md`

## 新增策略指南

### 1. 创建策略类

在 `src/ashare_lab/strategies/` 下新建文件，实现 `target_weights` 方法：

```python
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class YourStrategy:
    param1: float = 0.5
    param2: int = 10

    def target_weights(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        # 实现选股逻辑
        return {symbol: weight}
```

### 2. 数据访问约束

**必须遵守：**
- 仅使用 `history` 中 `today` **之前**的数据
- 禁止使用 `today` 当日的 `close` 价格（未来信息泄露）
- 如需基本面数据，必须使用 `announce_date` 对齐（见 `docs/data_contract.md`）

### 3. 回测集成

修改 `scripts/run_backtest.py` 或创建新脚本：

```python
from ashare_lab.strategies.your_strategy import YourStrategy

strategy = YourStrategy(param1=0.8, param2=20)
result = engine.run(data_by_symbol, strategy=strategy)
```

## 重要文档参考

- `docs/constraints.md` - **策略约束硬规则（必读）**
- `docs/data_contract.md` - 统一数据 schema 规范
- `docs/objectives.md` - 盈利与验收目标
- `docs/data_sources.md` - 数据源选型建议
- `NEXT_STEPS.md` - 功能开发路线图

## 技术栈

- **Python**: ≥ 3.10
- **核心依赖**: pandas ≥ 2.1, numpy ≥ 1.26, akshare ≥ 1.13
- **代码质量**: ruff（line-length=100）
- **测试**: pytest ≥ 8

## 开发原则

1. **数据对齐严格性**: 所有时间序列必须对齐到统一交易日历，禁止前视偏差
2. **成本真实性**: 逐笔扣除成本，报告必须包含成本占比统计
3. **诊断信息透明**: 成交阻断、风控触发等异常情况必须记录并输出
4. **策略可复现性**: 随机种子固定、数据缓存、完整参数记录
5. **最小可行原则**: V0 阶段优先跑通链路，不追求完美精度（如涨跌停价格取整）
