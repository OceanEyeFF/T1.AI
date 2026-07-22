---
title: "WT-R4-A3 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
updated: "2026-07-22T17:45:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A3 Plan / Task Queue

## Metadata

- worktrack_id: WT-R4-A3
- milestone_id: MS-R4-001
- updated: 2026-07-22T17:45:00+08:00
- current_phase: t2_complete
- selected_next_action_id: R4-A3-T3
- selected_next_action: Limited-live fill 510300 + pool-61 staleness (requires live batch approve)
- selection_reason: T1–T2 done (caps + freq-wall/resume); live gated
- execution_not_started: false
- t1_status: completed
- t1_notes: .servo/worktrack/WT-R4-A3-t1-notes.md
- t2_status: completed
- t2_completed_at: 2026-07-22T17:45:00+08:00
- t2_notes: .servo/worktrack/WT-R4-A3-t2-notes.md
- contract_ref: .servo/worktrack/WT-R4-A3-contract.md

## Task List

1. [x] Caps enforce on fetch path — **R4-A3-T1** — completed
2. [x] Frequency-wall + resume — **R4-A3-T2** — completed
3. [ ] Limited-live fill: 510300 + pool-61 staleness — **R4-A3-T3** — pending (**requires explicit live batch approve**)
4. [ ] Soft80 P2 progress or residual update — **R4-A3-T4** — pending
5. [ ] Consistency + Gate/Close packet — **R4-A3-T5** — pending
6. [ ] Formal Gate + Close — **R4-A3-GATE** — pending

## Current Next Action

- selected_next_action_id: R4-A3-T3
- selected_next_action: >
  Limited-live fill via tushare_batch + DataLake/cache write for 510300.SH
  and approved pool-61 staleness; **blocked until programmer live-batch approve**
- selection_reason: A3_Q1 P1 live package; M1/normal gate
- selected_task_stop_condition: >
  no live without explicit approve; no full-campaign; token env-only;
  no commit/push without approve
- suggested_deliverable: >
  approved manifest + fill evidence for 510300 (+ staleness list) under caps/resume

## Schedule Handoff

- suggested_next_route: Wait programmer live-batch approve → Dispatch R4-A3-T3
- needs_approval: **yes — live batch**; yes for commit/push
- live_gate: blocked_until_programmer_batch_approve
- next_after_t3: R4-A3-T4 (soft80 P2)
- t2_evidence: 19 passed (batch + caps suites)
