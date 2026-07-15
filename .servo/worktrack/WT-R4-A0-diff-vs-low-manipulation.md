---
title: "WT-R4-A0 Diff vs low_manipulation"
artifact_type: "worktrack-pool-diff"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A0"
updated: "2026-07-15T11:08:00+08:00"
owner: "OceanEyeFF"
contrast_only: true
live_pull: "none"
---

# WT-R4-A0 T5 — Diff vs `low_manipulation` / `custom_low_manipulation`

> 旧池仅作**对照基线**，不覆写、不删除、不晋升为 A0 终态 universe。

## 1. Compared Artifacts

| Side | Registry ID | Version | Path | Count |
|---|---|---|---|---:|
| Old (contrast) | `custom_low_manipulation` | `v1` | `inputs/pools/low_manipulation/` | **14** |
| New (A0) | `custom_research_liquidity_quality_v1` | `1` | `inputs/pools/research_liquidity_quality/` | **61** |

Colloquial alias `custom_low_manipulation_v1` = `{id=custom_low_manipulation, version=v1}`。

## 2. Set Diff (symbols)

| Metric | Value |
|---|---:|
| \|old\| | 14 |
| \|new\| | 61 |
| \|intersection\| | **14** |
| \|only_old\| | **0** |
| \|only_new\| | **47** |
| Jaccard \|∩\|/\|∪\| | 0.230 |
| old ⊆ new | **true** (100% coverage) |

### 2.1 Intersection (14) — all old members retained

`601899`, `603993`, `601138`, `601600`, `600150`, `600111`, `600519`, `601318`, `600050`, `000063`, `601168`, `600036`, `600900`, `603799`

### 2.2 Only in old — none

旧池无“被新策略硬过滤/阈值踢出”的成员；与当前 cache ∩ 新准则一致。

### 2.3 Only in new (47) — expansion under new thesis

相对旧池新增（按 symbol 排序）：

`000001`, `000333`, `000630`, `000733`, `000768`, `000807`, `000858`, `000977`, `002179`, `002230`, `002415`, `002460`, `002466`, `002554`, `002594`, `003816`, `600011`, `600028`, `600188`, `600256`, `600339`, `600362`, `600372`, `600406`, `600438`, `600549`, `600570`, `600583`, `600588`, `600760`, `600795`, `600845`, `600893`, `600905`, `600967`, `601012`, `601088`, `601225`, `601728`, `601808`, `601857`, `601985`, `601989`, `603019`, `603083`, `603236`

## 3. Thesis / Construction Diff（刻意）

| 维度 | `low_manipulation` | `research_liquidity_quality` |
|---|---|---|
| 命题 | 低控盘概率 proxy | 主板研究可交易卫生 / 数据完备 |
| 维度结构 | 6 维（scale 35% + … + moneyflow 5%） | 5 维（liquidity 30% + turnover 25% + completeness 20% + hygiene 15% + sync 10%） |
| 资金流角色 | 独立评分维 5% | **非独立维**；仅进入 data_completeness |
| 硬过滤叙事 | 主板排除 + score≥60 | H1–H7 卫生硬过滤 + score≥55 |
| 目标规模 | 历史 14（阈值 60） | 软 **80** / 硬 **100**（本快照 **61**） |
| 再平衡口径 | `frozen` | `monthly`（文档；A0 无调度器） |
| research_only | `false` | **`true`**（Gate 前） |
| 旧池角色 | 生产叙事候选 | **仅对照** |

结论：**超集扩展 + 命题换轨**，不是同准则微调。旧池 14 全进新池，说明在当前 cache 与新硬过滤下旧选股仍属“可交易卫生”集合；新增 47 只来自同一 cache 宇宙的卫生排序，而非旧控盘代理阈值。

## 4. Registry Metadata Diff

| Field | Old | New |
|---|---|---|
| `stock_pool_id` | `custom_low_manipulation` | `custom_research_liquidity_quality_v1` |
| `stock_pool_version` | `v1` | `1` |
| `pool_family` | `custom` | `custom` |
| `pool_label` | Low-Manipulation-Probability Pool… | 研究流动性卫生池 v1 |
| `construction_method` | 6-dimension composite… | hard-filters + 5-dimension hygiene… |
| `base_universe` | sectors_70 + quick8 cache… | cache-available main board first |
| `symbols_count` | 14 | 61 |
| `rebalance_frequency` | frozen | monthly |
| `is_research_only` | false | true |
| `owner` | WT-EXPAND-001 | stock_pool/research_liquidity_quality |

## 5. Size / Gate Implications

- 硬上限 100：**通过**（61）。
- 软目标 80：**未达**（deficit 19）——原因是 cache 宇宙过窄（见 T3 data-gaps），**不得**为凑数 live 补洞；留给 A3。
- 旧池不改为默认；A0 新池 `is_research_only=true`。
- `low_manipulation/` 目录：**未修改**。

## 6. Non-claims

- 不声称新池“更低控盘”或更高 alpha。
- 不声称旧池失效；仅记录集合与叙事差异。
- 不启动 live；不合并到训练默认可执行池。

## 7. Evidence Links

- New registry: `inputs/pools/research_liquidity_quality/`
- Old registry: `inputs/pools/low_manipulation/`
- T3 gaps: `.servo/worktrack/WT-R4-A0-data-gaps.md`
- T4 export: `.servo/worktrack/WT-R4-A0-t4-export-notes.md`
- Brief §4.1: `.servo/worktrack/WT-R4-A0-strategy-brief.md`

## 8. Handoff

- next: R4-A0-T6 focused tests/smoke finalize + closeout evidence
