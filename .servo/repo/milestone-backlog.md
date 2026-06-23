---
title: "Milestone Backlog"
artifact_type: "milestone-backlog"
updated: "2026-06-22T12:45:00+08:00"
updated_by: "codex-with-programmer-acceptance"
---

# Milestone Backlog

> Live backlog only contains `planned` and `active` milestones. Completed or superseded milestones belong in `.servo/repo/milestone-history.md`.

## Pipeline Summary

- active_count: 1
- planned_count: 0
- completed_count: 5
- superseded_count: 0
- active_milestone: MS-R1-001

## Active

### MS-R1-001

- milestone_id: MS-R1-001
- title: 模型层提取与统一治理
- purpose: 将散落在脚本和 monolithic 文件中的模型代码提取为统一 ModelABC 接口的自包含实现
- status: active
- milestone_kind: goal-driven
- priority: 4
- depends_on_milestones: MS-R0-001
- created_by: codex-with-programmer-confirmation
- created_at: 2026-06-23T00:00:00+08:00
- updated: 2026-06-23T00:00:00+08:00
- updated_by: codex
- artifact_path: .servo/milestone/MS-R1-001.md
- pre_milestone_intake_review: .servo/repo/MS-R1-001-pre-milestone-intake-review.md
- worktrack_list:
  - WT-R1-A1 (planned): 从 develop 提取 LSTM/XGB 源码并审计差异
  - WT-R1-A2 (planned): 定义 ModelABC 接口 + 模型 registry
  - WT-R1-A3 (planned): Transformer 重构
  - WT-R1-A4 (planned): LSTM 统一实现
  - WT-R1-A5 (planned): XGBoost 封装实现
  - WT-R1-A6 (planned): 下游脚本解耦
  - WT-R1-A7 (planned): 维护文档
  - WT-R1-A8 (planned): 铲平旧实现

## Planned

- none
