---
title: "WT-R4-A4 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-24T09:40:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A4 Plan / Task Queue

## Metadata

- worktrack_id: WT-R4-A4
- milestone_id: MS-R4-001
- updated: 2026-07-24T09:40:00+08:00
- current_phase: t3_complete
- selected_next_action_id: R4-A4-T4
- selected_next_action: Hygiene AO-O1 allowlist + AO-O2 dataset_builder (+ AO-O3 doc)
- selection_reason: T3 load API done; next A4-D4 hygiene AO-O1/O2
- execution_not_started: false
- t1_status: completed
- t2_status: completed
- t2_completed_at: 2026-07-23T20:55:00+08:00
- t2_notes: .servo/worktrack/WT-R4-A4-t2-notes.md
- t3_status: completed
- t3_completed_at: 2026-07-24T09:40:00+08:00
- t3_notes: .servo/worktrack/WT-R4-A4-t3-notes.md
- live_policy: zero_live
- contract_ref: .servo/worktrack/WT-R4-A4-contract.md

## Task List

1. [x] Derived layout + schema contract — **R4-A4-T1** — completed
2. [x] Minimal derived builder (cache → derived; Return5/10/20 + RSI) — **R4-A4-T2** — completed
3. [x] Reproducible load API + Arch-v1 tests — **R4-A4-T3** — completed
4. [ ] Hygiene: AO-O1 allowlist + AO-O2 dataset_builder tests (+ AO-O3 doc) — **R4-A4-T4** — pending
5. [ ] QA report + consistency + Gate/Close packet — **R4-A4-T5** — pending
6. [ ] Formal Gate + Close — **R4-A4-GATE** — pending

## Current Next Action

- selected_next_action_id: R4-A4-T4
- selected_next_action: Hygiene AO-O1 allowlist + AO-O2 dataset_builder (+ AO-O3 doc)
- blocked_until: programmer 「开始 T4」or Dispatch

## Schedule Handoff

- suggested_next_route: Dispatch R4-A4-T4 on request
- needs_approval: yes for commit/push; live batches (none planned)
- stop_conditions:
  - no full-campaign / train / Phase4 / EXEC-002
  - no soft80 expansion
  - no blind merge develop
  - no token in repo
