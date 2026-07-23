---
title: "WT-R4-A4: derived 最小实现 + 质量审计报告收口（非训练）"
artifact_type: "worktrack-contract"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
status: "active"
node_type: "feature"
derived_from_milestone: true
created: "2026-07-23T17:47:00+08:00"
updated: "2026-07-23T20:45:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A4 derived 最小实现 + 质量审计报告收口

## Control Signal

- worktrack_id: WT-R4-A4
- milestone_id: MS-R4-001
- derived_from_milestone: true
- status: active
- implementation_status: t1_complete
- node_type: feature
- goal_summary: >
  在已批准 cache（池 v1@1 / 61 + 510300 qfq）上落地 derived 最小合同与可复现
  load；交付 CS4 质量审计报告；按 Init 默认关闭 AO-O1/O2 hygiene；不训、不
  full-campaign、不 Phase4/EXEC-002、不 blind-merge develop。
- execution_not_started: false
- selected_next_action_id: R4-A4-T2
- t1_status: completed
- t1_completed_at: 2026-07-23T20:45:00+08:00
- t1_notes: .servo/worktrack/WT-R4-A4-t1-notes.md
- t1_schema: .servo/worktrack/WT-R4-A4-derived-schema.md
- t1_result: >
  R4_DERIVED_* frozen (M1 ret+rsi; year parts); README + schema draft;
  unit+contract green (zero live; no parquet build)
- pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
- live_policy: zero_live (cache-only); any live requires explicit M1/normal batch
- upstream_a3:
  - .servo/worktrack/WT-R4-A3-closeout.md (pass_with_residuals)
  - soft80 accepted_residual; 510300 qfq-only; 601989 trial exclude; AO-O→A4
- upstream_a1_a2:
  - .servo/worktrack/WT-R4-A1-lake-source-contract.md (frozen)
  - make_r4_datalake + consumer cutover (A2)
