# 免费特征扩展指南

**适用于：** TuShare 免费用户（120积分）

本指南介绍如何**仅使用日线行情数据（OHLCV）**扩展更多技术指标特征，无需额外积分。

---

## ✅ 当前已实现的6个特征

| 特征名称 | 计算方式 | 数据来源 |
|---------|---------|---------|
| `return_1d` | `close[t-1] / close[t-2] - 1` | close |
| `return_5d` | `close[t-1] / close[t-6] - 1` | close |
| `return_20d` | `close[t-1] / close[t-21] - 1` | close |
| `volume_ratio` | `volume[t-1] / mean(volume[t-6:t-1])` | volume |
| `volume_change` | `volume[t-1] / volume[t-2] - 1` | volume |
| `amount_change` | `amount[t-1] / amount[t-2] - 1` | amount |

**数据来源：** TuShare `daily` 接口（免费）

---

## 🎯 可免费添加的技术指标（仅用OHLCV）

### 优先级1：经典技术指标 ⭐⭐⭐

#### 1. RSI（相对强弱指标）

**计算公式：**
```python
delta = close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(span=14).mean()
avg_loss = loss.ewm(span=14).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
```

**预期IC提升：** +0.005 ~ +0.01

**已实现：** ✅ `src/ashare_lab/features/technical.py - RSI`

---

#### 2. MACD（趋势指标）

**计算公式：**
```python
ema_12 = close.ewm(span=12).mean()
ema_26 = close.ewm(span=26).mean()
macd_line = ema_12 - ema_26
macd_signal = macd_line.ewm(span=9).mean()
macd_hist = macd_line - macd_signal
```

**预期IC提升：** +0.005 ~ +0.01

**已实现：** ✅ `src/ashare_lab/features/technical.py - MACDLine/Signal/Hist`

---

#### 3. 布林带偏离度

**计算公式：**
```python
rolling_mean = close.rolling(20).mean()
rolling_std = close.rolling(20).std()
bollinger_deviation = (close - rolling_mean) / rolling_std  # Z-score
```

**预期IC提升：** +0.003 ~ +0.008

**已实现：** ✅ `src/ashare_lab/features/technical.py - BollingerDeviation`

---

### 优先级2：价格形态特征 ⭐⭐

#### 4. 价格斜率（趋势强度）

**计算公式：**
```python
log_price = np.log(close)
# 对时间做线性回归，斜率表示趋势强度
slope = np.polyfit(range(20), log_price[-20:], 1)[0]
```

**预期IC提升：** +0.005 ~ +0.01

**已实现：** ✅ `src/ashare_lab/features/price_slope.py - PriceSlope`

---

#### 5. 历史波动率

**计算公式：**
```python
returns = close.pct_change()
volatility = returns.rolling(20).std() * np.sqrt(252)  # 年化波动率
```

**预期IC提升：** +0.003 ~ +0.008

**已实现：** ❌ 待创建

---

#### 6. 振幅特征

**计算公式：**
```python
amplitude = (high - low) / close  # 当日振幅
avg_amplitude = amplitude.rolling(20).mean()  # 平均振幅
```

**预期IC提升：** +0.003 ~ +0.005

**已实现：** ❌ 待创建

---

### 优先级3：量价关系特征 ⭐

#### 7. 量价背离度

**计算公式：**
```python
price_change = close.pct_change()
volume_change = volume.pct_change()
correlation = price_change.rolling(20).corr(volume_change)
divergence = 1 - abs(correlation)  # 背离度（0-2）
```

**预期IC提升：** +0.003 ~ +0.005

**已实现：** ❌ 待创建

---

#### 8. 成交额占比

**计算公式：**
```python
amount_ratio = amount / amount.rolling(20).mean()
```

**预期IC提升：** +0.002 ~ +0.004

**已实现：** ❌ 待创建（类似 volume_ratio）

---

### 优先级4：K线形态特征 ⭐

#### 9. 实体比例

**计算公式：**
```python
body = abs(close - open)
range_ = high - low
body_ratio = body / range_  # 实体占振幅的比例
```

**预期IC提升：** +0.002 ~ +0.003

**已实现：** ❌ 待创建

---

#### 10. 上下影线比例

**计算公式：**
```python
upper_shadow = high - max(open, close)
lower_shadow = min(open, close) - low
shadow_ratio = upper_shadow / lower_shadow
```

**预期IC提升：** +0.002 ~ +0.003

**已实现：** ❌ 待创建

---

## 📊 特征扩展路线图

### 阶段1：当前（6个特征）✅

**已实现：**
- return_1d/5d/20d
- volume_ratio/change
- amount_change

