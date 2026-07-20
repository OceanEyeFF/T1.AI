---
title: "MS-R4-001 / WT-R4-A1 Intake Review"
artifact_type: "worktrack-intake-review"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
updated: "2026-07-20T19:16:00+08:00"
owner: "OceanEyeFF"
updated_by: "cursor-intake-WT-R4-A1-after-A0-close"
---

# MS-R4-001 / WT-R4-A1 Intake Review

## Control Signal

```yaml
selected_worktrack_id: WT-R4-A1
selected_worktrack_title: 湖/源合同 + cache inventory + schema + 日/RPM 上限建议（供批准）
target_milestone_id: MS-R4-001
derived_from_milestone: true
active_milestone_ref: .servo/milestone/MS-R4-001.md
active_milestone_branch: milestone/MS-R4-001-tushare-datalake
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
blocker: none
prerequisite_closed: WT-R4-A0 (pass_with_accepted_residuals)
decisions_locked_from_milestone:
  - D2=L2_limited_live
  - D3=R1_audit_reuse
  - D5=tushare_primary_akshare_backup
  - CG2=M1_normal
  - pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
deferred_to_A1_then_approve:
  - daily_call_cap_numeric
  - rpm_cap_numeric
  - lake_source_contract_freeze
  - cache_layout_inventory_formal
  - schema_field_contract_draft
out_of_scope_explicit:
  - lake_fill / limited-live campaign (A3)
  - training / model promotion
  - Phase_4_lab_dedup
  - EXEC-002 / ashare_exec knife follow-ons
milestone_review_gate_ready: true
continuation_required: false
next_route: Await programmer Init WT-R4-A1 (docs node); do not auto-Init
contract_ref: pending_init
```

## Request Summary

```yaml
request_summary: >
  After WT-R4-A0 Close, open A1 intake only: draft lake/source contract,
  inventory existing TuShare cache vs approved pool, propose schema fields,
  and recommend daily/RPM caps for programmer approval. No lake fill, no
  training, no Phase 4, no EXEC-002.
```

## Repo Fundamentals

```yaml
repo_fundamentals: pass
active_milestone: MS-R4-001
milestone_status: active
baseline_branch: develop
milestone_branch: milestone/MS-R4-001-tushare-datalake
develop_tip: 7453daa
a0_implementation_commit: 3807f81
goal_alignment: >
  A1 freezes the reproducible lake/source contract and rate-limit policy
  that A2–A4 will implement against the A0 approved pool — not a fill campaign.
prohibited_actions:
  - TuShare lake fill / silent full-campaign / unapproved limited-live
  - Training matrix / model retrain / alpha_score promotion
  - Phase 4 lab dedup merge
  - EXEC-002 or ashare_exec scope expansion
  - Overwriting low_manipulation as final universe
  - Writing TUSHARE_TOKEN into repo/artifacts
  - commit/push without programmer approval
```

## Snapshot Freshness

```yaml
snapshot_freshness: pass_with_caveat
evidence_refs:
  - .servo/worktrack/WT-R4-A0-closeout.md
  - .servo/worktrack/WT-R4-A0-gate-evidence.md
  - .servo/worktrack/WT-R4-A0-data-gaps.md
  - inputs/pools/research_liquidity_quality/config.toml
caveat: >
  A0 Close writeback is in working tree pending commit/push approval.
  Milestone tip lags develop (Infra/EXEC already on develop); A1 Init should
  use milestone branch policy and avoid pulling EXEC/Phase4 into R4 scope.
refresh_required_after: approved_close_writeback_commit
```

## Historical Conflict Risk

```yaml
historical_conflict_risk: medium
notes:
  - soft_target_80 unmet → A1 must not pretend universe is complete; inventory gap → A3
  - 510300.SH empty → schema/inventory must list index/ETF as deferred fill
  - ashare_infra DataLake already on develop — A1 contract should reference
    DataLake as sole entry (Phase 2) without re-opening EXEC package work
  - do not conflate ashare_exec (Phase 3) with R4 lake contract
```

## Proposed A1 Scope (for Init)

### In scope (docs / contract only)

1. **湖/源合同草案**
   - Primary: TuShare daily (qfq / daily_basic / moneyflow) from `2023-01-01`
   - Backup: AkShare semantics (no delete)
   - Consumer entry: `ashare_infra.lake.DataLake` (no direct `load_or_fetch_*` in new lab code)
   - Universe binding: `custom_research_liquidity_quality_v1` @ `1` (61 symbols)
2. **Cache inventory**
   - Reuse A0 T3 inventory as baseline (`tushare_qfq/basic/moneyflow` ~65; pool∩cache)
   - Explicit gaps: soft_target deficit; `510300.SH` empty; symbols outside cache
3. **Schema 草案**
   - Partition/layout expectations under `inputs/data/cache/`
   - Required columns for qfq / daily_basic / moneyflow (draft for A2 tests)
4. **日/RPM 上限建议（供批准）**
   - Policy locked: L2 limited-live + M1/normal
   - A1 delivers **recommended numeric caps** only; no live calls in A1

### Out of scope

- Any network lake fill / A3 campaign
- A2 implementation of loaders/tests beyond referencing contracts
- Training / EXEC-002 / Phase 4

## Suggested Deliverables (post-Init)

| ID | Deliverable |
|----|-------------|
| A1-D1 | `.servo/worktrack/WT-R4-A1-lake-source-contract.md` |
| A1-D2 | `.servo/worktrack/WT-R4-A1-cache-inventory.md` |
| A1-D3 | `.servo/worktrack/WT-R4-A1-schema-draft.md` |
| A1-D4 | `.servo/worktrack/WT-R4-A1-rate-limit-recommendations.md` (daily + RPM) |

## Suggested Init Questions (if programmer wants to lock before Init)

```yaml
A1_Q1_rate_limit_stance: >
  Prefer conservative starter caps for L2 (e.g. draft band to confirm at Init):
  daily_calls≈200–500; rpm≈40–80 — final numbers require programmer approve.
A1_Q2_index_anchor: >
  Keep 510300.SH as deferred inventory gap (no fill in A1) — confirm Y/N.
A1_Q3_datalake_binding: >
  Contract names DataLake as sole consumer entry — confirm Y (recommended).
```

## Intake Verdict

```yaml
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
needs_programmer_init: true
auto_init: false
next_programmer_actions:
  - Approve commit/push of A0 Close writeback on milestone branch (separate)
  - Optionally answer A1_Q1–Q3 then 「Init WT-R4-A1」
stop_conditions:
  - no lake fill
  - no training
  - no Phase 4 / EXEC-002
```
