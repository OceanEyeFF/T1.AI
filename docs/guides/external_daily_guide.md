# 外部日线采集与决策回放

采集名单包括标普 500 `SPX`、纳斯达克综合 `IXIC`、恒生 `HSI`、恒生科技 `HKTECH`，以及沪金 `AU.SHF`、沪铜 `CU.SHF`、原油 `SC.INE`、液化石油气 `PG.DCE` 和 PTA `TA.ZCE` 主力合约。指数走 TuShare `index_global`，期货走 `fut_daily`。缓存位于本机忽略目录 `inputs/data/cache/tushare_external/daily.sqlite`。每行保留交易日期、来源接口、观察时间和数据版本。[国际指数接口](https://tushare.pro/document/1?doc_id=211) · [期货日线接口](https://tushare.pro/document/2?doc_id=138)

## 采集和回放

在仓库根目录用项目 Python 环境执行。采集从环境变量 `TUSHARE_TOKEN` 读取凭据，回放只读缓存，可离线运行。

```bash
python -m scripts.external_daily capture --start 2026-11-16 --end 2026-11-20
python -m scripts.external_daily replay --market CN --as-of '2026-11-20T15:00:00+08:00'
python -m scripts.external_daily replay --market HK --as-of '2026-11-20T16:10:00+08:00'
```

默认采集全部九条序列。可重复传 `--symbol`，采集或重试指定标的。采集结果列出每条序列返回行数、写入版本数和查询的实际结束日期，单条失败时保留其他已入库序列。回放返回每条序列截至决策时刻的可用行数及最近一条行情。代码可直接调用 `DataLake.load_external_daily(as_of=...)` 读取各序列的完整可见行。

也可按手工操作日志批量回放。每行提供唯一 `id`、市场 `CN` 或 `HK`、带偏移的 `decision_at`，以及动作、标的、方向、股数、委托号和备注。输出保留人工记录，并附上该时刻可读的行情。股数、方向和委托号可按操作情况留空。样例包含周末复盘与假设的后续交易日时刻，用于对照两批行情首次采集前后的可见范围。清空缓存重采后，首次观察时间会变化，样例报告会随之变化。[模拟手工操作 CSV](../../tests/fixtures/external_daily/manual_operations.csv)

```bash
python -m scripts.external_daily replay-operations \
  --csv tests/fixtures/external_daily/manual_operations.csv --start 2026-11-16
```

## 决策时刻的数据边界

- `trade_date` 是数据源交易日，`available_at` 是系统实际收到该版本的 UTC 时间。TuShare 日线接口未提供每条记录的原始发布时间，回放只读取 `available_at <= 决策时刻` 的版本。首次采集前的历史决策可能返回空，补拉行情不会倒填系统的观察时间。
- 采集按来源市场的本地日期排除当天。美股使用纽约时区，恒生和恒生科技使用香港时区，国内期货使用上海时区。这个保守规则可能延迟本地当天已收盘的行情，也避免把当天尚未完成的日线当作完整行情。
- 如同一交易日的行情内容变化，新版本以新观察时间入库。按原时刻回放仍使用旧版本。原值重复采集不增加版本。决策必须给出带时区的具体时刻，只有日期时应保留为缺少决策时刻。

## 期货数据候选

2026-11-16 至 11-20 的 TuShare `fut_daily` 小样本验证中，以下 16 个主力代码各返回 5 条日线，收盘字段均有值。其中铜、原油、液化石油气和 PTA 已进入常规采集名单。

| 类别 | 已取到日线的品种 |
|---|---|
| 金属 | 铜 `CU.SHF`、铝 `AL.SHF`、锌 `ZN.SHF`、镍 `NI.SHF`、银 `AG.SHF` |
| 油气 | 原油 `SC.INE`、燃料油 `FU.SHF`、低硫燃料油 `LU.INE`、液化石油气 `PG.DCE` |
| 化工基材 | PTA `TA.ZCE`、甲醇 `MA.ZCE`、线型低密度聚乙烯 `L.DCE`、聚丙烯 `PP.DCE`、聚氯乙烯 `V.DCE`、乙二醇 `EG.DCE`、苯乙烯 `EB.DCE` |

液化石油气和天然气适合分别记录。海外原油和天然气可进一步核对 CME 的 WTI、Henry Hub，以及 ICE 的 Brent 行情。构造期货收益特征时应保存主力对应的实际合约，明确换月规则，再处理价格跳点。[TuShare 主力映射](https://tushare.pro/document/2?doc_id=189) · [上期所上市品种](https://www.shfe.com.cn/) · [大商所能化品种](https://www.dce.com.cn/qhxy/file/2025-08-05/17543892971982c9a882b9879b789653019879c0382e003d.pdf) · [CME 能源结算数据](https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.settlements.html) · [ICE 原油基准](https://www.ice.com/oil)
