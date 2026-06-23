---
title: "WT-EXPAND-001 Closeout Report"
artifact_type: "worktrack-closeout-report"
worktrack_id: "WT-EXPAND-001"
updated: "2026-06-22T13:20:00+08:00"
owner: "OceanEyeFF"
---

# WT-EXPAND-001 Closeout Report

## Control Signal

- worktrack_id: WT-EXPAND-001
- closeout_status: closed
- gate_verdict: pass
- next_route: none (post-milestone append, no active milestone)

## Accepted Changes

### New Files

- `scripts/fetch_sectors70.py` — TuShare batch fetcher for sectors_70 universe
- `scripts/score_low_manipulation.py` — 6-dimension composite scoring system
- `configs/stock_pools/custom_low_manipulation_v1.toml` — 14-stock low-manipulation pool
- `configs/stock_pools/custom_low_manipulation_v1_symbols.csv`
- `configs/stock_pools/custom_low_manipulation_v1_metadata.json`

### Cache Expansion

- `tushare_qfq`: 9 → 66 symbols
- `tushare_daily_basic`: 8 → 65 symbols
- `tushare_moneyflow`: 8 → 65 symbols

### Pool Registered

- `custom_low_manipulation_v1`: 14 stocks, score >= 60 (top 22% of 64)
- Top 3: 601899 (紫金矿业, 80.8), 603993 (洛阳钼业, 74.5), 601138 (工业富联, 73.3)

## Validation

- 177/177 TuShare requests succeeded in 2.2 minutes
- 64 stocks scored across 6 dimensions
- Registry load + export smoke: pass
- `git diff --check`: pass

## Residual Risk

- Score thresholds uncalibrated; rankings may shift with broader universe or different lookback windows
- Moneyflow data quality not manually verified
- All caching and scoring is reproducible via committed scripts
