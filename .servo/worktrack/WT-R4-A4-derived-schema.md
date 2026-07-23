---
title: "WT-R4-A4 Derived Schema (minimal)"
artifact_type: "schema-draft"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
deliverable: "A4-D1"
status: "frozen_for_T2"
updated: "2026-07-23T20:40:00+08:00"
owner: "OceanEyeFF"
freeze_state: "frozen_for_T2"
aligned_with:
  - ashare_infra.lake.r4_contract (R4_DERIVED_*)
  - ashare_lab.features.momentum (Return5D/10D/20D)
  - ashare_lab.features.technical (RSI)
  - WT-R4-A1-schema-draft.md (partition pattern)
  - A4_Q1=M1_ret_rsi / A4_Q2=inputs_derived_year_parts
---

# WT-R4-A4 — Derived 最小 Schema

> **性质：** A4-T1 文档。供 T2 builder / T3 load / contract 测试引用。  
> **权威常量：** `ashare_infra.lake.r4_contract` 的 `R4_DERIVED_*`。  
> **不在本任务：** 写 parquet、实现 builder、改 DataLake load API（T2/T3）。

## 1. Control Signal

```yaml
schema_id: MS-R4-001-derived-minimal-v0
status: frozen_for_T2
minimal_set: M1_ret_rsi
derived_root: inputs/data/derived
source_namespace: tushare_qfq
source_adjust: qfq
refresh_default: false
history_start: "2023-01-01"
pool_binding: custom_research_liquidity_quality_v1@1
symbol_on_disk: ts_code
on_disk_date_representation: column_date_datetime64ns
live_policy: zero_live
```

## 2. Path & Partition Schema

```text
{derived_root}/{family}/{ts_code}/year={YYYY}/part.parquet
```

| Element | Contract |
|---------|----------|
| `derived_root` | `inputs/data/derived` |
| `family` | `momentum` \| `technical`（最小集） |
| `ts_code` | `600519.SH` / `000001.SZ` |
| `year` | 四位公历年；与行内 `date` 年份一致 |
| File | `part.parquet` |

Helpers: `r4_derived_part_path` / `r4_derived_symbol_dir` / `r4_derived_required_columns`.

**禁止：** 跨 family 静默拼接同一逻辑帧；禁止把 `workspace/datasets/` 当作 derived 合同根。

## 3. Family: momentum

| Column | dtype (expected) | Required | Notes |
|--------|------------------|----------|-------|
| `date` | datetime64[ns] | **yes** | 交易日；升序 |
| `return_5d` | float64 | **yes** | 对齐 `Return5D`（含 shift 防前视） |
| `return_10d` | float64 | **yes** | 对齐 `Return10D` |
| `return_20d` | float64 | **yes** | 对齐 `Return20D` |

```yaml
required_columns_momentum: [date, return_5d, return_10d, return_20d]
```

## 4. Family: technical

| Column | dtype (expected) | Required | Notes |
|--------|------------------|----------|-------|
| `date` | datetime64[ns] | **yes** | |
| `rsi_14` | float64 | **yes** | 对齐 `RSI(period=14)` |

```yaml
required_columns_technical: [date, rsi_14]
```

## 5. Optional / Deferred

| Item | Status |
|------|--------|
| `atr_14` | optional（不进 Gate 硬 AC） |
| MACD / Bollinger | deferred（`R4_DERIVED_DEFERRED_FAMILIES`） |
| volatility family | deferred |
| market_state | deferred（A2-carry） |

## 6. Test Expectations (T1)

- **Unit：** 常量锁定 + path helper 形状 + unknown family raises
- **Contract：** 引用 `R4_DERIVED_*`；不要求磁盘已有 parquet（T2 前可空）
- **Integration（T2+）：** 构建后断言列 schema + year 分区可读

## 7. Non-Goals

- Live TuShare pull
- Soft80 expansion
- Training / Phase4 / EXEC-002
- Replacing DatasetBuilder `workspace/datasets/` outputs
