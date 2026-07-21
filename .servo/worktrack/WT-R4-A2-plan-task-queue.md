---
title: "WT-R4-A2 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
updated: "2026-07-21T09:50:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A2 Plan / Task Queue

## Metadata

- worktrack_id: WT-R4-A2
- milestone_id: MS-R4-001
- updated: 2026-07-21T09:50:00+08:00
- current_phase: t2_complete_t3_pending
- selected_next_action_id: R4-A2-T3
- selected_next_action: Disk/schema contract tests vs A1 inventory+schema
- selection_reason: T2 bound cache-first DataLake to A1; next disk contract
- execution_not_started: false
- t1_completed_at: 2026-07-20T22:30:00+08:00
- t1_notes: .servo/worktrack/WT-R4-A2-t1-notes.md
- t2_completed_at: 2026-07-21T09:50:00+08:00
- t2_notes: .servo/worktrack/WT-R4-A2-t2-notes.md

## Task List

1. [x] Scoped `ashare_infra` land from develop — **R4-A2-T1** — completed
2. [x] Cache-first DataLake path bound to A1 contract — **R4-A2-T2** — completed
3. [ ] Disk/schema contract tests vs A1 inventory+schema (pool 61; 510300 unavailable) — **R4-A2-T3**
4. [ ] Integration tests: cache-hit / as_of / no-direct (done partial); optional caps→configs — **R4-A2-T4**
5. [ ] Gate evidence + closeout — **R4-A2-T5**
6. [ ] Formal Gate + Close — **R4-A2-GATE**

## Current Next Action

- selected_next_action_id: R4-A2-T3
- selected_next_action: Contract tests for cache layout / columns / pool 61 / 510300 gap
- selection_reason: A1 inventory+schema frozen; path live
- selected_task_stop_condition: no live; no fill; no ashare_exec; commit/push gated
- suggested_deliverable: tests under tests/contract/… referencing A1 artifacts

## Schedule Handoff

- suggested_next_route: WorktrackScope.Dispatch R4-A2-T3
- t2_evidence: 74 passed; make_r4_datalake + consumer cutover + no-direct contract
- note: no-direct-load_or_fetch landed in T2; T4 may add cache-hit/as_of integration + caps promote