**模型表现预期：** IC ~ 0.04 - 0.05

---

### 阶段2：添加经典技术指标（10个特征）⭐⭐⭐

**新增：**
- RSI(14) ✅ 已实现
- MACD(12,26,9) ✅ 已实现
- 布林带偏离度 ✅ 已实现
- 价格斜率 ✅ 已实现

**模型表现预期：** IC ~ 0.05 - 0.06

**工作量：** 0天（已实现，只需集成到数据集构建）

---

### 阶段3：添加波动率和量价特征（13个特征）⭐⭐

**新增：**
- 历史波动率
- 振幅特征
- 量价背离度

**模型表现预期：** IC ~ 0.06 - 0.07

**工作量：** 0.5天

---

### 阶段4：添加K线形态特征（15个特征）⭐

**新增：**
- 实体比例
- 上下影线比例

**模型表现预期：** IC ~ 0.07 - 0.08

**工作量：** 0.5天

---

## 🚀 立即可用的增强版脚本

浮浮酱可以立即帮主人创建增强版的数据集构建脚本，集成所有**已实现**的技术指标（10个特征）。

**命令：**
```bash
python scripts/build_sequence_dataset_enhanced.py \
  --start 20240101 \
  --end 20241231 \
  --symbols-csv data/universe.csv \
  --source tushare \
  --seq-len 30 \
  --output-dir data/datasets
```

**新增特征：**
- ✅ RSI(14)
- ✅ MACD Line
- ✅ MACD Signal
- ✅ MACD Hist
- ✅ 布林带偏离度
- ✅ 价格斜率(20d)

**预期提升：**
- 特征数：6 → 12
- 预测IC：0.04-0.05 → 0.05-0.06

---

## 💡 最佳实践建议

### 1. 先验证基础流程（6个特征）

**目的：** 确保数据拉取、训练、推荐流程正常

**命令：**
```bash
python scripts/build_sequence_dataset.py \
  --start 20240101 --end 20240131 \
  --symbols 600519,000333,601318 \
  --source tushare --seq-len 30
```

**验收标准：**
- ✅ 数据拉取成功
- ✅ 生成 train/valid/test.parquet
- ✅ 标签有效率 > 90%

---

### 2. 添加已实现的技术指标（12个特征）

**目的：** 提升模型预测能力

**修改方式：** 编辑 `scripts/build_sequence_dataset.py` 的 `_compute_features` 函数

**差异：**
```python
# 原来（6个特征）
def _compute_features(data: pd.DataFrame) -> pd.DataFrame:
    features = [
        Return1D(),
        Return5D(),
        Return20D(),
        VolumeRatio(window=5),
        VolumeChange(),
        AmountChange(),
    ]
    # ...

# 增强版（12个特征）
def _compute_features(data: pd.DataFrame) -> pd.DataFrame:
    features = [
        # 动量特征
        Return1D(),
        Return5D(),
        Return20D(),
        # 量价特征
        VolumeRatio(window=5),
        VolumeChange(),
        AmountChange(),
        # 技术指标
        RSI(period=14),
        MACDLine(),
        MACDSignal(),
        MACDHist(),
        BollingerDeviation(window=20),
        PriceSlope(window=20),
    ]
    # ...
```

---

### 3. 训练并评估模型

**命令：**
```bash
python scripts/train_mtl.py \
  --config configs/model_mtl.yaml \
  --train-data data/datasets/train.parquet \
  --valid-data data/datasets/valid.parquet
```

**目标：**
- 验证集 IC > 0.05
- 测试集 IC > 0.05

---

### 4. 根据IC决定是否继续扩展

**决策树：**
```
测试集 IC > 0.06  → ✅ 效果不错，可以开始推荐
测试集 IC 0.05-0.06 → ⚠️ 尝试添加波动率特征（阶段3）
测试集 IC < 0.05 → ❌ 检查数据质量或模型架构
```

---

## 📚 相关代码位置

| 特征类型 | 代码位置 | 状态 |
|---------|---------|------|
| 动量特征 | `src/ashare_lab/features/momentum.py` | ✅ 已实现 |
| 量价特征 | `src/ashare_lab/features/volume.py` | ✅ 已实现 |
| 技术指标 | `src/ashare_lab/features/technical.py` | ✅ 已实现（RSI/MACD/Bollinger）|
| 价格斜率 | `src/ashare_lab/features/price_slope.py` | ✅ 已实现 |
| 波动率特征 | - | ❌ 待创建 |
| K线形态 | - | ❌ 待创建 |

---

**文档维护者：** 浮浮酱 & A-Share Lab Team
**最后更新：** 2025-01-18
**版本：** v1.0
