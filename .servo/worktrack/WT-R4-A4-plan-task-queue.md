---
title: "WT-R4-A4 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-23T17:47:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A4 Plan / Task Queue

## Metadata

- worktrack_id: WT-R4-A4
- milestone_id: MS-R4-001
- updated: 2026-07-23T17:47:00+08:00
- current_phase: initialized
- selected_next_action_id: R4-A4-T1
- selected_next_action: Derived layout + schema contract (zero live)
- selection_reason: Init complete; first seeded action is A4-D1
- execution_not_started: true
- live_policy: zero_live
- contract_ref: .servo/worktrack/WT-R4-A4-contract.md
- init_defaults_locked: A4_Q1=M1_ret_rsi; A4_Q2=inputs_derived_year_parts; A4_Q3=md_plus_json; A4_Q4=O1_O2_in_AC; A4_Q5=zero_live; A4_Q6=registry61_trial60; A4_Q7=wt_close_only

## Task List

1. [ ] Derived layout + schema contract — **R4-A4-T1** — pending
2. [ ] Minimal derived builder (cache → derived; Return5/10/20 + RSI) — **R4-A4-T2** — pending
3. [ ] Reproducible load API + Arch-v1 tests — **R4-A4-T3** — pending
4. [ ] Hygiene: AO-O1 allowlist + AO-O2 dataset_builder tests (+ AO-O3 doc) — **R4-A4-T4** — pending
5. [ ] QA report + consistency + Gate/Close packet — **R4-A4-T5** — pending
6. [ ] Formal Gate + Close — **R4-A4-GATE** — pending

## Current Next Action

- selected_next_action_id: R4-A4-T1
- selected_next_action: Freeze derived layout/schema constants + README (zero live)
- blocked_until: programmer 「开始 T1」or Dispatch approval for execution start
- notes: >
  T1 零 live。T2–T3 仍零 live（cache-only）。T4 hygiene 无 live。
  T5 产出 QA + Gate packet。任何 live 须显式 M1/normal（默认禁止）。

## Schedule Handoff

- suggested_next_route: Dispatch R4-A4-T1 on request
- needs_approval: yes for commit/push; live batches (none planned); milestone final acceptance (A4_Q7)
- execution_not_started: true
- stop_conditions:
  - no full-campaign / train / Phase4 / EXEC-002
  - no soft80 expansion
  - no blind merge develop
  - no token in repo
