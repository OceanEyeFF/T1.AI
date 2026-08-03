---
title: "MS-R4-001 / WT-R4-A4 Intake Review"
artifact_type: "worktrack-intake-review"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-23T17:47:00+08:00"
owner: "OceanEyeFF"
updated_by: "cursor-init-worktrack-WT-R4-A4"
---

# MS-R4-001 / WT-R4-A4 Intake Review

## Control Signal

```yaml
selected_worktrack_id: WT-R4-A4
selected_worktrack_title: derived 最小实现 + 质量审计报告收口（非训练）
target_milestone_id: MS-R4-001
derived_from_milestone: true
active_milestone_ref: .servo/milestone/MS-R4-001.md
active_milestone_branch: milestone/MS-R4-001-tushare-datalake
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
needs_programmer_init: false
auto_init: false
blocker: none
prerequisite_closed: WT-R4-A3 (pass_with_residuals @ 8d60f09 / tip 0aa6037)
init_completed: true
init_completed_at: 2026-07-23T17:47:00+08:00
contract_ref: .servo/worktrack/WT-R4-A4-contract.md
plan_task_queue_ref: .servo/worktrack/WT-R4-A4-plan-task-queue.md
init_result_ref: .servo/worktrack/WT-R4-A4-init-result.md
init_defaults_applied:
  A4_Q1: M1_ret_rsi
  A4_Q2: inputs_derived_year_parts
  A4_Q3: md_plus_json
  A4_Q4: O1_O2_in_AC
  A4_Q5: zero_live
  A4_Q6: registry61_trial60
  A4_Q7: wt_close_only
upstream_ready:
  - make_r4_datalake (tushare/qfq/refresh=False) + consumer cutover (A2)
  - caps enforce 180/80000 + tushare_batch pause/resume (A3 T1–T2)
  - pool∩cache 61/61 + 510300.SH qfq filled (A3 T3)
  - soft80 accepted_residual; 601989 trial exclude; index qfq-only (A3 T4)
  - Arch-v1 tests/{unit,integration,contract}; no token in repo
decisions_locked_from_milestone:
  - D2=L2_limited_live
  - D3=R1_audit_reuse
  - D4=lake_qa_closeout
  - D5=tushare_primary_akshare_backup
  - CG2=M1_normal
  - pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
  - A1_caps: rpm=180 daily_per_api=80000
  - soft80: accepted_residual (61 < 80; hard_cap 100 met)
  - index_510300: qfq required; basic/mf N/A accepted
  - trial_exclude: 601989 (registry kept)
out_of_scope_explicit:
  - full-campaign / 全市场 silent pull
  - training / model promotion / X×Y×Z matrix
  - Phase_4 / EXEC-002
  - blind_full_merge_of_develop
  - writing TUSHARE_TOKEN into repo
  - soft80 expansion / pool reselect (already accepted residual)
milestone_review_gate_ready: true
latest_review_status: effective_pass
milestone_review_count: 1
latest_review_checkpoint: MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00
effective_review_pass: true
review_invalidated_by: none
continuation_required: false
next_route: Init completed; Dispatch R4-A4-T1 on request（零 live）
```

## Request Summary

```yaml
request_summary: >
  WT-R4-A4 已 Init（feature）。contract + plan queue 已播种；
  selected_next_action=R4-A4-T1（derived layout/schema；零 live）。
  A4_Q1–Q7 按 intake 建议默认锁定。执行尚未开始。
```

## Repo Fundamentals