- init_defaults_locked:
  - A4_Q1: M1_ret_rsi — Return 5d/10d/20d + RSI; ATR optional; defer MACD/Bollinger/market-state
  - A4_Q2: inputs_derived_year_parts — inputs/data/derived/{family}/{ts_code}/year=YYYY/part.parquet
  - A4_Q3: md_plus_json — WT-R4-A4-qa-report.md + optional workspace/r4_a4_qa/*.json
  - A4_Q4: O1_O2_in_AC — AO-O1+O2 in AC; O3 doc-only; O4 optional
  - A4_Q5: zero_live — cache-only derived build
  - A4_Q6: registry61_trial60 — QA reports registry 61 + trial 60 note
  - A4_Q7: wt_close_only — A4 Gate closes WT only; MS final acceptance / develop merge separate
- out_of_scope: full_campaign; training; Phase_4; EXEC-002; token-in-repo; blind_full_merge_develop; soft80_expansion
- plan_task_queue: .servo/worktrack/WT-R4-A4-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A4-intake-review.md

## Metadata

- 工作追踪编号: WT-R4-A4
- 分支: milestone/MS-R4-001-tushare-datalake
- 基准分支: develop
- 基准引用: 0aa6037796ea1c8ea70f29c6682a2a1be2227c42
- 约定状态: active
- 负责人: OceanEyeFF
- 更新时间: 2026-07-23T17:47:00+08:00
- milestone_id: MS-R4-001

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-R4-001-tushare-datalake@0aa6037
- worktrack_branch: milestone/MS-R4-001-tushare-datalake
- integration_target_ref: milestone/MS-R4-001-tushare-datalake
- closeout_target_ref: milestone/MS-R4-001-tushare-datalake
- final_baseline_branch: develop
- checkpoint_base_ref: 0aa6037796ea1c8ea70f29c6682a2a1be2227c42
- branch_action: use_existing_milestone_branch
- branch_action_reason: >
  one_development_branch_per_milestone；禁止为 A4 另开 feature 分支。
  Tip already has A0–A3 lake/cache/live path; do not blind-merge develop EXEC/Phase4 into R4.

## Milestone Binding

- milestone_id: MS-R4-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-R4-001.md
- decisions_locked: >
  D2=L2, D3=R1, D4=lake_qa_closeout, D5=tushare_primary, CG2=M1,
  pool=custom_research_liquidity_quality_v1@1,
  soft80=accepted_residual, index_510300=qfq_only, trial_exclude=601989,
  A4_Q1=M1_ret_rsi, A4_Q2=inputs_derived_year_parts, A4_Q3=md_plus_json,
  A4_Q4=O1_O2_in_AC, A4_Q5=zero_live, A4_Q6=registry61_trial60, A4_Q7=wt_close_only

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-R4-001-WT-R4-A4-intake-review.md
- repo_fundamentals: pass
- snapshot_freshness: pass_with_caveat
- milestone_purpose_alignment: pass
- historical_conflict_risk: medium
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
- prerequisite: WT-R4-A3 closed (pass_with_residuals)

## Node Type

- type: feature
- source_from_milestone: worktrack_list WT-R4-A4 node_type=feature
- baseline_form: commit-on-milestone-branch
- merge_required: yes（合入 develop 待 milestone close / programmer checkpoint；A4_Q7=wt_close_only）
- gate_criteria: >
  Derived 最小合同与 year 分区落地；cache-only 可复现 build/load（Return5/10/20 + RSI）；
  Arch-v1 测试绿；QA 报告交接（registry61 + trial60 + residuals）；AO-O1/O2 完成或显式豁免；
  无 token 入仓；无 full-campaign；无训/Phase4/EXEC-002；无 soft80 扩池；无 blind full merge develop
- if_interrupted_strategy: checkpoint-or-recover

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: feature WT；默认零 live；执行尚未开始，待 programmer 「开始 T1」

## 任务目标

### Control Signal

- 目标摘要: derived 最小实现 + QA 收口（CS3/CS4）；非训练。

### Supporting Detail

- 完整目标: >
  定义 `inputs/data/derived/` 布局与 schema；从 cache（refresh=False）构建
  Return5d/10d/20d + RSI（ATR 可选）；提供可复现 load；交付质量审计报告；
  收口 AO-O1 allowlist + AO-O2 dataset_builder 旧测；AO-O3 文档说明。

## 范围

### Control Signal

- 范围摘要: derived 合同/构建/load + QA 报告 + AO-O1/O2；相关测与 servo 文档。

### Supporting Detail

- 允许写入:
  - `src/ashare_infra/lake/**`、可选 `src/ashare_infra/data/**`（derived helpers）
  - `src/ashare_lab/features/**` 或 thin adapters（复用既有特征，禁止第二套真理）
  - `inputs/data/derived/**`（cache-only build；不写 token）
  - `tests/{unit,integration,contract}/**` 与 A4 相关（含 AO-O1/O2）
  - `inputs/configs/data_source.toml` 注释/文档对齐（AO-O3）
  - `.servo/worktrack/WT-R4-A4-*` / control-state / milestone progress（最小）
  - `workspace/r4_a4_qa/**`（可选 JSON 证据）
- 允许只读:
  - A1–A3 冻结合同、cache、closeout、residuals
  - `inputs/data/cache/tushare_*`（默认只读；零 live）
- 数据策略: **零 live**；token 仅 env；禁止 soft80 扩池 live

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不做 full-campaign、不训、不并 Phase4/EXEC-002、不 soft80 扩池、不 blind-merge develop、不在本 WT 做 milestone 终验。

### Supporting Detail

- 全市场 / silent full-campaign
- 训练 / 模型晋升 / X×Y×Z
- Phase 4 / EXEC-002
- Soft80 扩池或 registry 重选
- MACD / Bollinger / market-state 完整层（可 residual）
- MS-R4-001 final acceptance + develop merge（A4_Q7 另批）
- Token 入仓；blind full merge develop

## 验收标准（AC）

1. Derived layout + schema 可版本化（常量/合同/README 对齐 A4_Q2）
2. Cache-only 构建 Return5/10/20 + RSI 可复现；池绑定 v1@1
3. Load API + Arch-v1 unit/contract/integration 断言 schema/覆盖
4. QA 报告：`.servo/worktrack/WT-R4-A4-qa-report.md`（+ 可选 JSON）；含 soft80/510300/601989/AO-O 状态
5. AO-O1 + AO-O2 完成；AO-O3 文档；AO-O4 可选
6. 无 token / 无 full-campaign / 无训 / 无 Phase4/EXEC-002
7. Gate + Close 仅关 WT-R4-A4（里程碑终验另批）

## 计划引用

- plan_task_queue: .servo/worktrack/WT-R4-A4-plan-task-queue.md
- init_result: .servo/worktrack/WT-R4-A4-init-result.md
