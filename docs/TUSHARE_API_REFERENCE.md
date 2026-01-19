# TuShare API 高阶数据接口参考

本文档列出 TuShare Pro 提供的高阶数据接口，供未来特征扩展使用。

**官方文档：** https://tushare.pro/document/2

---

## 🎯 当前已使用的接口

### 1. 日线行情 `daily` ✅ 免费（120积分）

```python
pro.daily(ts_code='600519.SH', start_date='20200101', end_date='20241231')
```
**返回字段：** ts_code, trade_date, open, high, low, close, vol, amount
**使用位置：** `src/ashare_lab/data/tushare_source.py`
**积分要求：** 120（免费用户可用）✅
**限流：** 每分钟200次

---

## 📊 可扩展的高阶数据接口

**⚠️ 积分要求警告：**
- 以下接口需要更高积分等级（120+ ~ 5000+）
- 免费用户（120积分）**暂时无法访问**大部分高阶接口
- **建议：** 先用免费的日线数据验证模型效果，再考虑升级积分

**查看你的当前积分：** https://tushare.pro/user/token

---

### 一、基本面数据（需要积分）

#### 1.1 财务数据

**利润表 `income`**
```python
pro.income(ts_code='600519.SH', period='20231231')
```
**关键字段：**
- `total_revenue` - 营业总收入
- `revenue` - 营业收入
- `n_income` - 净利润
- `n_income_attr_p` - 归属母公司净利润
- `operate_profit` - 营业利润
- `gross_margin` - 毛利率

**推荐因子：**
- 营收增长率（YoY）
- 净利润增长率（YoY）
- 毛利率趋势
- ROE（净资产收益率）

---

**资产负债表 `balancesheet`**
```python
pro.balancesheet(ts_code='600519.SH', period='20231231')
```
**关键字段：**
- `total_assets` - 总资产
- `total_liab` - 总负债
- `total_hldr_eqy_inc_min_int` - 股东权益合计
- `money_cap` - 货币资金
- `accounts_receiv` - 应收账款

**推荐因子：**
- 资产负债率
- 流动比率
- 速动比率
- 存货周转率

---

**现金流量表 `cashflow`**
```python
pro.cashflow(ts_code='600519.SH', period='20231231')
```
**关键字段：**
- `n_cashflow_act` - 经营活动现金流量净额
- `n_cashflow_inv_act` - 投资活动现金流量净额
- `n_cash_flows_fnc_act` - 筹资活动现金流量净额
- `c_cash_equ_end_period` - 期末现金及现金等价物余额

**推荐因子：**
- 经营现金流/净利润比率
- 自由现金流（FCF）
- 现金流增长率

---

#### 1.2 财务指标 `fina_indicator`

```python
pro.fina_indicator(ts_code='600519.SH', period='20231231')
```
**关键字段：**
- `roe` - 净资产收益率
- `roa` - 总资产报酬率
- `grossprofit_margin` - 销售毛利率
- `debt_to_assets` - 资产负债率
- `current_ratio` - 流动比率
- `quick_ratio` - 速动比率
- `eps` - 每股收益
- `bps` - 每股净资产
- `pe` - 市盈率
- `pb` - 市净率

**推荐因子：**
- ROE 趋势（连续5个季度）
- PE 相对行业均值
- PB 历史分位数
- 盈利质量（经营现金流/净利润）

---

### 二、市场数据

#### 2.1 复权因子 `adj_factor`

```python
pro.adj_factor(ts_code='600519.SH', trade_date='20241231')
```
**用途：** 计算复权价格（已在 `tushare_source.py` 中使用）

---

#### 2.2 每日指标 `daily_basic`

```python
pro.daily_basic(ts_code='600519.SH', trade_date='20241231')
```
**关键字段：**
- `turnover_rate` - 换手率（%）
- `turnover_rate_f` - 换手率（自由流通股）
- `volume_ratio` - 量比
- `pe` - 市盈率（总市值/净利润）
- `pe_ttm` - 市盈率（TTM）
- `pb` - 市净率（总市值/净资产）
- `ps` - 市销率（总市值/营业收入）
- `ps_ttm` - 市销率（TTM）
- `total_share` - 总股本（万股）
- `float_share` - 流通股本（万股）
- `free_share` - 自由流通股本（万股）
- `total_mv` - 总市值（万元）
- `circ_mv` - 流通市值（万元）

**推荐因子：**
- 换手率 MA5/MA20 比值
- 量比突破（> 1.5）
- PE/PB 历史分位数
- 流通市值排名

---

#### 2.3 限售解禁 `share_float`

```python
pro.share_float(ts_code='600519.SH')
```
**用途：** 预测解禁对股价的影响（高级策略）

---

### 三、市场情绪数据

#### 3.1 龙虎榜数据 `top_list`

```python
pro.top_list(trade_date='20241231')
```
**关键字段：**
- `buy` - 买入额
- `buy_rate` - 买入占总成交比例
- `sell` - 卖出额
- `net_buy` - 净买入额

**推荐因子：**
- 龙虎榜买入强度
- 机构席位占比

---

#### 3.2 融资融券 `margin`

```python
pro.margin(trade_date='20241231')
```
**关键字段：**
- `rzye` - 融资余额（元）
- `rqyl` - 融券余量（股）
- `rzmre` - 融资买入额（元）
- `rzche` - 融资偿还额（元）

**推荐因子：**
- 融资余额变化率
- 融资净买入额

---

#### 3.3 北向资金 `moneyflow_hsgt`

```python
pro.moneyflow_hsgt(trade_date='20241231')
```
**关键字段：**
- `ggt_ss` - 港股通（上海）
- `ggt_sz` - 港股通（深圳）
- `hgt` - 沪股通（百万元）
- `sgt` - 深股通（百万元）
- `north_money` - 北向资金（百万元）
- `south_money` - 南向资金（百万元）

