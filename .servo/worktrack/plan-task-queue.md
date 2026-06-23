---
title: "WT-S2-A2-next Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
updated: "2026-06-22T11:12:24+08:00"
owner: "OceanEyeFF"
---

# WT-S2-A2-next Plan / Task Queue

## Metadata

- worktrack_id: WT-S2-A2-next
- milestone_id: MS-S2-001
- updated: 2026-06-22T11:12:24+08:00
- current_phase: closed
- contract_ref: .servo/worktrack/contract.md
- queue_status: active
- task_window_id: WT-S2-A2-next-window-001
- window_boundary: compression contract only; no live TuShare calls or A3 sample registration.

## Task List

1. [x] Compress A1 into A3 input contract
   - task_id: S2-A2N-T1
   - status: completed
   - priority: P1
   - assigned: current-carrier
   - depends_on: none
   - risk_level: low
   - acceptance: A3 input contract limits A3 to base universe, liquid large-cap proxy, and at most one low-control-proxy candidate path.
   - evidence_ref: docs/modules/stock_pool_a3_input_contract_MS_S2_001.md
   - stop_condition: stop if compression expands into A3 execution or provider calls.
2. [x] Defer over-broad A1 layers
   - task_id: S2-A2N-T2
   - status: completed
   - priority: P1
   - assigned: current-carrier
   - depends_on: S2-A2N-T1
   - risk_level: low
   - acceptance: Mid/small-cap observation and suspected-control observation are explicitly out of A3.
   - evidence_ref: docs/modules/stock_pool_a3_input_contract_MS_S2_001.md#A3-Non-Goals
   - stop_condition: stop if suspected-control or small-cap sample construction remains in A3 entry scope.
3. [x] Validate compression boundary
   - task_id: S2-A2N-T3
   - status: completed
   - priority: P1
   - assigned: current-carrier
   - depends_on: S2-A2N-T2
   - risk_level: low
   - acceptance: Diff hygiene passes and no A3 execution occurs.
   - evidence_ref: .servo/worktrack/gate-evidence.md
   - stop_condition: stop if validation fails or control state allows A3 without review.

## Current Next Action

- selected_next_action_id: MS-S2-001-mid-review-before-A3
- selected_next_action: Stop for programmer mid-review before A3.
- selection_reason: A2-next compression is complete; A3 remains blocked pending programmer review of the narrowed input contract.
- selected_task_acceptance: Programmer reviews compressed A3 input contract before A3 starts.
- selected_task_risk_level: low
- selected_task_stop_condition: stop before provider calls, A2 implementation/tests, A3 sample registration, push, merge, branch deletion, release, model revalidation, or signal promotion.

## Dispatch Packet

- dispatch_packet_ready: false
- dispatch_mode: current-carrier
- carrier_decision: current-carrier because the task is a small docs/research slice over live dirty planning artifacts and needs precise scope control.
- selected_next_action_id: MS-S2-001-mid-review-before-A3
- task_brief: Present A2-next compression evidence for programmer review before A3.
- shared_fact_pack:
  - goal_charter: .servo/goal-charter.md
  - milestone: .servo/milestone/MS-S2-001.md
  - contract: .servo/worktrack/contract.md
  - intake_review: .servo/worktrack/MS-S2-001-WT-S2-A2-next-intake-review.md
- context_budget:
  - must_read: docs/modules/stock_pool_a3_input_contract_MS_S2_001.md; docs/modules/stock_pool_stratification_contract_MS_S2_001.md; .servo/worktrack/contract.md
  - may_read: .servo/worktrack/s2-a2-closeout-report.md; .servo/worktrack/S2-A2-registry-schema-gap-report.md
  - do_not_read: generated data/cache files and large reports unless directly needed
- next_route: Programmer mid-review; A3 init blocked until review passes.

## Acceptance Alignment

- currently_addressed_acceptance: WT-S2-A2-next compression completed.
- remaining_acceptance: programmer review before A3, then A3/A4 if approved.
