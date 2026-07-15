---
title: "WT-R4-A0 T4 Registry Export Notes"
artifact_type: "worktrack-export-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A0"
updated: "2026-07-15T10:27:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A0 T4 — Registry Export

## Assertions

- symbols_count: **61**
- hard_cap ≤100: **pass**
- soft_target ≤80: **not met** (deficit 19; documented; no live fill)
- export via: `export_stock_pool_artifacts()`
- live_pull: **none**

## Artifacts

| Role | Path |
|---|---|
| Registry record | `inputs/pools/research_liquidity_quality/config.toml` |
| Registry symbols | `inputs/pools/research_liquidity_quality/symbols.csv` |
| Construction snapshot | `inputs/pools/research_liquidity_quality/construction_snapshot.json` |
| Strategy pools export | `src/ashare_lab/stock_pool/research_liquidity_quality/pools/custom_research_liquidity_quality_v1/1/` (`symbols.csv`, `metadata.json`, `config.toml`) |
| Pipeline default export | `output/stock_pools/custom_research_liquidity_quality_v1/1/` |

## Registry Identity

- stock_pool_id: `custom_research_liquidity_quality_v1`
- stock_pool_version: `1`
- pool_family: `custom`
- is_research_only: `true`
- owner: `stock_pool/research_liquidity_quality`

## Handoff

- next: R4-A0-T5 diff vs `custom_low_manipulation` / `inputs/pools/low_manipulation`
