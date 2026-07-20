---
title: "WT-R4-A1: 湖/源合同 + cache inventory + schema + 日/RPM 上限建议"
artifact_type: "worktrack-contract"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
status: "closed"
node_type: "docs"
derived_from_milestone: true
created: "2026-07-20T19:43:00+08:00"
updated: "2026-07-20T21:22:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A1 湖/源合同 + inventory + schema + 日/RPM 建议

## Control Signal

- worktrack_id: WT-R4-A1
- milestone_id: MS-R4-001
- derived_from_milestone: true
- status: closed
- implementation_status: closed
- gate_verdict: pass
- closed_at: 2026-07-20T21:22:00+08:00
- node_type: docs
- goal_summary: >
  冻结可复现湖/源合同、相对 A0 批准池的 cache inventory、schema 字段草案，
  以及 L2 limited-live 的日调用/RPM 数值 caps（已批准）；本 WT 不灌湖、不训。
- execution_not_started: false
- selected_next_action_id: none
- t5_status: completed
- t5_completed_at: 2026-07-20T21:08:00+08:00
- closeout_ref: .servo/worktrack/WT-R4-A1-closeout.md
- gate_evidence_ref: .servo/worktrack/WT-R4-A1-gate-evidence.md
- consistency_ref: .servo/worktrack/WT-R4-A1-consistency-matrix.md
- next_worktrack: WT-R4-A2 intake
- a2_intake_ref: .servo/worktrack/MS-R4-001-WT-R4-A2-intake-review.md
- t1_status: completed
- t1_deliverable: .servo/worktrack/WT-R4-A1-lake-source-contract.md
- t1_completed_at: 2026-07-20T20:25:00+08:00
- t2_status: completed
- t2_deliverable: .servo/worktrack/WT-R4-A1-cache-inventory.md
- t2_completed_at: 2026-07-20T20:34:00+08:00
- t3_status: completed
- t3_deliverable: .servo/worktrack/WT-R4-A1-schema-draft.md
- t3_completed_at: 2026-07-20T20:37:00+08:00
- t4_status: completed
- t4_deliverable: .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md
- t4_completed_at: 2026-07-20T20:39:00+08:00
- t4_suggested_caps: daily_per_api=80000; rpm=180; status=**approved**; approval=accept_recommended; approved_at=2026-07-20T20:52:00+08:00; account_points=2000; supersedes_v0_300_50
- pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
- init_defaults_locked:
  - A1_Q1: account=2000pts → **approved** rpm=180 daily/api=80000 (accept_recommended)
  - A1_Q2: Y — 510300.SH remains deferred inventory gap (no fill in A1)
  - A1_Q3: Y — DataLake is sole consumer entry in contract text
- out_of_scope: lake_fill; training; Phase_4; EXEC-002; silent live; token-in-repo
- plan_task_queue: .servo/worktrack/WT-R4-A1-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A1-intake-review.md

## Metadata

- 工作追踪编号: WT-R4-A1
- 分支: milestone/MS-R4-001-tushare-datalake
- 基准分支: develop
- 基准引用: 5cb94b40c89f4ee30a332aeb65ab60068453288d
- 约定状态: closed
- 负责人: OceanEyeFF
- 更新时间: 2026-07-20T21:22:00+08:00
- milestone_id: MS-R4-001
- gate_verdict: pass

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-R4-001-tushare-datalake@5cb94b40c89f4ee30a332aeb65ab60068453288d
- worktrack_branch: milestone/MS-R4-001-tushare-datalake
- integration_target_ref: milestone/MS-R4-001-tushare-datalake
- closeout_target_ref: milestone/MS-R4-001-tushare-datalake
- final_baseline_branch: develop
- checkpoint_base_ref: 5cb94b40c89f4ee30a332aeb65ab60068453288d
- branch_action: use_existing_milestone_branch
- branch_action_reason: >
  one_development_branch_per_milestone；禁止为 A1 另开 feature 分支。
  Milestone tip may lag develop (Infra/EXEC); A1 docs must not pull EXEC/Phase4 into R4 scope.

## Milestone Binding

- milestone_id: MS-R4-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-R4-001.md
- decisions_locked: >
  D2=L2, D3=R1, D5=tushare_primary, CG2=M1,
  pool=custom_research_liquidity_quality_v1@1,
  A1_Q1=accept_recommended_180_80000, A1_Q2=Y_510300_deferred, A1_Q3=Y_DataLake_sole_entry

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-R4-001-WT-R4-A1-intake-review.md
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
- prerequisite: WT-R4-A0 closed (pass_with_accepted_residuals)

## Node Type

- type: docs
- source_from_milestone: worktrack_list WT-R4-A1 node_type=docs
- baseline_form: commit-on-milestone-branch
- merge_required: yes（合入 develop 待 milestone close / programmer checkpoint）
- gate_criteria: >
  四份交付物齐备：湖/源合同、cache inventory、schema 草案、日/RPM caps（approved 180/80000）；
  T5 一致性矩阵通过；无 live 调用；无 token 入仓；明确不灌湖/不训/不并 Phase4/EXEC-002
