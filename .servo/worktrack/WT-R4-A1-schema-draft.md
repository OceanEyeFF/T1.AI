---
title: "WT-R4-A1 Schema Draft"
artifact_type: "schema-draft"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
deliverable: "A1-D3"
status: "frozen"
updated: "2026-07-20T21:22:00+08:00"
owner: "OceanEyeFF"
freeze_state: "frozen_for_A2"
aligned_with:
  - ashare_infra.data.tushare_source (develop)
  - docs/reference/data_contract.md
  - WT-R4-A1-lake-source-contract.md
  - sampled cache parquet 2026-07-20
---

# WT-R4-A1 — Schema 草案

> **性质：** A1-T3 文档。供 A2 contract/integration 测试引用。  
> **权威实现（字段集）：** `ashare_infra.data.tushare_source` 的 `SUPPORTED_*`（develop）。  
> **磁盘样例：** `inputs/data/cache/tushare_*/000001.SZ/year=2024/part.parquet`（只读核对）。  
> **不在本 WT：** 改适配器代码、灌湖、derived 终稿。

## 1. Control Signal

```yaml
schema_id: MS-R4-001-tushare-daily-schema-v0
status: frozen_for_A2
primary_adjust: qfq
on_disk_date_representation: column_date_datetime64ns
in_memory_bars_representation: DatetimeIndex_named_date_preferred
history_start: "2023-01-01"
symbol_on_disk: ts_code  # e.g. 000001.SZ
symbol_in_pool_csv: bare_6_digit  # e.g. 000001
amount_unit_tushare: thousand_CNY
```

## 2. Path & Partition Schema

```text
{cache_root}/{namespace}/{ts_code}/year={YYYY}/part.parquet
```

| Element | Contract |
|---------|----------|
| `cache_root` | `inputs/data/cache`（相对 repo） |
| `namespace` | `tushare_qfq` \| `tushare_daily_basic` \| `tushare_moneyflow` \| `tushare`（raw）\| `tushare_hfq` |
| `ts_code` | TuShare 风格，`600519.SH` / `000001.SZ` |
| `year` | 四位公历年；与行内 `date` 的年份一致 |
| File | 单文件 `part.parquet`（每 symbol×year） |

**R4 默认 namespace：** `tushare_qfq`（锁定前复权）。  
**Index / ETF 锚点（defer）：** `tushare_qfq/510300.SH/…`（当前无 part；A3 fill）。

**禁止：** 跨 `qfq`/`raw`/`hfq` 静默拼接同一逻辑序列。

## 3. On-disk vs In-memory

| Layer | `date` | OHLCV columns | Notes |
|-------|--------|---------------|-------|
| **On-disk parquet**（样例） | 列 `date: datetime64[ns]`；index 为 `RangeIndex` | 见 §4 | A2 可读盘断言用此形态 |
| **Adapter normalize（内存）** | 常设为 **DatetimeIndex**（`date`） | 同字段 | `tushare_source._normalize_*` |
| **DataLake 返回** | 通常 DatetimeIndex 升序 | 同字段 | 消费方以 Index 切片为准 |

A2 测试建议：  
- **磁盘合同测** → 断言列名 / dtype / 分区路径；  
- **API 合同测** → 断言 Index 单调、无未来洞（配合 `as_of`）。

## 4. Dataset: OHLCV（`tushare_qfq`）

对齐 `SUPPORTED_FIELDS` + 磁盘 `date` 列。

| Column | dtype (on-disk sample) | Required | Notes |
|--------|------------------------|----------|-------|
| `date` | datetime64[ns] | **yes** | 交易日；升序 |
| `open` | float64 | **yes** | 前复权 |
| `high` | float64 | **yes** | |
| `low` | float64 | **yes** | |
| `close` | float64 | **yes** | |
| `volume` | float64 | **yes** | TuShare `vol` 映射 |
| `amount` | float64 | **yes** | **单位：千元**（勿再 `/1e8`） |

```yaml
required_columns_qfq: [date, open, high, low, close, volume, amount]
adjust_modes_supported: [raw, qfq, hfq]
r4_default_adjust: qfq
```

## 5. Dataset: Daily Basic（`tushare_daily_basic`）

对齐 `SUPPORTED_DAILY_BASIC_FIELDS`。