**推荐因子：**
- 北向资金净流入
- 北向资金持股占比变化

---

#### 3.4 股东人数 `stk_holdernumber`

```python
pro.stk_holdernumber(ts_code='600519.SH')
```
**关键字段：**
- `holder_num` - 股东人数
- `end_date` - 截止日期

**推荐因子：**
- 股东人数变化率（筹码集中度）

---

### 四、行业与概念板块

#### 4.1 行业分类 `stock_basic`

```python
pro.stock_basic(ts_code='600519.SH')
```
**关键字段：**
- `industry` - 所属行业
- `market` - 市场类型（主板/创业板等）
- `list_date` - 上市日期

**用途：**
- 行业中性化策略
- 行业轮动策略

---

#### 4.2 概念板块 `concept`

```python
pro.concept(src='ts')
```
**用途：** 热点概念挖掘（如：ChatGPT、新能源车）

---

### 五、宏观经济数据

#### 5.1 GDP数据 `cn_gdp`

```python
pro.cn_gdp()
```
**用途：** 宏观经济周期判断

---

#### 5.2 CPI/PPI `cn_cpi`, `cn_ppi`

```python
pro.cn_cpi()
pro.cn_ppi()
```
**用途：** 通胀预期因子

---

#### 5.3 货币供应量 `cn_m`

```python
pro.cn_m()
```
**关键字段：**
- `m0` - 流通中现金
- `m1` - 狭义货币
- `m2` - 广义货币

**用途：** 流动性宽松/紧缩判断

---

## 🎯 推荐的特征扩展优先级

### 优先级1：市场数据（无积分要求）⭐⭐⭐

| 接口 | 特征 | 预期IC提升 |
|------|------|-----------|
| `daily_basic` | 换手率、量比、PE/PB分位数 | +0.01 ~ +0.02 |
| `moneyflow_hsgt` | 北向资金净流入 | +0.005 ~ +0.01 |
| `margin` | 融资余额变化 | +0.005 ~ +0.01 |

**实现难度：** 低
**API限流：** 较宽松

---

### 优先级2：财务数据（需要积分）⭐⭐

| 接口 | 特征 | 预期IC提升 |
|------|------|-----------|
| `fina_indicator` | ROE、毛利率、资产负债率 | +0.02 ~ +0.03 |
| `income` | 营收/净利润增长率 | +0.02 ~ +0.03 |

**实现难度：** 中
**注意事项：**
- 财务数据季度更新（需要对齐发布日期）
- 避免未来信息泄露（使用 `ann_date` 对齐）

---

### 优先级3：市场情绪（需要高积分）⭐

| 接口 | 特征 | 预期IC提升 |
|------|------|-----------|
| `top_list` | 龙虎榜买入强度 | +0.01 ~ +0.015 |
| `stk_holdernumber` | 筹码集中度 | +0.005 ~ +0.01 |

**实现难度：** 高
**注意事项：**
- 数据稀疏（不是每日更新）
- 需要前向填充（ffill）

---

## 📝 实现建议

### Step 1: 创建新特征模块

```python
# src/ashare_lab/features/market_basic.py
class TurnoverRate(BaseFeature):
    """换手率特征"""
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # 从 daily_basic 获取 turnover_rate
        pass

class PERank(BaseFeature):
    """PE历史分位数"""
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # 计算PE在过去252天的历史分位数
        pass
```

### Step 2: 创建数据拉取脚本

```python
# scripts/fetch_daily_basic.py
def fetch_daily_basic(symbols, start, end):
    """拉取 daily_basic 数据"""
    for symbol in symbols:
        df = pro.daily_basic(ts_code=symbol, start_date=start, end_date=end)
        # 保存到缓存
        save_to_cache(df, f"cache/daily_basic/{symbol}.parquet")
```

### Step 3: 集成到数据集构建

```python
# scripts/build_sequence_dataset_enhanced.py
def _compute_features(data: pd.DataFrame, daily_basic: pd.DataFrame) -> pd.DataFrame:
    # 现有特征
    features = [Return1D(), Return5D(), ...]

    # 新增市场数据特征
    features.extend([
        TurnoverRate(),
        PERank(),
        NorthMoneyFlow(),
    ])

    # ...
```

---

## ⚠️ 注意事项

### 1. API限流

TuShare Pro有积分和积分等级限制：
- **积分120（免费用户）：** 每分钟调用200次
- **积分2000：** 每分钟调用400次
- **积分5000+：** 无限制

**建议：**
- 使用缓存（避免重复拉取）
- 实现重试机制（指数退避）
- 批量拉取（一次拉取多日数据）

### 2. 数据对齐

**关键原则：** 避免未来信息泄露

```python
# ❌ 错误：使用当日财务数据预测当日收益
features["roe"] = daily_basic["roe"]  # 使用当日数据

# ✅ 正确：使用前一日财务数据
features["roe"] = daily_basic["roe"].shift(1)  # 使用前一日数据
```

### 3. 数据质量检查

```python
# 检查缺失值比例
missing_rate = df.isnull().mean()
if missing_rate > 0.3:
    logger.warning(f"{symbol}: 缺失值比例过高 {missing_rate:.2%}")
```

---

## 📚 参考资源

- **TuShare Pro文档：** https://tushare.pro/document/2
- **积分获取：** https://tushare.pro/document/1?doc_id=13
- **数据字典：** https://tushare.pro/document/2?doc_id=25

---

**文档维护者：** 浮浮酱 & A-Share Lab Team
**最后更新：** 2025-01-15
**版本：** v1.0
