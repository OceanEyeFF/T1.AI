---
title: "Milestone Backlog"
artifact_type: "milestone-backlog"
updated: "2026-07-14T17:24:00+08:00"
updated_by: "cursor-close-r3-init-t1-with-programmer-confirmation"
---

# Milestone Backlog

> Live backlog only contains `planned` and `active` milestones. Completed or superseded milestones belong in `.servo/repo/milestone-history.md`.

## Pipeline Summary

- active_count: 1
- planned_count: 1
- completed_count: 8
- superseded_count: 0
- active_milestone: MS-T1-001

## Active

### MS-T1-001

- milestone_id: MS-T1-001
- title: 广义测试体系清理（T-heavy）
- purpose: 对 tests/ 做架构级重写（分层、fixtures、markers、CI fast/full）；经批准退役死测；温和 cov 门禁；完成后启动 MS-R4
- status: active
- milestone_kind: goal-driven
- priority: 3
- depends_on_milestones: MS-R3-001
- precedes: MS-R4-001
- created_by: programmer
- created_at: 2026-07-14T17:24:00+08:00
- activated_at: 2026-07-14T17:24:00+08:00
- activated_by: OceanEyeFF
- artifact_path: .servo/milestone/MS-T1-001.md
- pre_milestone_intake: .servo/repo/MS-T1-001-pre-milestone-intake-review.md
- milestone_branch: milestone/MS-T1-001-test-suite-rewrite
- decisions_locked: D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed
- worktrack_list:
  - WT-T1-A1 (completed): inventory + Arch-v1 + Del-A1 approval
  - WT-T1-A2 (completed): Del-A1 executed
  - WT-T1-A3 (completed): Arch-v1 migration; pytest 396 passed
  - WT-T1-A4 (planned): markers + CI 分层 + cov 门禁（数值 A4 实测）+ 文档 + R4 延后交接
- updated: 2026-07-14T18:45:00+08:00
- updated_by: cursor-WT-T1-A3-arch-v1

## Planned

### MS-R4-001

- milestone_id: MS-R4-001
- title: TuShare 数据湖构建
- purpose: 以 TuShare 替代 AkShare 作为主数据源，从 2023 年起构建干净数据底座
- status: planned
- milestone_kind: goal-driven
- priority: 5
- depends_on_milestones: MS-T1-001
- created_by: programmer
- created_at: 2026-06-23T03:00:00+08:00
- note: 记录但不激活；D2=S1 — 需先完成 MS-T1-001（MS-R3-001 已完成）
- pre_milestone_intake: .servo/repo/MS-R4-001-pre-milestone-intake-review.md