```yaml
repo_fundamentals: pass
active_milestone: MS-R4-001
milestone_status: active
baseline_branch: develop
develop_tip: 7453daa
milestone_branch: milestone/MS-R4-001-tushare-datalake
milestone_tip: 0aa6037
a3_gate: pass_with_residuals
a3_close: 8d60f09
a3_control_pin: 0aa6037
goal_alignment: >
  A4 is the final planned WT of MS-R4-001: land minimal derived contract
  on approved cache, ship QA report handoff (CS3/CS4), optionally close
  AO-O hygiene — without training, full-campaign, Phase4, or EXEC-002.
prohibited_actions:
  - Silent full-campaign / 全市场 TuShare pull
  - Live without explicit M1/normal batch approve (default A4 = zero live)
  - Training / Phase4 / EXEC-002
  - Blind full merge of develop
  - Token-in-repo
  - commit/push without approval
  - Soft80 live expansion (accepted residual; not reopened)
```

## Snapshot Freshness

```yaml
snapshot_freshness: pass_with_caveat
evidence_refs:
  - .servo/worktrack/WT-R4-A3-closeout.md
  - .servo/worktrack/WT-R4-A3-gate-evidence.md
  - .servo/worktrack/WT-R4-A3-consistency-matrix.md
  - .servo/worktrack/WT-R4-A3-t4-notes.md
  - .servo/worktrack/WT-R4-A1-lake-source-contract.md
  - .servo/worktrack/WT-R4-A1-schema-draft.md
  - inputs/data/derived/README.md
  - src/ashare_infra/lake/r4_contract.py
  - workspace/r4_a3_t3/live-verify-report.json
caveat: >
  Cache layer is Gate-ready for pool 61 + 510300 qfq. derived/ is directory
  + README only (no parquet / no DataLake derived API). control-state
  observed_checkout may lag tip 0aa6037 until refresh. develop still carries
  EXEC/Phase4 lag — do not blind-merge.
refresh_required_after: optional after A4 Init if tip moves
```

## Milestone Purpose Alignment

```yaml
milestone_purpose_alignment: pass
note: >
  CS3 (derived load) + CS4 (QA report) + D4=lake_qa_closeout map directly
  to A4 charter. A0–A3 close CS1/CS2/CS5/CS6 and cache half of CS3.
  Completing A4 should put MS-R4-001 at 5/5 worktracks (milestone Gate
  remains a separate programmer acceptance).
```

## Historical Conflict Risk

```yaml
historical_conflict_risk: medium
notes:
  - derived README vs DatasetBuilder path mismatch (inputs/data/derived vs workspace/datasets)
  - ashare_lab.features already has momentum/tech indicators — risk of dual write paths
  - AO-O2 dataset_builder tests (~10 fail) can expand scope if treated as hard AC
  - A4 is final WT — pressure to also close milestone / merge develop must stay approval-gated
  - zero-live default protects quota; any live reopen needs explicit M1/normal
worktrack_adjustment_recommendations: none
add_remove_worktrack_recommendations: none
```

## Inherited Residuals (from A3 → A4)

| ID | Residual | A4 expectation |
|----|----------|----------------|
| R-soft80 | 61 < soft_target 80 | **document only** in QA; do not reopen expansion |
| R-510300-mf | ETF basic/moneyflow N/A | **document only**; index qfq-only |
| R-601989 | upstream exhausted; trial exclude | reflect in QA scope (trial 60 vs registry 61) |
| R-AO-O1 | no-direct allowlist too wide | Init choose: in AC or defer |
| R-AO-O2 | dataset_builder integration ~10 fail | Init choose: fix in AC or defer |
| R-AO-O3 | data_source.toml dual-track | doc comment preferred |
| R-AO-O4 | AST contract reinforcement | optional / low |
| R-A2-carry | market_state deferred; backtest hard-cut | docs track unless Init pulls in |

## Proposed A4 Scope (for Init)

### In scope (core)

