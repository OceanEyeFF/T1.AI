---
title: "MS-R4-001 / WT-R4-A2 Intake Review"
artifact_type: "worktrack-intake-review"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
updated: "2026-07-20T21:30:00+08:00"
owner: "OceanEyeFF"
updated_by: "cursor-init-worktrack-WT-R4-A2"
---

# MS-R4-001 / WT-R4-A2 Intake Review

## Control Signal

```yaml
selected_worktrack_id: WT-R4-A2
selected_worktrack_title: Cache-first 加载路径与 contract/integration 测试（Arch-v1）
target_milestone_id: MS-R4-001
derived_from_milestone: true
active_milestone_ref: .servo/milestone/MS-R4-001.md
active_milestone_branch: milestone/MS-R4-001-tushare-datalake
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
blocker: none
prerequisite_closed: WT-R4-A1 (pass)
upstream_frozen:
  - WT-R4-A1-lake-source-contract.md (frozen_for_A2)
  - WT-R4-A1-cache-inventory.md (frozen_for_A2)
  - WT-R4-A1-schema-draft.md (frozen_for_A2)
  - WT-R4-A1-rate-limit-recommendations.md (approved 180/80000)
decisions_locked_from_milestone:
  - D2=L2_limited_live
  - D3=R1_audit_reuse
  - D5=tushare_primary_akshare_backup
  - CG2=M1_normal
  - pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
  - A1_caps: rpm=180 daily_per_api=80000 (approved; promote to config optional in A2)
out_of_scope_explicit:
  - lake_fill / limited-live campaign (A3)
  - training / model promotion
  - Phase_4 / EXEC-002
  - silent live / token-in-repo
  - blind_full_merge_of_develop
milestone_review_gate_ready: true
latest_review_status: effective_pass
milestone_review_count: 1
latest_review_checkpoint: MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00
effective_review_pass: true
review_invalidated_by: none
continuation_required: false
next_route: Init completed; Dispatch R4-A2-T1 on request
init_completed_at: 2026-07-20T21:30:00+08:00
contract_ref: .servo/worktrack/WT-R4-A2-contract.md
plan_task_queue_ref: .servo/worktrack/WT-R4-A2-plan-task-queue.md
init_defaults_applied:
  A2_Q1: Y_scoped_ashare_infra_bringup_not_full_develop_merge
  A2_Q2: Y_caps_promote_optional_in_T4_else_defer_A3
  A2_Q3: Y_basic_moneyflow_via_adapter_or_thin_lake_helpers_ok
```

## Request Summary

```yaml
request_summary: >
  WT-R4-A2 已 Init（test）。contract + plan queue 已播种；
  selected_next_action=R4-A2-T1（scoped ashare_infra land on milestone）。
  执行尚未开始。tip 无 DataLake；须 path-limited bring-up，禁止 blind merge develop。
```

## Repo Fundamentals

```yaml
repo_fundamentals: pass
active_milestone: MS-R4-001
milestone_status: active
baseline_branch: develop
milestone_branch: milestone/MS-R4-001-tushare-datalake
develop_tip: 7453daa
a1_close_commit: 16ef565
milestone_tip_at_init: adede39
goal_alignment: >
  A2 lands cache-first DataLake path + Arch-v1 contract/integration tests
  against A1 frozen lake/source, inventory, schema, and approved caps.
prohibited_actions:
  - TuShare lake fill / silent full-campaign / unapproved limited-live
  - Training matrix / model retrain / alpha_score promotion
  - Phase 4 lab dedup merge
  - EXEC-002 or ashare_exec scope expansion
  - Blind full merge of develop into milestone
  - Writing TUSHARE_TOKEN into repo/artifacts
  - commit/push without programmer approval
```

## Snapshot Freshness

```yaml
snapshot_freshness: pass_with_caveat
evidence_refs:
  - .servo/worktrack/WT-R4-A1-closeout.md
  - .servo/worktrack/WT-R4-A1-gate-evidence.md
  - .servo/worktrack/WT-R4-A1-lake-source-contract.md
  - .servo/worktrack/WT-R4-A1-schema-draft.md
  - .servo/worktrack/WT-R4-A1-cache-inventory.md
caveat: >
  Milestone tip lags develop: ashare_infra/DataLake exists on develop only.
  A2 Init locks scoped infra bring-up (not full merge; not tests-only against missing APIs).
  Must not pull ashare_exec / Phase4 into R4 scope.
refresh_required_after: optional after T1 land if conflicts
```

## Milestone Purpose Alignment

```yaml
milestone_purpose_alignment: pass
note: >
  CS2/CS3 require TuShare default path + tests and reproducible cache load
  for the approved pool — exactly A2's test-node charter.
```

## Historical Conflict Risk

```yaml
historical_conflict_risk: medium
notes:
  - tip has empty ashare_infra shells; develop has full package — scoped land required
  - soft_target_80 / 510300 remain inventory residuals → do not fail A2; assert gaps
  - do not conflate ashare_exec (Phase 3) with R4 lake contract tests
  - lab consumers may still call load_or_fetch_* on tip — R4 surfaces must move to DataLake
worktrack_adjustment_recommendations: none
add_remove_worktrack_recommendations: none
```

## Proposed A2 Scope (for Init)

### In scope

1. **Scoped `ashare_infra` bring-up** on milestone (lake + data adapters + needed deps/tests)
2. **Cache-first DataLake path** bound to A1 contract (tushare primary, qfq, pool v1)
3. **Disk/schema contract tests** vs A1 inventory + schema (pool 61; 510300 unavailable)
4. **API/integration tests** (no live): cache-hit, as_of, no-direct-load_or_fetch for R4 surfaces
5. **Optional** caps promote `180/80000` → `inputs/configs` (T4; else defer A3)

### Out of scope

- Lake fill / L2 live campaign (A3)
- Training / EXEC-002 / Phase 4
- Blind full merge of develop

## Suggested Deliverables (post-Init)

| ID | Deliverable |
|----|-------------|
| A2-D1 | Scoped `ashare_infra` on milestone (importable DataLake) |
| A2-D2 | Cache-first load path wired to A1 contract |
| A2-D3 | Contract tests: layout/columns/pool binding / index gap |
| A2-D4 | Integration tests: cache-hit / as_of / no-direct fetch (no live) |
| A2-D5 | Gate evidence + closeout (optional caps config) |

## Intake Verdict

```yaml
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
init_completed: true
init_completed_at: 2026-07-20T21:30:00+08:00
needs_programmer_init: false
auto_init: false
next_route: Dispatch R4-A2-T1 (or programmer 「开始 T1」)
stop_conditions:
  - no lake fill
  - no training
  - no Phase 4 / EXEC-002
  - no blind full merge of develop
```
