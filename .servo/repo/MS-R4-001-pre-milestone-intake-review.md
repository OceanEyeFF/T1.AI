---
title: "MS-R4-001 Pre-Milestone Intake Review (Draft)"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-R4-001"
updated: "2026-06-23T03:00:00+08:00"
updated_by: "codex"
---

# MS-R4-001 Pre-Milestone Intake Review (Draft)

## Intake Status

- intake_status: planned_not_activated
- request_summary: >
  Programmer 要求以 TuShare 替代 AkShare 作为主数据源，从 2023 年起构建干净数据湖。
  当前状态：记录但不激活。需先完成 MS-R2-001（目录排布）和 MS-R3-001（深度清理）。
- programmer_confirmed: false
- ready_for_init_milestone: false
- intake_skipped: false

## Purpose

- 以 TuShare API 替代 AkShare 作为唯一数据源
- 从 2023-01-01 起拉取全量 A 股（mainboard only）日K（qfq）、资金流（moneyflow）、基本面（daily_basic）
- 输出到 `inputs/data/cache/`（parquet 格式，按 symbol + year 分区）
- 构建高阶衍生特征层：动量、波动率、技术指标 → `inputs/data/derived/`
- 为后续 X×Y×Z 滚动训练矩阵提供干净数据底座

## Open Questions (未确认)

1. **TuShare API 频率限制**：stk_moneyflow 接口有 200次/分钟限制，全量拉取需要预估 token 配额和分钟级等待策略
2. **数据范围**：全市场 5000+ 股票 vs 精选 70 只（sectors_70）？当前 pools/ 只有 14 只 low_manipulation
3. **缓存策略**：已有 `inputs/data/cache/tushare_*` 的 parquet 缓存是否可以直接复用？
4. **与后续 Milestone 的衔接**：数据湖构建完成后，立即进入 X×Y×Z 全量训练测试还是先做数据质量审计？

## Blocks

- MS-R2-001 未完成（当前 active）
- MS-R3-001 未开始（planned）
- TuShare token 配额未确认
- 数据范围未确认

## Skip Record

- intake_skipped: false
