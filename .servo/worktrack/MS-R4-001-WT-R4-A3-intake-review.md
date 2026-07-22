---
title: "MS-R4-001 / WT-R4-A3 Intake Review"
artifact_type: "worktrack-intake-review"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
updated: "2026-07-22T14:16:00+08:00"
owner: "OceanEyeFF"
updated_by: "cursor-init-worktrack-WT-R4-A3"
---

# MS-R4-001 / WT-R4-A3 Intake Review

## Control Signal

```yaml
selected_worktrack_id: WT-R4-A3
selected_worktrack_title: 经批准的 limited-live 增量补洞 + 频率墙/简历策略（normal 模式）
target_milestone_id: MS-R4-001
derived_from_milestone: true
active_milestone_ref: .servo/milestone/MS-R4-001.md
active_milestone_branch: milestone/MS-R4-001-tushare-datalake
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
needs_programmer_init: false
auto_init: false
blocker: none
prerequisite_closed: WT-R4-A2 (pass_with_residuals @ 6a2413e / pin 4474da9)
init_completed: true
init_completed_at: 2026-07-22T14:16:00+08:00
contract_ref: .servo/worktrack/WT-R4-A3-contract.md
plan_task_queue_ref: .servo/worktrack/WT-R4-A3-plan-task-queue.md
init_result_ref: .servo/worktrack/WT-R4-A3-init-result.md
init_defaults_applied:
  A3_Q1: P1_caps_then_510300_staleness
  A3_Q2: keep_v1_until_reselect
  A3_Q3: defer_hygiene
upstream_ready:
  - make_r4_datalake (tushare/qfq/refresh=False)
  - inputs/configs/tushare_rate_limits.toml (180 rpm / 80000)
  - A1 frozen lake/source + inventory + schema
  - pool custom_research_liquidity_quality_v1@1 (61)
decisions_locked_from_milestone:
  - D2=L2_limited_live
  - D3=R1_audit_reuse
  - D5=tushare_primary_akshare_backup
  - CG2=M1_normal
  - pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
  - A1_caps: rpm=180 daily_per_api=80000
out_of_scope_explicit:
  - full-campaign / 全市场 silent pull
  - training / model promotion
  - Phase_4 / EXEC-002
  - blind_full_merge_of_develop
  - writing TUSHARE_TOKEN into repo
milestone_review_gate_ready: true
latest_review_status: effective_pass
milestone_review_count: 1
latest_review_checkpoint: MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00
effective_review_pass: true
review_invalidated_by: none
continuation_required: false
next_route: Init completed; Dispatch R4-A3-T1 on request
```

## Request Summary

```yaml
request_summary: >
  WT-R4-A3 已 Init（feature）。contract + plan queue 已播种；
  selected_next_action=R4-A3-T1（caps enforce；零 live）。
  T3+ live 须显式批次批准。执行尚未开始。
```

## Repo Fundamentals

```yaml
repo_fundamentals: pass
active_milestone: MS-R4-001
milestone_status: active
baseline_branch: develop
develop_tip: 7453daa
milestone_branch: milestone/MS-R4-001-tushare-datalake
milestone_tip: 4474da9
a2_gate: pass_with_residuals
a2_impl: c80b7ae + d21420f
a2_close: 6a2413e
goal_alignment: >
  A3 is the first approved live-capable slice: enforce L2 caps, fill
  inventory gaps (510300 + soft80 path), and implement frequency-wall
  pause/resume — without full-campaign or training.
prohibited_actions:
  - Silent full-campaign / 全市场 TuShare pull
  - Live without explicit M1/normal batch approve
  - Training / Phase4 / EXEC-002
  - Blind full merge of develop
  - Token-in-repo
  - commit/push without approval
```

## Snapshot Freshness

```yaml
snapshot_freshness: pass_with_caveat
evidence_refs:
  - .servo/worktrack/WT-R4-A2-closeout.md
  - .servo/worktrack/WT-R4-A2-gate-evidence.md
  - .servo/worktrack/WT-R4-A2-code-review-checklist.md
  - .servo/worktrack/WT-R4-A1-cache-inventory.md
  - .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md
  - inputs/configs/tushare_rate_limits.toml
  - src/ashare_infra/lake/r4_contract.py
caveat: >
  Milestone tip has DataLake + cutover (A2). develop@7453daa still carries
  EXEC/Phase4 lag — do not blind-merge. Caps file present; fetch path does
  not yet call r4_approved_*. 510300.SH has 0 parts on all three namespaces.
  Live requires TUSHARE_TOKEN in env at execution time (not now).
refresh_required_after: optional after A3 Init if tip moves
```