- if_interrupted_strategy: checkpoint-or-recover

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: docs WT；紧贴 A0 gaps + DataLake 约定；低并行价值

## 任务目标

### Control Signal

- 目标摘要: 产出可批准的湖/源合同 + inventory + schema + 日/RPM 建议（文档/合同层）。

### Supporting Detail

- 完整目标: >
  基于 A0 批准池与 T3 cache gaps，起草 TuShare-primary / AkShare-backup 源合同；
  盘点 cache∩pool；定义 qfq/daily_basic/moneyflow（及 index 缺口）schema 草案；
  给出 L2 日调用与 RPM 建议区间供批准。A2 起才落地加载路径与合同测。

## 范围

### Control Signal

- 范围摘要: 仅 `.servo/worktrack/WT-R4-A1-*.md` 与必要的控制面/指针更新；只读 cache/pool。

### Supporting Detail

- 允许写入:
  - `.servo/worktrack/WT-R4-A1-lake-source-contract.md`
  - `.servo/worktrack/WT-R4-A1-cache-inventory.md`
  - `.servo/worktrack/WT-R4-A1-schema-draft.md`
  - `.servo/worktrack/WT-R4-A1-rate-limit-recommendations.md`
  - `.servo/worktrack/WT-R4-A1-consistency-matrix.md`
  - `.servo/worktrack/WT-R4-A1-closeout.md`
  - `.servo/worktrack/WT-R4-A1-gate-evidence.md`
  - 本 contract / plan queue / control-state / milestone progress（最小）
- 允许只读:
  - `inputs/pools/research_liquidity_quality/`
  - `inputs/data/cache/tushare_*`（inventory；不写 cache）
  - A0 gaps/brief、`ashare_infra.lake` 文档约定
- 数据策略: **只读 inventory**；禁止 live；禁止写 cache/derived

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不灌湖、不 limited-live、不训、不改加载实现主体、不并 Phase4/EXEC-002。

### Supporting Detail

- A3 limited-live 补洞战役
- A2 loader/contract 测试实现主体（可引用草案，不在 A1 写生产代码）
- A4 derived QA 终稿
- 训练 / 模型晋升
- Phase 4 lab 去重
- EXEC-002 / ashare_exec 扩展
- commit/push（除非 programmer 另批）
- 最终 milestone 验收

## 受影响模块

### Control Signal

- 关键影响模块: `.servo/worktrack/WT-R4-A1-*`；只读 pool/cache/infra 约定

## 计划中的下一状态

- 本 WT: **closed** (Gate pass)
- 下一: WT-R4-A2 intake → Init on request

## 验收标准

- [x] 存在湖/源合同草案（TuShare primary、AkShare backup、DataLake 入口、池绑定、自 2023-01-01）
- [x] 存在 cache inventory（相对 A0 池；显式 gaps：soft80、510300、pool∖cache）
- [x] 存在 schema 草案（布局 + 关键列；供 A2 测引用）
- [x] 存在日/RPM 建议（**approved** `accept_recommended`：180 rpm / 80000 per API·日；2000 积分档）
- [x] 无 live / 无 token 入仓 / 无灌湖写盘
- [x] 文档明确 out-of-scope：Phase4 / EXEC-002 / training
- [x] T5 一致性矩阵通过（`.servo/worktrack/WT-R4-A1-consistency-matrix.md`）

## 约束

- L2 + M1/normal；A1 零网络拉数
- 绑定 `custom_research_liquidity_quality_v1@1`，不以 low_manipulation 为最终 universe
- one milestone development branch
- 数值 caps 在 A1 已 **approved**（180 / 80000）；A3 live 须仍经显式战役批准，但不再卡「数值未批」

## 回滚条件

- 出现 live 调用或 cache 写入 → 停止并 recover
- 范围漂移到 A2 实现 / Phase4 / EXEC → 停止并 re-bound

## Linked Artifacts

- plan_task_queue: .servo/worktrack/WT-R4-A1-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A1-intake-review.md
- lake_source: .servo/worktrack/WT-R4-A1-lake-source-contract.md
- cache_inventory: .servo/worktrack/WT-R4-A1-cache-inventory.md
- schema_draft: .servo/worktrack/WT-R4-A1-schema-draft.md
- rate_limits: .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md
- consistency: .servo/worktrack/WT-R4-A1-consistency-matrix.md
- closeout: .servo/worktrack/WT-R4-A1-closeout.md
- gate_evidence: .servo/worktrack/WT-R4-A1-gate-evidence.md
- milestone: .servo/milestone/MS-R4-001.md
- upstream_a0_gaps: .servo/worktrack/WT-R4-A0-data-gaps.md
- upstream_a0_closeout: .servo/worktrack/WT-R4-A0-closeout.md
