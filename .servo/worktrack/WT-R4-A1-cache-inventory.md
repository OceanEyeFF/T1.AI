---
title: "WT-R4-A1 Cache Inventory"
artifact_type: "cache-inventory"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
deliverable: "A1-D2"
status: "frozen"
updated: "2026-07-20T21:22:00+08:00"
owner: "OceanEyeFF"
freeze_state: "frozen_for_A2"
live_pull: "none"
policy: "read_only_inventory"
---

# WT-R4-A1 — Cache Inventory（相对 A0 批准池）

> **性质：** A1-T2 只读盘点。不写 cache、不 live、不灌湖。  
> **绑定池：** `custom_research_liquidity_quality_v1` / `1`（61 symbols）  
> **扫描时刻：** 2026-07-20T20:34:00+08:00（本机 `inputs/data/cache`）  
> **上游基线：** `.servo/worktrack/WT-R4-A0-data-gaps.md`（T3 @ 2026-07-15）

## 1. Control Signal

```yaml
inventory_id: MS-R4-001-cache-inventory-v0
cache_root: inputs/data/cache
pool_id: custom_research_liquidity_quality_v1
pool_version: "1"
pool_symbols: 61
pool_qfq_coverage: 61/61
pool_daily_basic_coverage: 61/61
pool_moneyflow_coverage: 61/61
index_510300_available: false
soft_target_80_met: false
hard_cap_100_ok: true
live_pull: none
write_cache: none
```

## 2. Method

1. 读取 `inputs/pools/research_liquidity_quality/symbols.csv`（裸 6 位码）。
2. 映射 `ts_code`：`6*→.SH`，`0*/3*→.SZ`（本池无 BJ）。
3. 扫描命名空间目录下 `{ts_code}/year=*/part.parquet`：
   - `tushare_qfq`
   - `tushare_daily_basic`
   - `tushare_moneyflow`
4. 对池内 qfq 全量统计行数与 `date` min/max（只读 parquet）。
5. **不**调用 TuShare / **不**写盘。

## 3. Namespace Summary

| Namespace | Dirs with ≥1 parquet | Empty dirs | Notes |
|-----------|---------------------:|-----------:|-------|
| `tushare_qfq` | 65 | 1 (`510300.SH`) | 与 A0 T3 一致 |
| `tushare_daily_basic` | 65 | 0 | |
| `tushare_moneyflow` | 65 | 0 | |

Cross-table（在 **qfq 非空** 集合上）：

| Check | Count | Detail |
|-------|------:|--------|
| qfq missing daily_basic | 0 | none |
| qfq missing moneyflow | 0 | none |
| daily_basic without qfq | 0 | none |

## 4. Pool ∩ Cache

| Check | Result |
|-------|--------|
| Pool symbols | 61 |
| Pool ∩ qfq (nonempty) | **61 / 61** |
| Pool missing qfq | **[]** |
| Pool ∩ daily_basic | **61 / 61** |
| Pool missing daily_basic | **[]** |
| Pool ∩ moneyflow | **61 / 61** |
| Pool missing moneyflow | **[]** |

结论：A0 批准池在三张表上 **满覆盖**（相对当前本地 cache）。扩池到 soft 80 的瓶颈是 **cache universe 规模**，不是池内洞。

## 5. Pool qfq Depth（行数 / 日期）

| Metric | Value |
|--------|-------|
| Row-count min | 622 (`601989.SH`) |
| Row-count max | 783 (`603993.SH`) |
| Date min (observed) | 2023-01-03 |
| Date max (observed) | 2026-03-31 |
| Year partitions (sample) | 2023–2026 四年分区常见 |

对齐湖合同 `history_start=2023-01-01`：首个交易日多为 `2023-01-03`（预期）。

部分标的 `date_max` 早于全集 max（例：`601989.SH` → 2025-08-12）——记为 **staleness 候选**，不在 A1 补洞；A3 inventory 复查 / limited-live 时优先。

## 6. Cache Outside Pool（qfq nonempty − pool）

共 **4** 个有数但不在批准池内：

| ts_code | Note |
|---------|------|
| `300750.SZ` | 创业板；A0 H1 硬过滤（预期） |
| `600498.SH` | 主板；未入选本版池 |
| `600879.SH` | 主板；未入选本版池 |
| `603619.SH` | 主板；未入选本版池 |

这些 **不是** 池内缺口；可作为 A3 扩 universe / 重跑策略的候选原料，不得自动并入验收 universe。

## 7. Material Gaps / Deferrals

| ID | Gap | Severity for A1 | Deferred to |
|----|-----|-----------------|-------------|
| G1 | Soft target 80 unmet（选 61；cache 主板有数 ~65） | accepted residual | A3 扩池 + 重选 |
| G2 | `510300.SH` 目录存在、**0** parquet | accepted residual | A3 / L2 index fill |
| G3 | 部分池内标的 `date_max` 落后全集 | low / watch | A3 增量刷新 |
| G4 | `data_source.toml` 仍默认 akshare | doc drift | A2 配置对齐（另批） |

**非缺口：** 池内 qfq/basic/moneyflow 交叉缺失 = 0（相对本次扫描）。

## 8. Delta vs A0 T3 Gaps（2026-07-15）

| Item | A0 T3 | A1 T2 (now) |
|------|-------|-------------|
| qfq nonempty | 65 | 65 |
| empty `510300.SH` | yes | yes |
| selected / pool | 61 | 61（registry） |
| pool∖qfq | n/a（当时选股自 cache） | **0** |
| cross-table holes | 0 | 0 |
| qfq date_max | 2026-03-31 | 2026-03-31 |
| row range | 622–783 | 622–783 |

本地 cache **未出现**相对 A0 的实质性退化；inventory 可直接承接湖合同草案。

## 9. Implications for Downstream

| WT | Use of this inventory |
|----|------------------------|
| A2 | 合同测夹具可绑定 61 池符号 + 现有 year 分区；断言无池内三表洞 |
| A3 | 优先：扩主板 qfq/basic/mf 以冲击 soft 80；填充 `510300.SH`；复查 staleness |
| A4 | QA 以本 inventory 为 baseline；禁止把 4 个 extra 或 `low_manipulation` 当最终 universe |

## 10. Non-actions（本 T2）

- No TuShare / network calls
- No cache / derived writes
- No registry 改版
- No Phase 4 / EXEC-002

## 11. Related Artifacts

- 湖/源合同：`.servo/worktrack/WT-R4-A1-lake-source-contract.md`
- A0 gaps：`.servo/worktrack/WT-R4-A0-data-gaps.md`
- 池：`inputs/pools/research_liquidity_quality/`
- 下一交付：`.servo/worktrack/WT-R4-A1-schema-draft.md`（T3）
