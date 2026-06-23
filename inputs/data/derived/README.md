# derived/ — 高阶衍生特征层

由 `dataset/builder.py` 在数据集构建时写入，消费 `inputs/data/cache/` 中的 TuShare 原始数据。

计划包含：

- 动量特征（5d/10d/20d return）
- 波动率特征（ATR、历史波动率）
- 技术指标（RSI、MACD、Bollinger Bands）
- 市场状态特征（指数联动、板块映射）

当前状态：目录就位，实际特征构建待 TuShare 数据湖完成后实现。
