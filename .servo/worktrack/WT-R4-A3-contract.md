---
title: "WT-R4-A3: Limited-live 增量补洞 + 频率墙/简历策略（normal）"
artifact_type: "worktrack-contract"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
status: "active"
node_type: "feature"
derived_from_milestone: true
created: "2026-07-22T14:16:00+08:00"
updated: "2026-07-23T14:34:00+08:00"
owner: "OceanEyeFF"
status: "closed"
---

# WT-R4-A3 Limited-live 增量补洞 + 频率墙/简历策略

## Control Signal

- worktrack_id: WT-R4-A3
- milestone_id: MS-R4-001
- derived_from_milestone: true
- status: closed
- implementation_status: closed
- gate_verdict: pass_with_residuals
- closed_at: 2026-07-23T14:34:00+08:00
- node_type: feature
- goal_summary: >
  将已批准 caps（180/80000）接到 fetch 限流；实现频率墙暂停/简历；
  在 M1/normal 显式批次批准下做 L2 limited-live 补洞（510300 + 池 61 陈旧优先；
  soft80 为 P2）；不训、不 full-campaign、不 blind-merge develop。
- execution_not_started: false
- selected_next_action_id: CLOSED
- t1_status: completed
- t1_completed_at: 2026-07-22T14:54:00+08:00
- t1_notes: .servo/worktrack/WT-R4-A3-t1-notes.md
- t1_result: tushare_rate_limit wired into fetch_*; unit+contract green (zero live)
- t2_status: completed
- t2_completed_at: 2026-07-22T17:45:00+08:00
- t2_notes: .servo/worktrack/WT-R4-A3-t2-notes.md
- t2_result: tushare_batch plan/dry-run/pause/resume; 19 passed (zero live)
- t3_status: completed_pass_with_residuals
- t3_completed_at: 2026-07-23T09:35:00+08:00
- t3_notes: .servo/worktrack/WT-R4-A3-t3-notes.md
- t3_addon: .servo/worktrack/WT-R4-A3-t3-addon.md
- t3_result: >
  live approve M1-normal-2026-07-23-510300+staleness7;
  510300 qfq via fund_daily (859 rows); staleness 6/7→2026-07-22;
  residuals: ETF basic/mf N/A; 601989 upstream exhausted
- t4_status: completed
- t4_completed_at: 2026-07-23T13:05:00+08:00
- t4_notes: .servo/worktrack/WT-R4-A3-t4-notes.md
- t4_result: >
  soft80 accepted_residual (zero live); pool v1@1/61 kept;
  trial exclude 601989; 510300 basic/mf accepted N/A; AO-O→A4
- t5_status: completed
- t5_completed_at: 2026-07-23T13:08:00+08:00
- t5_consistency: .servo/worktrack/WT-R4-A3-consistency-matrix.md
- t5_gate_evidence: .servo/worktrack/WT-R4-A3-gate-evidence.md
- t5_closeout: .servo/worktrack/WT-R4-A3-closeout.md
- proposed_gate_verdict: pass_with_residuals
- pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
- caps_config: inputs/configs/tushare_rate_limits.toml (180 / 80000) — **enforced in T1**
- live_policy: M1_normal — T3 live done; T4 zero live
- upstream_a2:
  - .servo/worktrack/WT-R4-A2-closeout.md (pass_with_residuals)
  - make_r4_datalake + consumer cutover already on tip
- upstream_a1:
  - .servo/worktrack/WT-R4-A1-lake-source-contract.md (frozen_for_A2)
  - .servo/worktrack/WT-R4-A1-cache-inventory.md (frozen_for_A2)
  - .servo/worktrack/WT-R4-A1-schema-draft.md (frozen_for_A2)
  - .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md (approved)
- init_defaults_locked:
  - A3_Q1: P1_caps_then_510300_staleness — caps+freq-wall/resume before live; then 510300 + pool-61 staleness; soft80 P2
  - A3_Q2: keep_v1_until_reselect — keep registry v1@1 until soft80 reselect; new version if reselect
  - A3_Q3: defer_hygiene — dataset old tests / allowlist / toml / market_state deferred (A3-tail or A4)
- live_policy: M1_normal — no live until explicit batch approve after T1–T2
- out_of_scope: full_campaign; training; Phase_4; EXEC-002; token-in-repo; blind_full_merge_develop
- plan_task_queue: .servo/worktrack/WT-R4-A3-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md

## Metadata

- 工作追踪编号: WT-R4-A3
- 分支: milestone/MS-R4-001-tushare-datalake
- 基准分支: develop
- 基准引用: 4474da9d86c21eaa219988b187302895647e7b06
- 约定状态: active
- 负责人: OceanEyeFF
- 更新时间: 2026-07-22T14:16:00+08:00
- milestone_id: MS-R4-001

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-R4-001-tushare-datalake@4474da9
- worktrack_branch: milestone/MS-R4-001-tushare-datalake
- integration_target_ref: milestone/MS-R4-001-tushare-datalake
- closeout_target_ref: milestone/MS-R4-001-tushare-datalake
- final_baseline_branch: develop
- checkpoint_base_ref: 4474da9
- branch_action: use_existing_milestone_branch
- branch_action_reason: >
  one_development_branch_per_milestone；禁止为 A3 另开 feature 分支。
  Tip already has A2 DataLake; do not blind-merge develop EXEC/Phase4 into R4.

## Milestone Binding

