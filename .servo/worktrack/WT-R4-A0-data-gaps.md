---
title: "WT-R4-A0 T3 Data Gaps"
artifact_type: "worktrack-data-gaps"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A0"
updated: "2026-07-15T10:09:49+08:00"
owner: "OceanEyeFF"
live_pull: "none"
---

# WT-R4-A0 T3 — Cache-first Select & Data Gaps

## Run Summary

- policy: **cache_first / no live**
- run_at: `2026-07-15T10:09:49+08:00`
- universe: `65` symbols from `inputs/data/cache/tushare_qfq/` with parquet
- scored: `62`
- selected: `61` (soft_target=80, hard_cap=100, threshold=55.0)
- reject_count: `2`
- index_anchor `510300.SH` available: `False`
- amount_unit: TuShare 千元 → 亿元 via `/1e5` (T3 hotfix; was incorrectly `/1e8`)
- evidence: `.servo/worktrack/WT-R4-A0-t3-select-run-notes.json`

## Selected Symbols

`601318`, `601899`, `002594`, `601138`, `600111`, `603993`, `601600`, `601012`, `603799`, `002230`, `603019`, `000063`, `002460`, `600150`, `600549`, `000977`, `600406`, `600519`, `002466`, `600362`, `000630`, `600036`, `000807`, `600893`, `601985`, `002179`, `600050`, `600900`, `600760`, `600795`, `000333`, `000858`, `600438`, `601168`, `600570`, `603083`, `000768`, `002415`, `600256`, `600905`, `600011`, `601989`, `600372`, `600188`, `000733`, `600588`, `601857`, `603236`, `601225`, `600028`, `000001`, `003816`, `600583`, `600845`, `600967`, `000096`, `601088`, `601808`, `600339`, `601728`, `002554`

## Reject Reason Counts

| reason | count |
|---|---:|
| H7_limit_hits | 2 |

## Cache Inventory

| dataset | with_data | empty_dirs |
|---|---:|---|
| `tushare_qfq` | 65 | `510300.SH` |
| `tushare_daily_basic` | 65 | — |
| `tushare_moneyflow` | 65 | — |

- qfq row-count range: 622–783
- qfq date_max observed: `2026-03-31`

## Cross-table Gaps (qfq ∩ others)

- qfq missing daily_basic: **0** → none
- qfq missing moneyflow: **0** → none
- daily_basic without qfq: **0** → none

## Material Gaps / Deferrals

1. **Universe too small for soft_target 80** — cache only ~65 main-board symbols with qfq; selected `61` << 80. **Do not live-fill in A0**; expand universe at A3 lake fill.
2. **510300.SH index anchor empty** — directory exists under `tushare_qfq/510300.SH` but **0 parquet** files → `index_available=false`; D5 market_synchronicity stays neutral (~50). Need ETF/index qfq fill (A3 / limited-live L2 later).
3. **ChiNext present but hard-filtered** — `300750.SZ` in cache; excluded by H1 (expected).
4. **Floor recommendation (≥20)** — **met** (selected=61). Soft target 80 **not met** due to cache universe size; proceed to T4 as research snapshot with explicit size-deficit note.
5. **Amount unit fix (implementation)** — corrected TuShare 千元→亿元 (`/1e5`); prior `/1e8` caused mass `H5_amount_floor`. Logged for audit; aligns with `tushare_source` docs.

## Non-actions

- No TuShare live pulls
- No token use
- No registry export (deferred to T4)

## Handoff

- next: R4-A0-T4 registry-export `custom_research_liquidity_quality_v1` with selected set + size-deficit notes
- A3 lake should prioritize: broader main-board qfq/basic/mf + fill `510300.SH`
