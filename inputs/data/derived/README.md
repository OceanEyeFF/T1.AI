# derived/ — R4 高阶衍生特征层（最小合同）

> **合同 ID：** `MS-R4-001-derived-minimal-v0`（`R4_DERIVED_CONTRACT_ID`）  
> **权威常量：** `ashare_infra.lake.r4_contract`（WT-R4-A4-T1 冻结）  
> **Schema 文档：** `.servo/worktrack/WT-R4-A4-derived-schema.md`  
> **构建/加载：** T2 builder / T3 load（本目录 T1 仅布局+README）

## 布局（对齐 cache year 分区）

```text
inputs/data/derived/
  {family}/{ts_code}/year={YYYY}/part.parquet
```

| Element | Contract |
|---------|----------|
| `derived_root` | `inputs/data/derived`（`R4_DERIVED_ROOT`） |
| `family` | 最小集：`momentum` \| `technical` |
| `ts_code` | TuShare 风格，如 `600519.SH` |
| `year` | 四位公历年；与行内 `date` 年份一致 |
| File | `part.parquet` |

## 最小特征集（A4_Q1 = M1_ret_rsi）

| Family | Required columns | Lab feature 对齐 |
|--------|------------------|------------------|
| `momentum` | `date`, `return_5d`, `return_10d`, `return_20d` | `Return5D` / `Return10D` / `Return20D` |
| `technical` | `date`, `rsi_14` | `RSI(period=14)` |

- **可选：** `atr_14`（`R4_DERIVED_OPTIONAL_COLUMNS`；不阻塞 Gate）
- **延后：** MACD / Bollinger / volatility 家族 / market_state（`R4_DERIVED_DEFERRED_FAMILIES`）

## 输入与策略

- **源：** 仅 `tushare_qfq` cache（`R4_DERIVED_SOURCE_NAMESPACE`）
- **池绑定：** `custom_research_liquidity_quality_v1@1`（61）
- **历史起点：** `2023-01-01`（`R4_HISTORY_START`）
- **Live：** 默认 **零 live**（`refresh=False`）；禁止旁路直拉 TuShare
- **禁止：** 与 `workspace/datasets/` 静默双写为第二套 derived 真理；DatasetBuilder 输出仍属 workspace，不替代本目录合同

## 当前状态

- T1：目录 + README + 常量/路径助手已冻结
- T2+：实际 parquet 构建尚未落地
