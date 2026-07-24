# derived/ — R4 高阶衍生特征层（最小合同）

> **合同 ID：** `MS-R4-001-derived-minimal-v0`（`R4_DERIVED_CONTRACT_ID`）  
> **权威常量：** `ashare_infra.lake.r4_contract`（WT-R4-A4-T1 冻结）  
> **Schema 文档：** `.servo/worktrack/WT-R4-A4-derived-schema.md`  
> **构建/加载：** T2 `ashare_lab.derived`；T3 `DataLake.load_derived*` / `make_r4_datalake`

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

## Load API（T3）

| API | 语义 |
|-----|------|
| `DataLake.load_derived(symbol, family, start=None, end=None, as_of=None)` | 读单一 family 年分区；filesystem only |
| `DataLake.load_derived_minimal(symbol, …)` | 返回 `momentum` + `technical` |
| `DataLake.load_scope_derived(scope, family, as_of=None)` | 按 DataScope 批量（空帧跳过） |
| `make_r4_datalake(..., derived_root=…)` | 默认绑定 `R4_DERIVED_ROOT` |

- **零 live：** load 不调用 `fetch_tushare_*`；缺分区 → 空帧（保留 schema 列）
- **可复现：** 同一路径重复 load 结果一致；列对齐 `r4_derived_required_columns`

## 当前状态

- T1：目录 + README + 常量/路径助手已冻结
- T2：cache-only builder 已落地（`ashare_lab.derived` + `r4_derived_io`）；本地可由 cache 重建 parquet
- T3：`DataLake.load_derived*` + Arch-v1 unit/contract/integration
- Parquet 分区（`**/year=*/`）默认不入仓（见 `.gitignore`）；README / 合同入仓