1. **Derived minimal contract**: define layout under `inputs/data/derived/` (or Init-chosen root), feature column set, partition scheme, pool binding (`v1@1`), reproducible build from cache-only (`refresh=False`)
2. **Minimal feature implementation**: momentum and/or volatility and/or technical subset (Init names columns); prefer reuse of `ashare_lab.features` where safe — **no second truth** for same metrics
3. **Load path**: DataLake or factory helper to load derived for approved pool; Arch-v1 unit/contract/integration tests asserting schema + reproducibility
4. **Quality audit report**: CS4 handoff artifact covering cache completeness, derived coverage, qfq consistency notes, partition layout, pool binding, and explicit gap/defer records (soft80 / 510300 / 601989 / AO-O status)
5. **Gate/Close packet** for WT-R4-A4; milestone final acceptance remains separate unless programmer expands scope at Init

### In scope (optional hygiene — Init choose)

6. AO-O1: tighten `test_no_direct_load_or_fetch` allowlist
7. AO-O2: fix `tests/integration/dataset/test_dataset_builder.py`
8. AO-O3: clarify `data_source.toml` vs `make_r4_datalake` (doc)
9. AO-O4: AST contract reinforcement (low priority)
10. Document A2-carry (market_state / backtest hard-cut) as deferred post-milestone if not pulled in

### Out of scope

- Full-campaign / 全市场
- Training / model promotion / Phase4 / EXEC-002
- Soft80 pool expansion / registry reselect
- Blind merge develop
- Minute-level / stk_mins lake
- Deleting AkShare
- Unapproved live TuShare pull

## Suggested Deliverables (post-Init)

| ID | Deliverable |
|----|-------------|
| A4-D1 | Derived layout + schema contract (frozen constants / docs) |
| A4-D2 | Minimal derived builder (cache → derived; zero live default) |
| A4-D3 | Reproducible load API + Arch-v1 tests |
| A4-D4 | Quality audit report (CS4) with residual table |
| A4-D5 | Hygiene pack (AO-O*) per Init defaults — or explicit defer in QA |
| A4-D6 | Gate/Close for WT-R4-A4 |

## Init Defaults to Confirm (programmer)

| ID | Question | Recommended default |
|----|----------|---------------------|
| **A4_Q1** | Derived minimal feature set? | **M1**: Return 5d/10d/20d + RSI (+ ATR optional); defer MACD/Bollinger/market-state to post-R4 or residual |
| **A4_Q2** | Derived storage root + layout? | **`inputs/data/derived/`** partitioned like cache (`{feature_family}/{ts_code}/year=YYYY/part.parquet`); bind pool v1@1; update README |
| **A4_Q3** | QA report format / path? | **Markdown** `.servo/worktrack/WT-R4-A4-qa-report.md` + optional JSON evidence under `workspace/r4_a4_qa/` |
| **A4_Q4** | AO-O hygiene in AC? | **P1**: include **AO-O1 + AO-O2** in A4 AC; **AO-O3** doc-only; **AO-O4** optional |
| **A4_Q5** | Live policy? | **Zero live** (cache-only derived build). Any live = explicit M1/normal batch |
| **A4_Q6** | Trial vs registry in QA? | Report **registry 61** + note **trial 60** (exclude 601989); soft80 accepted |
| **A4_Q7** | Milestone close with A4? | **WT close only** at A4 Gate; **MS-R4-001 final acceptance + develop merge** = separate programmer approve after A4 Close |

> Init 时可用一行确认：  
> `A4_Q1=M1_ret_rsi` / `A4_Q2=inputs_derived_year_parts` / `A4_Q3=md_plus_json` / `A4_Q4=O1_O2_in_AC` / `A4_Q5=zero_live` / `A4_Q6=registry61_trial60` / `A4_Q7=wt_close_only`

## Intake Verdict

```yaml
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
init_completed: true
init_completed_at: 2026-07-23T17:47:00+08:00
needs_programmer_init: false
auto_init: false
next_route: Dispatch R4-A4-T1 (or programmer 「开始 T1」)
stop_conditions:
  - no live until explicit M1/normal batch approve (default zero live)
  - no full-campaign / 全市场
  - no training / Phase4 / EXEC-002
  - no soft80 expansion campaign
  - no blind full merge of develop
  - no token in repo
  - no milestone final acceptance without separate approve
```
