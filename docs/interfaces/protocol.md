# 交易协议（Trading Protocol）

本文档定义 A-share Low-Frequency Lab 的交易执行协议，明确"什么时候产生信号、什么时候成交、持有多久、如何调仓"等核心时序约定。

**目标：** 避免模型与策略返工，确保回测链路与实盘逻辑一致，防止未来信息泄露。

---

## 1. 信号时点（Signal Generation Time）

### 默认口径（V0/V1）

- **时点：** 收盘后计算信号
- **可用信息集合：** t 日（当日）的 `close`、`volume`、`amount` 等收盘数据可用
- **不可用信息：** t+1 日的任何数据（包括开盘价）

### 技术实现

- 策略 `target_weights(today, history)` 方法中：
  - `today` 为当前交易日时间戳（如 2024-01-15）
  - `history` 字典中每只股票的 DataFrame **仅包含 `today` 之前的数据**（不包含 `today` 当日）
  - 策略可以使用 `today` 参数查找外部数据（如公告、新闻），但必须使用 `today` 收盘后可获得的信息

### V2 扩展规划

- 支持盘中信号（分钟线）：需要明确定义"盘中可用信息集合"（避免使用未来分钟数据）
- 配置项：`signal_time_mode: ["close", "intraday"]`

---

## 2. 成交时点（Execution Time）

### 默认口径（V0/V1）

- **时点：** 次日开盘成交（t+1 日 `open` 价格）
- **延迟：** 从信号产生（t 日收盘后）到实际成交（t+1 日开盘），存在 **1 个交易日的延迟**
- **价格：** 使用 t+1 日的 `open` 价格作为成交价

### 成交规则

#### 买入成交条件

1. **资金充足：** 可用现金 ≥ 目标买入金额 + 手续费
2. **非涨停：** t+1 日开盘价未触及涨停价（`open < limit_up`）
3. **非停牌：** t+1 日未停牌（`is_halt == False`）
4. **风控允许：** 未触发单日最大亏损阈值（见风控协议）

**成交失败处理：**
- 记录诊断信息：`buy_blocked_limit_up`（涨停阻断）、`buy_blocked_halt`（停牌阻断）、`risk_buy_disabled`（风控阻断）
- 订单取消，现金保留

#### 卖出成交条件

1. **可卖数量充足：** 满足 T+1 约束（见 `PositionBook.sellable_shares`）
2. **非跌停：** t+1 日开盘价未触及跌停价（`open > limit_down`）
3. **非停牌：** t+1 日未停牌

**成交失败处理：**
- 记录诊断信息：`sell_blocked_limit_down`（跌停阻断）、`sell_blocked_tplus1`（T+1 约束阻断）
- 订单取消,持仓保留

### V2 扩展规划

- 支持盘中成交（分钟线）：信号产生后 N 分钟内成交
- 支持收盘成交：t 日收盘后产生信号 → t 日收盘价成交（需验证实盘可行性）
- 配置项：`execution_time_mode: ["next_open", "next_close", "intraday"]`

---

## 3. 持有周期（Holding Period）

### 默认口径（V0/V1）

- **持有策略：** 持有到下一次调仓信号产生
- **调仓频率：** 每个交易日评估一次（但不一定每天都调仓）
- **换仓门槛：** 建议引入"优势阈值"，仅当新候选相对当前持仓的分数优势超过阈值时才换仓（降低成本侵蚀）

### 最小持有期（可选约束）

- V0 不强制，V1 可配置：
  - `min_holding_days: int` - 最小持有天数（如 5 个交易日）
  - 目的：避免高频换手，降低成本

### V2 扩展规划

- 支持日内持有：盘中买入 → 尾盘卖出（需分钟线数据）
- 支持固定周期调仓：每周/每月调仓一次
- 配置项：`rebalance_frequency: ["daily", "weekly", "monthly"]`

---

## 4. 做T策略（Intraday Trading）

### V1 日线版本（当前）

**约束：**
- **不做真实日内 T：** 由于只有日线数据，无法实现盘中买入 → 盘中卖出
- **保留撮合能力：** 支持"先卖后买回"（但仅限同一标的，且必须满足 T+1 可卖约束）

**实现示例：**
- t 日收盘后：策略信号要求"降低某只股票 A 的仓位至 50%"
- t+1 日开盘：卖出 50% 的 A（释放资金）
- 同时买入其他标的（使用卖出释放的资金）

**限制：**
- 当日买入的股票当日不可卖出（T+1 约束）
- 无法实现"盘中低买高卖"

### V2 分钟线版本（未来）

**目标：**
- 引入分钟线数据（1min/5min）
- 支持盘中信号生成与成交
- 支持"盘中卖出 → 盘中/尾盘买回"的做 T 策略

**实现步骤（规划）：**
1. 数据层：扩展 `data_contract.md`，定义分钟线 schema
2. 策略层：支持盘中信号生成（`intraday_signal` 方法）
3. 回测层：支持分钟级撮合与 T+1 约束验证
4. 配置项：`enable_intraday_trading: bool`

---

## 5. 可用信息集合（Information Set）

### 时序对齐原则

**严格防穿越：** 策略在 t 时刻只能使用 t 时刻之前可获得的信息。

### 行情数据