- milestone_id: MS-R4-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-R4-001.md
- decisions_locked: >
  D2=L2, D3=R1, D5=tushare_primary, CG2=M1,
  pool=custom_research_liquidity_quality_v1@1,
  A1_caps=180/80000_approved,
  A3_Q1=P1_caps_then_510300_staleness,
  A3_Q2=keep_v1_until_reselect,
  A3_Q3=defer_hygiene

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- repo_fundamentals: pass
- snapshot_freshness: pass_with_caveat
- milestone_purpose_alignment: pass
- historical_conflict_risk: medium_high
- worktrack_adjustment_recommendations: none
- add_remove_worktrack_recommendations: none
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 1
- latest_review_checkpoint: MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00
- effective_review_pass: true
- review_invalidated_by: none
- prerequisite: WT-R4-A2 closed (pass_with_residuals)

## Node Type

- type: feature
- source_from_milestone: worktrack_list WT-R4-A3 node_type=feature
- baseline_form: commit-on-milestone-branch
- merge_required: yes（合入 develop 待 milestone close / programmer checkpoint）
- gate_criteria: >
  Caps 在 fetch 路径可 enforce；频率墙/resume 策略可测（含 dry-run）；
  经批准的 L2 limited-live 补洞有证据（510300 优先；soft80 进度或显式残差）；
  无 token 入仓；无 full-campaign；无训/Phase4/EXEC-002；无 blind full merge develop
- if_interrupted_strategy: checkpoint-or-recover

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: feature WT；T1–T2 无 live；T3+ live 须显式批次批准

## 任务目标

### Control Signal

- 目标摘要: caps enforce + 频率墙/resume + L2 limited-live 补洞（M1/normal）。

### Supporting Detail

- 完整目标: >
  将 `r4_approved_rpm` / `r4_approved_daily_per_api` 接到 TuShare fetch 限流；
  按 A1 建议实现 concurrency=1、burst pause on freq wall、batch≤50、可简历 manifest；
  在显式批准下填充 `510300.SH` 与池内陈旧洞；soft80 扩池/重选为 P2（重选则新 registry 版本）；
  hygiene（dataset 旧测等）延后。

## 范围

### Control Signal

- 范围摘要: infra fetch 限流 + resume；批准后的 L2 cache 写入；相关测与 servo 文档。

### Supporting Detail

- 允许写入:
  - `src/ashare_infra/data/**`、`src/ashare_infra/lake/**`（caps/limiter/resume）
  - `inputs/data/cache/tushare_*`（仅经批准的 limited-live 批次）
  - 可选 `inputs/pools/research_liquidity_quality/`（仅 soft80 重选且新版本）
  - `tests/{unit,integration,contract}/**` 与 A3 相关
  - `.servo/worktrack/WT-R4-A3-*` / control-state / milestone progress（最小）
- 允许只读:
  - A1/A2 冻结合同、inventory、caps、closeout
  - 现有 cache（T1–T2 默认只读）
- 数据策略: T1–T2 **零 live**；T3+ live 仅 M1/normal 显式批次批准；token 仅 env

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不做 full-campaign、不训、不并 Phase4/EXEC-002、不 blind-merge develop。

### Supporting Detail

- 全市场 / silent full-campaign
- A4 derived QA 终稿（可交接残差）
- 训练 / 模型晋升
- Phase 4 lab 去重
- EXEC-002 / ashare_exec
- Blind `git merge develop`
- 静默改写 pool v1@1（重选必须新版本）
- commit/push（除非 programmer 另批）
- 最终 milestone 验收

## 受影响模块

### Control Signal

- 关键影响模块: `ashare_infra.data.tushare_source` / lake；cache；可选 pools；`tests/**`；`.servo/worktrack/WT-R4-A3-*`

## 计划中的下一状态

- 当前: T2 完成 → **R4-A3-T3**（limited-live；须显式批次批准）
- T3 前: 须 programmer 显式 live 批次批准

## 验收标准

- [x] Caps 在运行时限流路径可读并 enforce（非仅 toml） — T1
- [x] 频率墙 / resume 策略有实现与可测证据（dry-run 优先） — T2
- [x] 经批准的 limited-live 对 `510300.SH`（及批准的 staleness）有补洞证据，或显式豁免 — T3
- [x] Soft80：有进度（扩池/重选）或显式 accepted residual 更新 — T4 (`accepted_residual`)
- [x] 无 token 入仓；无 full-campaign；无训/Phase4/EXEC-002
- [x] T5 一致性矩阵 + Gate/Close 包 — proposed Gate `pass_with_residuals`

## 约束

- L2 + M1/normal；live 批次须显式批准
- Caps: rpm=180 / daily_per_api=80000
- 绑定 `custom_research_liquidity_quality_v1@1` 直至重选
- one milestone development branch
- concurrency=1；burst_pause_on_freq_wall=true；batch≤50（A1）
- Hygiene deferred per A3_Q3

## 回滚条件

- 未经批准的 live / full-campaign → 停止并 recover
- 频率墙无 resume 却持续打爆配额 → 停止并 redesign
- 范围漂移到 EXEC / Phase4 / training → 停止并 re-bound

## Linked Artifacts

- plan_task_queue: .servo/worktrack/WT-R4-A3-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A3-intake-review.md
- upstream_a2_closeout: .servo/worktrack/WT-R4-A2-closeout.md
- upstream_a1_caps: .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md
- upstream_a1_inventory: .servo/worktrack/WT-R4-A1-cache-inventory.md
- caps_config: inputs/configs/tushare_rate_limits.toml
- milestone: .servo/milestone/MS-R4-001.md
