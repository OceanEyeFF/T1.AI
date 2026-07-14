---
title: "WT-R3-A3: F1/F2 路径修复 + 入口一致性"
artifact_type: "worktrack-contract"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A3"
status: "active"
node_type: "bugfix"
derived_from_milestone: true
created: "2026-07-14T15:10:00+08:00"
---

# WT-R3-A3 F1/F2 路径修复

## Control Signal

- branch: milestone/MS-R3-001-deep-cleanup
- baseline_branch: develop
- inventory_ref: .servo/worktrack/WT-R3-A1-inventory.md §8
- goal: 修复 R2 遗留 2 pytest 失败；使全量测试回到 397 pass（或等价全绿）

## Fixes

1. `inputs/pools/low_manipulation/config.toml` — `symbols_csv` 改为相对 registry 路径
2. `resolve_stock_pool_symbols` — 兼容 registry 相对路径与仓库相对路径
3. `scripts/build_sequence_dataset_market_state.py` — 默认 registry=`inputs/pools`；resolve/export 使用该目录

## Non-goals

- 数据湖 / 重训
- 再删 Batch C 保留项