| 数据类型       | t 日收盘后可用 | t+1 日开盘前可用 | 备注                          |
|----------------|----------------|------------------|-------------------------------|
| t 日 OHLC      | ✅              | ✅                | t 日收盘后可用                |
| t 日 volume    | ✅              | ✅                | t 日收盘后可用                |
| t+1 日 open    | ❌              | ❌                | 仅在 t+1 日开盘后可用（成交时）|
| t+1 日 close   | ❌              | ❌                | 未来信息，严禁使用            |

### 基本面数据

| 数据类型       | 对齐口径                          | 备注                          |
|----------------|-----------------------------------|-------------------------------|
| 财务报表       | 按 `announce_date` 对齐           | 禁止使用报表期末日期回填      |
| 财务指标       | 同上                              | V0 不接，V1 接入              |

### 公告/新闻数据

| 数据类型       | 对齐口径                          | 备注                          |
|----------------|-----------------------------------|-------------------------------|
| 公告           | 按 `event_time`（发布时间）对齐   | 原文必须存档，支持复跑        |
| 新闻           | 按 `publish_time` 对齐            | 警惕数据源时间戳不准确问题    |

---

## 6. 调仓逻辑（Rebalancing Logic）

### 执行顺序（关键！）

在 t+1 日开盘时，按以下顺序执行订单：

1. **卖出订单优先：** 先执行卖出订单（释放资金和持仓）
2. **买入订单后执行：** 使用卖出后的可用现金执行买入订单

**原因：**
- A 股不支持融资买入（无法先买后卖）
- 必须先释放资金才能用于新标的买入

### 订单生成规则

`BacktestEngine.run()` 中订单生成逻辑：

```python
# 1. 计算目标持仓（策略输出权重 → 转换为目标股数）
target_shares = weights_to_shares(target_weights, open_equity)

# 2. 对比当前持仓，生成订单
orders = diff_to_orders(current_book, target_shares)

# 3. 分离买卖订单
sell_orders = [o for o in orders if o.side == Side.SELL]
buy_orders = [o for o in orders if o.side == Side.BUY]

# 4. 先执行卖单
for order in sell_orders:
    execute_with_constraints(order)  # 检查 T+1、跌停、停牌

# 5. 后执行买单
for order in buy_orders:
    execute_with_constraints(order)  # 检查资金、涨停、停牌、风控
```

---

## 7. 风控协议（Risk Control）

### 单日最大亏损阈值

- **阈值：** 2%（从前一日收盘权益计算）
- **计算时点：** t+1 日开盘时，按 `open` 价格 mark-to-market
- **触发后行为：**
  - 停止开新仓（买入订单全部取消）
  - 仅允许降风险（卖出订单正常执行）
  - 记录诊断信息：`risk_buy_disabled`

### 成交失败记录

回测必须记录以下诊断信息（输出到 `diagnostics.csv`）：

| 指标                       | 含义                          |
|----------------------------|-------------------------------|
| `buy_blocked_limit_up`     | 涨停导致买入失败次数          |
| `buy_blocked_halt`         | 停牌导致买入失败次数          |
| `sell_blocked_limit_down`  | 跌停导致卖出失败次数          |
| `sell_blocked_tplus1`      | T+1 约束导致卖出失败次数      |
| `risk_buy_disabled`        | 风控触发禁止开仓次数          |

---

## 8. 配置文件（Configuration）

交易协议参数通过 `configs/protocol.yaml` 配置，支持以下选项：

```yaml
# 信号与成交时点
signal_time_mode: "close"          # 信号生成时点：close（收盘后）
execution_time_mode: "next_open"   # 成交时点：next_open（次日开盘）

# 持有周期
rebalance_frequency: "daily"       # 调仓频率：daily（每日评估）
min_holding_days: null             # 最小持有天数（null 表示无限制）

# 换仓门槛（降低成本）
enable_rebalance_threshold: true   # 是否启用换仓门槛
rebalance_score_threshold: 0.05    # 新候选相对当前持仓的分数优势阈值
min_expected_excess: 0.003         # 最小预期边际收益（应覆盖 N 倍成本）

# 做 T 策略
enable_intraday_trading: false     # 是否启用日内做 T（V1 不支持）

# 风控
max_daily_loss: 0.02               # 单日最大亏损阈值（2%）
risk_control_mode: "stop_buy"      # 风控触发后行为：stop_buy（停止开仓）

# 成本模型
min_commission: 5.0                # 最低手续费（RMB）
commission_rate: 0.001             # 手续费费率（千分之一）
```

---

## 9. 版本演进路线图

### V0（当前）

- ✅ 日线数据
- ✅ 收盘后信号 → 次日开盘成交
- ✅ T+1 约束、涨跌停阻断
- ✅ 单日亏损阈值风控

### V1（规划中）

- [ ] 换仓门槛与成本覆盖阈值
- [ ] 最小持有期配置
- [ ] 基本面数据接入（按 `announce_date` 对齐）

### V2（未来）

- [ ] 分钟线数据支持
- [ ] 盘中信号生成与成交
- [ ] 日内做 T 策略
- [ ] 动态调仓频率（周频/月频）

---

## 10. 相关文档

- **约束规则：** `docs/interfaces/constraints.md`
- **数据契约：** `docs/interfaces/data_contract.md`
- **目标验收：** `docs/interfaces/objectives.md`
- **回测引擎：** `src/ashare_lab/backtest/engine.py`
- **配置示例：** `configs/protocol.yaml`
