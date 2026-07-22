---
title: "WT-R4-A3 Plan / Task Queue"
artifact_type: "worktrack-plan-task-queue"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
updated: "2026-07-22T14:16:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A3 Plan / Task Queue

## Metadata

- worktrack_id: WT-R4-A3
- milestone_id: MS-R4-001
- updated: 2026-07-22T14:16:00+08:00
- current_phase: initialized
- selected_next_action_id: R4-A3-T1
- selected_next_action: Wire approved caps into TuShare fetch limiter (zero live)
- selection_reason: A3_Q1 P1 — enforce before any live; Init complete
- execution_not_started: true
- init_completed_at: 2026-07-22T14:16:00+08:00
- contract_ref: .servo/worktrack/WT-R4-A3-contract.md
- intake_review_ref: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- init_defaults:
  A3_Q1: P1_caps_then_510300_staleness
  A3_Q2: keep_v1_until_reselect
  A3_Q3: defer_hygiene

## Task List

1. [ ] Caps enforce on fetch path — **R4-A3-T1** — pending (selected)
2. [ ] Frequency-wall + resume (concurrency=1, batch≤50, dry-run tests) — **R4-A3-T2** — pending
3. [ ] Limited-live fill: 510300 + pool-61 staleness — **R4-A3-T3** — pending (**requires explicit live batch approve**)
4. [ ] Soft80 P2 progress or residual update — **R4-A3-T4** — pending
5. [ ] Consistency + Gate/Close packet — **R4-A3-T5** — pending
6. [ ] Formal Gate + Close — **R4-A3-GATE** — pending

## Current Next Action

- selected_next_action_id: R4-A3-T1
- selected_next_action: Implement runtime enforce of `r4_approved_rpm` / `r4_approved_daily_per_api` in TuShare fetch limiter; unit/contract tests; **zero live**
- selection_reason: A3_Q1 — caps+limiter before any quota-consuming call
- selected_task_stop_condition: >
  no live pull; no token in repo; no full-campaign; no commit/push without approve;
  do not start T3 without programmer live-batch approve
- suggested_deliverable: >
  limiter wired to approved caps + tests proving throttle/budget accounting without network

## Schedule Handoff

- suggested_next_route: WorktrackScope.Dispatch → R4-A3-T1
- needs_approval: yes for commit/push; **yes for any live (T3+)**
- execution_not_started: true
- live_gate: blocked_until_T1_T2_done_and_programmer_batch_approve
- next_after_t1: R4-A3-T2 (freq-wall/resume)
- deferred_hygiene: dataset_old_tests; allowlist; toml_dual_track; market_state (A3_Q3)
