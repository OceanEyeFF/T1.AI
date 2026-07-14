---
title: "WT-R3-A1 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A1"
updated: "2026-07-14T12:40:00+08:00"
owner: "OceanEyeFF"
---

# WT-R3-A1 Plan / Task Queue

## Metadata

- worktrack_id: WT-R3-A1
- milestone_id: MS-R3-001
- updated: 2026-07-14T12:40:00+08:00
- current_phase: awaiting_programmer_inventory_approval
- contract_ref: .servo/worktrack/WT-R3-A1-contract.md
- inventory_ref: .servo/worktrack/WT-R3-A1-inventory.md
- intake_review_ref: .servo/worktrack/MS-R3-001-WT-R3-A1-intake-review.md
- queue_status: active
- task_window_id: WT-R3-A1-window-001
- window_boundary: readonly inventory complete; no deletes executed.

## Task List

1. [x] Inventory docs candidates — R3-A1-T1 — completed
2. [x] Inventory checkpoints + caches — R3-A1-T2 — completed
3. [x] Inventory scripts + experiment configs — R3-A1-T3 — completed
4. [x] Reference audit pass — R3-A1-T4 — completed
5. [x] Triage R2 residual 2 pytest failures (T2) — R3-A1-T5 — completed
6. [x] Publish consolidated inventory for approval — R3-A1-T6 — completed
   - evidence: `.servo/worktrack/WT-R3-A1-inventory.md`

## Current Next Action

- selected_next_action_id: WT-R3-A1-programmer-approve-inventory
- selected_next_action: Programmer reviews and approves Batch A/B in WT-R3-A1-inventory.md
- selection_reason: A1 deliverable complete; A2 blocked until delete batch approval
- selected_task_risk_level: high（后续删除）
- selected_task_stop_condition: do not start A2 deletes without explicit batch approval

## Evidence

- pytest: 395 passed / 2 failed（F1 double-path symbols_csv；F2 default configs/stock_pools）
- both fails: R3-fixable；defer R4 count = 0
- deletes_executed: false

## Schedule Handoff

- suggested_next_route: Programmer approval → Init WT-R3-A2（approved deletes only）+ plan WT-R3-A3 path fixes
- execution_of_deletes: not_started
- needs_approval: yes — inventory batch approval before A2
