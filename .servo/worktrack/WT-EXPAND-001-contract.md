---
title: "WT-EXPAND-001 Worktrack Contract"
artifact_type: "worktrack-contract"
updated: "2026-06-22T13:15:00+08:00"
owner: "OceanEyeFF"
---

# WT-EXPAND-001 Worktrack Contract

> Post-MS-S2-001 expansion: extend stock universe from 8 to 64, build multi-indicator scoring, register low-manipulation pool.

## Metadata

- worktrack_id: WT-EXPAND-001
- title: 股票池扩展 + 综合低控盘评分 + 注册
- branch: milestone/MS-S2-001-stock-pool-stratification
- baseline_branch: develop
- baseline_ref: 98ef372
- owner: OceanEyeFF
- updated: 2026-06-22T13:15:00+08:00
- contract_status: closed

## Milestone Binding

- milestone_id: MS-S2-001 (completed; post-milestone append by programmer request)
- programmer_authorization: programmer requested universe expansion after MS-S2-001 acceptance

## Node Type

- type: fetch/compute/registry
- gate_criteria: all 177 TuShare requests succeed; 64 stocks scored; new pool registered and smoke-verified

## Task Goal

- goal_summary: Fetch sectors_70 data via TuShare, run multi-indicator scoring on 64 stocks, register top-scoring pool.

## Scope

- in_scope: TuShare data fetch (daily + daily_basic + moneyflow), composite scoring, pool registration, export smoke
- out_of_scope: model training, 3/5/10d revalidation, signal promotion, git commit/push

## Acceptance Criteria

- [x] 177/177 TuShare requests succeed (cache expanded from 8 to 65+ symbols)
- [x] `scripts/score_low_manipulation.py` runs on full 64-stock universe
- [x] `custom_low_manipulation_v1` registered with 14 stocks (score >= 60)
- [x] Registry load + export smoke pass
- [x] No model training, no signal promotion, no production calls