## Milestone Purpose Alignment

```yaml
milestone_purpose_alignment: pass
note: >
  CS1 soft80 residual + L2 limited-live (D2) + M1/normal (CG2) map directly
  to A3 charter. CS3 staleness/index fill and A4 QA remain downstream.
```

## Historical Conflict Risk

```yaml
historical_conflict_risk: medium_high
notes:
  - First live-quota-consuming WT in MS-R4-001 — policy surface is the risk
  - Frequency wall (doc290 / burst_pause) must be designed before large batches
  - Expanding toward soft80 may require cache-universe growth then pool reselect
    (registry version bump) — do not silently change v1@1 without decision
  - Hygiene residuals (dataset tests / allowlist) can dilute live campaign focus
worktrack_adjustment_recommendations: none
add_remove_worktrack_recommendations: none
```

## Proposed A3 Scope (for Init)

### In scope (core)

1. **Wire approved caps** (`r4_approved_rpm` / `r4_approved_daily_per_api`) into TuShare fetch limiter (enforce ≠ config-only)
2. **Frequency-wall / resume**: concurrency=1, burst pause on freq wall, per-batch ≤50 symbols, resumable manifests (A1 recommendations)
3. **L2 limited-live fill** (explicit batch approve):
   - Fill `510300.SH` parts (qfq / daily_basic / moneyflow as applicable)
   - Staleness refresh candidates from A1 inventory (e.g. early `date_max`)
   - Soft80 path: expand cache-eligible universe and/or reselect toward ≥80 ≤100 (version policy at Init)
4. **Evidence**: dry-run / budget accounting tests where possible; limited live only under approve; Gate packet

### In scope (optional hygiene — Init choose)

5. Fix `tests/integration/dataset/test_dataset_builder.py` after default→tushare
6. Tighten `test_no_direct_load_or_fetch` allowlist (drop or narrow `ashare_infra.data`)
7. Clarify `data_source.toml` vs R4 factory dual-track (doc or default flip)
8. Defer vs include `build_sequence_dataset_market_state.py` cutover

### Out of scope

- Full-campaign / 全市场
- Training / Phase4 / EXEC-002
- Blind merge develop
- A4 derived QA final closeout

## Suggested Deliverables (post-Init)

| ID | Deliverable |
|----|-------------|
| A3-D1 | Caps enforce path in fetch (reads approved 180/80000) |
| A3-D2 | Frequency-wall + resume strategy (manifest / pause / retry) |
| A3-D3 | Limited-live fill: 510300 + approved gap/staleness batch |
| A3-D4 | Soft80 progress or explicit accepted residual update |
| A3-D5 | Tests + Gate/Close (zero token in repo) |

## Init Defaults to Confirm (programmer)

| ID | Question | Recommended default |
|----|----------|---------------------|
| **A3_Q1** | Live fill priority? | **P1**: wire caps + freq-wall/resume **before** any live; then **510300 + pool-61 staleness**; soft80 expand as **P2** same WT if budget allows else residual |
| **A3_Q2** | Soft80 / pool version? | Keep **v1@1** until soft80 reselect lands; if reselect → **new registry version** (do not silently mutate 61) |
| **A3_Q3** | Hygiene residuals? | **Defer** dataset-old-tests / allowlist / toml / market_state to **A3-tail or A4** unless cheap; do not block live campaign |

> Init 时可用：`A3_Q1=P1_caps_then_510300_staleness` / `A3_Q2=keep_v1_until_reselect` / `A3_Q3=defer_hygiene`  
> **另需：** 首次 live 批次前显式 M1/normal 批准（token 仅 env）。

## Intake Verdict

```yaml
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
init_completed: true
init_completed_at: 2026-07-22T14:16:00+08:00
needs_programmer_init: false
auto_init: false
next_route: Dispatch R4-A3-T1 (or programmer 「开始 T1」)
stop_conditions:
  - no live until T1–T2 done + explicit batch approve
  - no full-campaign / 全市场
  - no training / Phase4 / EXEC-002
  - no blind full merge of develop
  - no token in repo
```
