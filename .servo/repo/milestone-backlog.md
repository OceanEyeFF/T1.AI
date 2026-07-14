---
title: "Milestone Backlog"
artifact_type: "milestone-backlog"
updated: "2026-07-14T11:35:00+08:00"
updated_by: "cursor-init-milestone-with-programmer-confirmation"
---

# Milestone Backlog

> Live backlog only contains `planned` and `active` milestones. Completed or superseded milestones belong in `.servo/repo/milestone-history.md`.

## Pipeline Summary

- active_count: 1
- planned_count: 1
- completed_count: 7
- superseded_count: 0
- active_milestone: MS-R3-001

## Active

### MS-R3-001

- milestone_id: MS-R3-001
- title: 旧文件深度清理
- purpose: 以治理模式（inventory→批准→分批删除）按 P3 偏瘦身默认分类清除过期文档/脚本/checkpoint；T2 分流 R2 遗留 2 fail；为 MS-R4 腾出干净仓库面
- status: active
- milestone_kind: goal-driven
- priority: 2
- depends_on_milestones: MS-R2-001
- created_by: programmer
- created_at: 2026-06-23T03:00:00+08:00
- activated_at: 2026-07-14T11:35:00+08:00
- activated_by: OceanEyeFF
- artifact_path: .servo/milestone/MS-R3-001.md
- pre_milestone_intake: .servo/repo/MS-R3-001-pre-milestone-intake-review.md
- milestone_branch: milestone/MS-R3-001-deep-cleanup
- decisions_locked: D1=B, D2=T2, D3=P3, D4=confirmed
- worktrack_list:
  - WT-R3-A1 (completed): inventory + 引用审计 + 2-fail 定性
  - WT-R3-A2 (completed): 按批准清单分批删除/退役
  - WT-R3-A3 (planned): 文档一致性 + 可修测 + R4 defer 交接
- updated: 2026-07-14T11:35:00+08:00
- updated_by: cursor-init-milestone-with-programmer-confirmation

## Planned

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
- note: 记录但不激活；需先完成 MS-R3-001
- pre_milestone_intake: .servo/repo/MS-R4-001-pre-milestone-intake-review.md