| Column | dtype (sample) | Required |
|--------|----------------|----------|
| `date` | datetime64[ns] | **yes** |
| `turnover_rate` | float64 | **yes** |
| `turnover_rate_f` | float64 | yes |
| `volume_ratio` | float64 | yes |
| `pe_ttm` | float64 | yes |
| `pb` | float64 | yes |
| `ps_ttm` | float64 | yes |
| `dv_ttm` | float64 | yes |
| `total_mv` | float64 | **yes**（A0 市值卫生） |
| `circ_mv` | float64 | **yes** |

```yaml
required_columns_daily_basic_min: [date, turnover_rate, total_mv, circ_mv]
required_columns_daily_basic_full: [date, turnover_rate, turnover_rate_f, volume_ratio, pe_ttm, pb, ps_ttm, dv_ttm, total_mv, circ_mv]
```

单位：以 TuShare `daily_basic` 文档为准（市值多为万元）；A0 策略已按现网语义使用——A2 测勿擅自改换算。

## 6. Dataset: Moneyflow（`tushare_moneyflow`）

对齐 `SUPPORTED_MONEYFLOW_FIELDS`。

| Column | dtype (sample) | Required |
|--------|----------------|----------|
| `date` | datetime64[ns] | **yes** |
| `buy_sm_vol` / `sell_sm_vol` | int64 | yes |
| `buy_sm_amount` / `sell_sm_amount` | float64 | yes |
| `buy_md_*` / `sell_md_*` | vol int64 / amount float64 | yes |
| `buy_lg_*` / `sell_lg_*` | … | yes |
| `buy_elg_*` / `sell_elg_*` | … | yes |
| `net_mf_vol` | int64 | **yes** |
| `net_mf_amount` | float64 | **yes** |

```yaml
required_columns_moneyflow_min: [date, net_mf_vol, net_mf_amount]
# full set = SUPPORTED_MONEYFLOW_FIELDS + date
```

## 7. Optional / Deferred Schemas

| Dataset | Status | Notes |
|---------|--------|-------|
| `adj_factor` | supported in adapter；非 R4 默认消费 | `SUPPORTED_ADJ_FACTOR_FIELDS` |
| `510300.SH` qfq | **deferred empty** | 同 §4 列合同；A3 fill 后启用 |
| `meta/stock_basic` | Infra 1.5 本地 meta | CSV/parquet；非本 T3 日频主表 |
| AkShare flat/nested CSV | backup | 见 Infra Phase 2；非 R4 primary |

## 8. Symbol & Join Keys

| Context | Key form | Example |
|---------|----------|---------|
| Pool CSV / registry | bare 6-digit | `000001` |
| Cache path / TuShare API | `ts_code` | `000001.SZ` |
| Join across qfq/basic/mf | `ts_code` + `date` | 同日对齐 |

规范化：`ashare_lab.symbols.symbol_to_ts_code` / lake meta `_normalize_symbol`（develop）。A2 须覆盖裸码 → ts_code。

## 9. Invariants（建议 A2 断言）

1. 分区路径匹配 §2；`year=` 与行内年份一致。  
2. 每文件 `date` 唯一、升序、无全 NaN 的 OHLC。  
3. 池内 61 标的：三表路径存在且可解析（见 inventory）。  
4. `amount`（qfq）语义 = 千元。  
5. `refresh` 合并不得制造永久日期空洞（适配器已修；回归测保留）。  
6. 默认 `adjust=qfq`；测试不得默认 raw 冒充 qfq。

## 10. Relation to `docs/reference/data_contract.md`

通用 OHLCV 表与分区规则与本文一致。本文额外冻结：

- daily_basic / moneyflow 全列；
- on-disk vs in-memory `date` 形态；
- R4 池绑定与 `510300` defer；
- amount 单位与 soft80 非 schema 失败条件。

A2 可通过后，再考虑把增量回写进 `docs/reference/data_contract.md`（另批 doc catch-up，非 A1 必过）。

## 11. Non-actions

- No adapter code changes in A1
- No cache rewrite / live fill
- No derived layer schema（A4）
- No Phase 4 / EXEC-002

## 12. Related Artifacts

- `.servo/worktrack/WT-R4-A1-lake-source-contract.md`
- `.servo/worktrack/WT-R4-A1-cache-inventory.md`
- `docs/reference/data_contract.md`
- Next: `.servo/worktrack/WT-R4-A1-rate-limit-recommendations.md`（T4）
