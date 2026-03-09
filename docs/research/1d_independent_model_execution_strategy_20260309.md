# 1d 独立模型完整执行策略（2026-03-09）

## 1. 目标

本文档用于固定 `1d` 独立模型的完整执行策略，回答三个问题：

1. `1d` 应该按什么模型顺序测试；
2. 当前仓库中的日频特征应如何分组与使用；
3. 实验应遵循“先基线、再增量、再换模型、再消融”的什么节奏。

本文档只梳理研究与执行思路，不涉及代码实现。

---

## 2. 总体结论

### 2.1 与主线模型的关系

- 当前主线继续固定为 `3d/5d/10d`；
- `1d` 不再并入主线模型；
- `3d` 继续保留在主线联合头中；
- `1d` 若继续研究，作为**独立短周期实验线**推进。

### 2.2 1d 的模型测试顺序

固定采用三层顺序：

1. `XGBoost + 1d direction`
2. `LSTM + 1d direction`
3. `Transformer + 1d direction`（仅在前两层证明值得继续后再做）

### 2.3 1d 的数据实验顺序

固定采用四阶段顺序：

1. 最小核心基线
2. 分组增量
3. 换模型复核
4. 组级消融

**不采用**“一开始就全量特征”的方式。

---

## 3. 模型路线（按顺序）

## 3.1 Phase M0：XGBoost 基线

### 目标

先回答：`1d` 是否具备最小可行性。

### 模型

- 模型：`XGBoost`
- 任务：`1d direction`
- 形式：二分类

### 标签建议

- 首选：`direction`
- 定义建议：
  - `r1 = close[t+1] / close[t] - 1` 或根据交易协议改为 `next_open_to_open`
  - `y = 1(r1 > 0)`
- 可选去噪版本：
  - `|r1| <= b` 样本过滤
  - `b` 建议 5~10 bps，仅作为扩展，不作为第一轮默认

### 对照

- 唯一对照：`1d close return` 回归
- 作用：验证 direction 是否比回归更稳

### 目的

- 不追求复杂性，只追求最小闭环
- 若这一层不通过门禁，后续不继续上 LSTM / Transformer

---

## 3.2 Phase M1：LSTM 复核

### 前提

仅当 XGBoost 证明 `1d` 值得继续时，才进入这一层。

### 模型

- 模型：`LSTM`
- 任务：仍为 `1d direction`
- 输入数据组：沿用 XGBoost 阶段中表现最好的那一组

### 目的

- 判断时序建模是否带来额外稳定收益
- 不在此阶段扩大特征面

---

## 3.3 Phase M2：Transformer 后置验证

### 前提

仅当以下条件同时满足时再做：

1. `1d` 方向模型已证明值得长期研究；
2. XGBoost 与 LSTM 都跑完；
3. 样本量、计算预算、实验窗口都允许继续扩展。

### 目的

- 不是为了“更先进”，而是为了验证更复杂结构是否真正带来增益
- 不作为 `1d` 的第一选择

---

## 4. 当前仓库可用的日频数据分组

## 4.1 基础核心组（默认第一组）

这是 `1d` 的首轮最小输入集合，优先使用。

### 价格动量与趋势

- `return_1d`
- `return_5d`
- `return_10d`
- `return_20d`
- `return_60d`
- `price_slope_5d`
- `price_slope_20d`

### 成交量与活跃度

- `volume_ratio_5d`
- `relative_volume`
- `volume_change`
- `amount_change`

### 技术指标

- `rsi_14`
- `macd_line`
- `macd_signal`
- `macd_hist`
- `bollinger_deviation`

### 说明

- 这是最接近当前公共主干的基础日频特征集合；
- `1d` 首轮实验以此为主，不再额外掺入资金流、估值、商品、ETF 等扩展项。

---

## 4.2 市场状态组（第一层增量）

- `market_mom_5d`
- `market_vol_20d`
- `market_amount_z20`

### 作用

- 提供市场环境上下文；
- 用于验证 `1d` 是否需要 regime-aware 输入。

---

## 4.3 短线增强组（第二层增量）

该组来自当前 `dim52/no_hist_hl` 体系中的短线结构化特征。

### 换手与微观活跃度

- `turnover_rate`
- `turnover_rate_f`
- `turnover_spread`
- `turnover_rate_z20`
- `db_volume_ratio`
- `db_volume_ratio_z20`

### 估值与规模

- `pe_ttm_z20`
- `pb_z20`
- `ps_ttm_z20`
- `dv_ttm`
- `total_mv_log`
- `circ_mv_log`
- `float_share_ratio`

### 资金流结构

