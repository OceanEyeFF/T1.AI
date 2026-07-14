---
title: "WT-T1-A1 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A1"
updated: "2026-07-14T18:20:00+08:00"
owner: "OceanEyeFF"
---

# WT-T1-A1 Plan / Task Queue

## Metadata

- worktrack_id: WT-T1-A1
- milestone_id: MS-T1-001
- updated: 2026-07-14T18:20:00+08:00
- current_phase: a1_approved_a2_completed
- selected_next_action_id: WT-T1-A3-init-on-request
- selected_next_action: Programmer Init WT-T1-A3 for Arch-v1 migration
- selection_reason: Del-A1 executed; Arch-v1 adopted; Cov-detail deferred to A4

## Task List

1. [x] Map tests surface (files, sizes, import/fixture patterns) — T1-A1-T1 — completed
2. [x] Classify candidates: migrate / delete / keep / defer-R4 — T1-A1-T2 — completed
3. [x] Draft target architecture (dirs, fixtures/factories, markers, fast/full) — T1-A1-T3 — completed
4. [x] Propose mild cov floor (Acc-balanced) — T1-A1-T4 — completed
5. [x] Publish consolidated inventory for approval — T1-A1-T5 — completed
   - evidence: `.servo/worktrack/WT-T1-A1-inventory.md`

## Current Next Action

- selected_next_action_id: WT-T1-A3-init-on-request
- selected_next_action: Programmer Init WT-T1-A3 for Arch-v1 migration
- selection_reason: Del-A1 executed; Arch-v1 adopted; Cov-detail deferred to A4
- selected_task_risk_level: medium（目录搬迁）
- selected_task_stop_condition: do not start A3 without explicit Init

## Evidence

- surface: 45 files / ~654 tests / ~9.7k LOC
- defer_r4_count: 0
- deletes_executed: true (Del-A1 only)
- moves_executed: false
- existing_fail_under: 90 (pyproject; detail deferred to A4)
- pytest_del_a1: 6 passed

## Schedule Handoff

- suggested_next_route: Init WT-T1-A3（Arch-v1）
- needs_approval: yes — Worktrack Init for A3
