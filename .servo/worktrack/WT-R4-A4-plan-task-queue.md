---
title: "WT-R4-A4 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-23T20:45:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A4 Plan / Task Queue

## Metadata

- worktrack_id: WT-R4-A4
- milestone_id: MS-R4-001
- updated: 2026-07-23T20:45:00+08:00
- current_phase: t1_complete
- selected_next_action_id: R4-A4-T2
- selected_next_action: Minimal derived builder (cache → derived; Return5/10/20 + RSI)
- selection_reason: T1 schema frozen; next is A4-D2 builder (zero live)
- execution_not_started: false
- t1_status: completed
- t1_completed_at: 2026-07-23T20:45:00+08:00
- t1_notes: .servo/worktrack/WT-R4-A4-t1-notes.md
- t1_schema: .servo/worktrack/WT-R4-A4-derived-schema.md
- live_policy: zero_live
- contract_ref: .servo/worktrack/WT-R4-A4-contract.md
- init_defaults_locked: A4_Q1=M1_ret_rsi; A4_Q2=inputs_derived_year_parts; A4_Q3=md_plus_json; A4_Q4=O1_O2_in_AC; A4_Q5=zero_live; A4_Q6=registry61_trial60; A4_Q7=wt_close_only

## Task List

1. [x] Derived layout + schema contract — **R4-A4-T1** — completed
2. [ ] Minimal derived builder (cache → derived; Return5/10/20 + RSI) — **R4-A4-T2** — pending
3. [ ] Reproducible load API + Arch-v1 tests — **R4-A4-T3** — pending
4. [ ] Hygiene: AO-O1 allowlist + AO-O2 dataset_builder tests (+ AO-O3 doc) — **R4-A4-T4** — pending
5. [ ] QA report + consistency + Gate/Close packet — **R4-A4-T5** — pending
6. [ ] Formal Gate + Close — **R4-A4-GATE** — pending

## Current Next Action

- selected_next_action_id: R4-A4-T2
- selected_next_action: Cache-only derived builder writing momentum/technical year parts
- blocked_until: programmer 「开始 T2」or Dispatch
- notes: >
  T2 零 live（refresh=False）。复用 ashare_lab.features；禁止第二套特征真理。

## Schedule Handoff

- suggested_next_route: Dispatch R4-A4-T2 on request
- needs_approval: yes for commit/push; live batches (none planned); milestone final acceptance (A4_Q7)
- execution_not_started: false
- stop_conditions:
  - no full-campaign / train / Phase4 / EXEC-002
  - no soft80 expansion
  - no blind merge develop
  - no token in repo