- `mf_net_amount_ratio`
- `mf_net_amount_abs_ratio`
- `mf_md_amount_ratio`
- `mf_lg_amount_ratio`
- `mf_elg_amount_ratio`
- `mf_buy_pressure_amount`
- `mf_buy_pressure_vol`
- `mf_flow_concentration`
- `mf_net_amount_z20`
- `mf_net_amount_impulse`
- `mf_large_amount_ratio`
- `mf_retail_amount_ratio`
- `mf_large_retail_spread`

### 资金流动量

- `mf_net_amount_ratio_ma5`
- `mf_net_amount_ratio_ma10`
- `mf_net_amount_ratio_mom5`
- `mf_net_amount_ratio_mom10`
- `mf_large_amount_ratio_ma5`
- `mf_large_amount_ratio_mom5`
- `mf_retail_amount_ratio_ma5`
- `mf_buy_pressure_amount_ma5`
- `mf_activity_ratio_20d`

### 说明

- 这是 `1d` 更可能受益的一层增强，因为其与短线行为更接近；
- 但不能一开始就并入，避免噪声和维度一同放大。

---

## 4.4 市场外额外数据组（最后层增量）

- 国际商品因子
- 国内期货商品因子
- ETF 或其他外部市场 proxy

### 说明

- 该组在当前 `3d/5d/10d` 主线中已被证明默认并入不成立；
- 因此对 `1d` 也只作为**最后一层**增量验证，而不是默认输入。

---

## 5. 数据实验顺序

## 5.1 Phase D0：最小基线

### 固定做法

- 模型：`XGBoost + 1d direction`
- 数据：仅使用“基础核心组”
- 不加市场状态组
- 不加短线增强组
- 不加市场外额外数据组

### 目的

- 先确认 `1d` 任务本身是否有最小生命力；
- 若连最小基线都不成立，则停止扩展。

---

## 5.2 Phase D1：分组增量

按以下固定顺序逐层增加输入：

1. 基础核心组
2. 基础核心组 + 市场状态组
3. 基础核心组 + 市场状态组 + 短线增强组
4. 基础核心组 + 市场状态组 + 短线增强组 + 市场外额外数据组

### 原则

- 一次只加一层；
- 不允许同时改模型和改数据；
- 每一层都要与前一层做同窗比较。

---

## 5.3 Phase D2：固定数据组后换模型

### 流程

- 先用 XGBoost 找到“最优数据组”；
- 然后在同一数据组上跑 LSTM；
- Transformer 仅在后置阶段进入。

### 目的

- 避免将“数据变化”和“模型变化”混为一谈；
- 保证结论可归因。

---

## 5.4 Phase D3：组级消融

### 原则

只对已选定的“最佳候选配置”做消融。

### 消融顺序

1. 市场外额外数据组
2. 短线增强组
3. 市场状态组
4. 必要时再对组内子集做细粒度消融

### 不建议

- 一开始做逐字段消融；
- 一开始对所有特征做全排列搜索。

---

## 6. 为什么不是“先全数据再做消融”

不建议 `1d` 一开始直接上全量数据，原因如下：

1. `1d` 本身噪声大；
2. 全量特征会把噪声、冗余、冲突目标一起放大；
3. 若结果不好，无法快速判断问题出在：
   - 模型
   - 标签
   - 特征组
   - 外部数据
4. 研究阶段的首要目标是**可归因**，不是一开始就追求“最高值”。

因此固定策略为：

- 先最小基线；
- 再逐层增量；
- 再换模型；
- 最后才做消融与外部数据复核。

---

## 7. 评估与门禁建议

## 7.1 统计层

- AUC
- Balanced Accuracy
- MCC
- Brier Score

## 7.2 横截面交易层

- 日频 TopQ next-day 平均收益
- Top-Bottom spread
- Hit Rate
- Turnover

## 7.3 研究态门禁

### 硬门禁

1. 多数滚动窗口中 AUC > 0.52；
2. Top-Bottom spread 均值为正；
3. 成本后仍为正。

### 软门禁

至少满足 2 条：

1. MCC 持续为正；
2. Brier 相对无信息基线稳定改善；
3. 高波动区间内性能降幅可控。

---

## 8. 当前固定执行策略（一句话版本）

`1d` 的执行路线固定为：

1. 先做 `XGBoost + 1d direction + 基础核心组`
2. 再按“市场状态 -> 短线增强 -> 市场外数据”逐层加数据
3. 再在最优数据组上测试 `LSTM`
4. `Transformer` 后置
5. 最后只对最佳组合做组级消融

---

## 9. 当前不做的事项

- 不做 `1d high/low/close` 三头混训
- 不把 `1d` 并回 `3d/5d/10d` 主线
- 不在第一轮就使用全量特征
- 不在第一轮就做外部市场数据常驻输入
