---
title: "Milestone Backlog"
artifact_type: "milestone-backlog"
updated: "2026-06-23T04:00:00+08:00"
updated_by: "codex-with-programmer-acceptance"
---

# Milestone Backlog

> Live backlog only contains `planned` and `active` milestones. Completed or superseded milestones belong in `.servo/repo/milestone-history.md`.

## Pipeline Summary

- active_count: 0
- planned_count: 2
- completed_count: 7
- superseded_count: 0
- active_milestone: none

## Planned

### MS-R3-001

- milestone_id: MS-R3-001
- title: 旧文件深度清理
- purpose: 删除 docs/archive/ 中已过期的历史文档、旧实验 TOML、旧脚本、旧 checkpoint，瘦身 Repo
- status: planned
- milestone_kind: goal-driven
- priority: 2
- depends_on_milestones: MS-R2-001
- created_by: programmer
- created_at: 2026-06-23T03:00:00+08:00
- note: 待 pre-milestone intake

### MS-R4-001

- milestone_id: MS-R4-001
- title: TuShare 数据湖构建
- purpose: 以 TuShare 替代 AkShare 作为主数据源，从 2023 年起构建干净数据底座
- status: planned
- milestone_kind: goal-driven
- priority: 5
- depends_on_milestones: MS-R3-001
- created_by: programmer
- created_at: 2026-06-23T03:00:00+08:00
- note: 记录但不激活；需先完成 R2-001 和 R3-001
- pre_milestone_intake: .servo/repo/MS-R4-001-pre-milestone-intake-review.md
