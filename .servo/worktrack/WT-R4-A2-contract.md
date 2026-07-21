---
title: "WT-R4-A2: Cache-first 加载路径与 contract/integration 测试（Arch-v1）"
artifact_type: "worktrack-contract"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
status: "active"
node_type: "test"
derived_from_milestone: true
created: "2026-07-20T21:30:00+08:00"
updated: "2026-07-20T21:30:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A2 Cache-first 加载路径与 contract/integration 测试

## Control Signal

- worktrack_id: WT-R4-A2
- milestone_id: MS-R4-001
- derived_from_milestone: true
- status: active
- implementation_status: t2_complete_t3_pending
- node_type: test
- goal_summary: >
  在 milestone 上落地 scoped `ashare_infra`/DataLake，按 A1 冻结合同实现 cache-first
  加载路径，并补齐 Arch-v1 contract/integration 测试；本 WT 不灌湖、不训、不 blind-merge develop。
- execution_not_started: false
- selected_next_action_id: R4-A2-T3
- t1_status: completed
- t1_notes: .servo/worktrack/WT-R4-A2-t1-notes.md
- t1_completed_at: 2026-07-20T22:30:00+08:00
- t1_result: DataLake importable; ashare_exec excluded; 23+23 tests green
- t2_status: completed
- t2_notes: .servo/worktrack/WT-R4-A2-t2-notes.md
- t2_completed_at: 2026-07-21T09:50:00+08:00
- t2_result: make_r4_datalake + consumer cutover; 74 tests green; no ashare_exec
- pool_binding: custom_research_liquidity_quality_v1 / version 1 (61 symbols)
- upstream_a1:
  - .servo/worktrack/WT-R4-A1-lake-source-contract.md (frozen_for_A2)
  - .servo/worktrack/WT-R4-A1-cache-inventory.md (frozen_for_A2)
  - .servo/worktrack/WT-R4-A1-schema-draft.md (frozen_for_A2)
  - .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md (approved 180/80000)
- init_defaults_locked:
  - A2_Q1: Y — scoped ashare_infra bring-up（禁止 blind full merge develop；禁止 tests-only）
  - A2_Q2: Y — caps→`inputs/configs` 可选（T4）；否则 defer A3
  - A2_Q3: Y — daily_basic/moneyflow 经 adapter 或 thin lake helpers 均可
- out_of_scope: lake_fill; training; Phase_4; EXEC-002; silent live; token-in-repo; blind_full_merge_develop
- plan_task_queue: .servo/worktrack/WT-R4-A2-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A2-intake-review.md

## Metadata

- 工作追踪编号: WT-R4-A2
- 分支: milestone/MS-R4-001-tushare-datalake
- 基准分支: develop
- 基准引用: adede390e14efdbf82b81da282da653cb83cc0a7
- 约定状态: active
- 负责人: OceanEyeFF
- 更新时间: 2026-07-20T21:30:00+08:00
- milestone_id: MS-R4-001

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-R4-001-tushare-datalake@adede390e14efdbf82b81da282da653cb83cc0a7
- worktrack_branch: milestone/MS-R4-001-tushare-datalake
- integration_target_ref: milestone/MS-R4-001-tushare-datalake
- closeout_target_ref: milestone/MS-R4-001-tushare-datalake
- final_baseline_branch: develop
- checkpoint_base_ref: adede390e14efdbf82b81da282da653cb83cc0a7
- branch_action: use_existing_milestone_branch
- branch_action_reason: >
  one_development_branch_per_milestone；禁止为 A2 另开 feature 分支。
  Tip lags develop (DataLake on develop only); A2 may path-limited bring-up
  ashare_infra from develop, but must not pull ashare_exec / Phase4 into R4.

## Milestone Binding

- milestone_id: MS-R4-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-R4-001.md
- decisions_locked: >
  D2=L2, D3=R1, D5=tushare_primary, CG2=M1,
  pool=custom_research_liquidity_quality_v1@1,
  A1_caps=180/80000_approved,
  A2_Q1=scoped_infra_bringup, A2_Q2=caps_promo_optional, A2_Q3=adapter_or_thin_helpers

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-R4-001-WT-R4-A2-intake-review.md
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
- prerequisite: WT-R4-A1 closed (pass)

## Node Type

- type: test
- source_from_milestone: worktrack_list WT-R4-A2 node_type=test
- baseline_form: commit-on-milestone-branch
- merge_required: yes（合入 develop 待 milestone close / programmer checkpoint）
- gate_criteria: >
  DataLake 可 import；cache-first 路径绑定 A1 合同与批准池；
  Arch-v1 contract/integration 测试通过（无 live）；明确 510300/soft80 residuals；
  无 token 入仓；无灌湖/训/Phase4/EXEC-002；无 blind full merge develop
- if_interrupted_strategy: checkpoint-or-recover

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: test WT；紧贴 A1 冻结合同 + scoped infra；分派按任务切片

## 任务目标

### Control Signal

- 目标摘要: scoped DataLake 落地 + cache-first + Arch-v1 contract/integration 测（无 live）。

### Supporting Detail

- 完整目标: >
  从 develop 路径限定引入 `ashare_infra`（含 DataLake 与所需 data adapters），
  默认 `default_source=tushare`、`adjust=qfq`、`refresh=False`；
  相对 A0 池与 A1 inventory/schema 写 contract/integration 测试；
  可选将 180/80000 caps 写入 `inputs/configs`。A3 才做 limited-live 补洞。

## 范围

### Control Signal

- 范围摘要: milestone 上 scoped infra + 测试；只读 cache；禁止 live/fill。

### Supporting Detail

- 允许写入:
  - `src/ashare_infra/**`（scoped bring-up from develop；排除 ashare_exec）
  - 必要的 lab shim / symbols 配套（最小）
  - `tests/{unit,integration,contract}/**` 与 A2 相关测
  - 可选 `inputs/configs/*` rate-limit 升格
  - `.servo/worktrack/WT-R4-A2-*` / control-state / milestone progress（最小）
- 允许只读:
  - A1 冻结合同 / inventory / schema / caps
  - `inputs/pools/research_liquidity_quality/`
  - `inputs/data/cache/tushare_*`（测试只读；不写 cache）
- 数据策略: **只读 cache**；禁止 live；禁止灌湖写盘（除非另批）

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不灌湖、不 limited-live、不训、不并 Phase4/EXEC-002、不 blind-merge develop。

### Supporting Detail

- A3 limited-live 补洞战役
- A4 derived QA 终稿
- 训练 / 模型晋升
- Phase 4 lab 去重
- EXEC-002 / ashare_exec 扩展
- Blind `git merge develop`（改用 path-limited bring-up）
- commit/push（除非 programmer 另批）
- 最终 milestone 验收

## 受影响模块

### Control Signal

- 关键影响模块: `ashare_infra.lake` / `ashare_infra.data`；`tests/**`；可选 configs；`.servo/worktrack/WT-R4-A2-*`

## 计划中的下一状态

- Init 后: Schedule → Dispatch R4-A2-T1（scoped ashare_infra land）
- closeout 后: WT-R4-A3 intake/init

## 验收标准

- [x] `from ashare_infra.lake import DataLake` 在 milestone tip 可用
- [x] Cache-first 默认路径绑定 A1 合同（tushare / qfq / pool v1 / history≥2023-01-01）via `make_r4_datalake`
- [ ] Contract 测覆盖：布局、关键列、池 61 绑定、`510300` unavailable
- [x] Integration/合同测覆盖：R4 面无直调 `load_or_fetch_*`（`test_no_direct_load_or_fetch`）；cache-hit/as_of 细节可在 T4 补
- [x] 无 live / 无 token 入仓 / 无灌湖写盘（本切片）
- [x] 明确 out-of-scope：Phase4 / EXEC-002 / training / blind full merge develop

## 约束

- L2 + M1/normal；A2 零网络拉数（测用本地 cache / smoke / mock）
- 绑定 `custom_research_liquidity_quality_v1@1`
- one milestone development branch
- Caps 已 approved（180/80000）；升格 configs 可选
- Soft80 / 510300 为 accepted inventory residuals，不阻塞 A2 Gate（须显式断言）

## 回滚条件

- 出现 live 调用或未经批准的 cache 写入 → 停止并 recover
- 范围漂移到 EXEC / Phase4 / full develop merge → 停止并 re-bound

## Linked Artifacts

- plan_task_queue: .servo/worktrack/WT-R4-A2-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A2-intake-review.md
- upstream_a1_lake: .servo/worktrack/WT-R4-A1-lake-source-contract.md
- upstream_a1_inventory: .servo/worktrack/WT-R4-A1-cache-inventory.md
- upstream_a1_schema: .servo/worktrack/WT-R4-A1-schema-draft.md
- upstream_a1_caps: .servo/worktrack/WT-R4-A1-rate-limit-recommendations.md
- upstream_a1_closeout: .servo/worktrack/WT-R4-A1-closeout.md
- milestone: .servo/milestone/MS-R4-001.md
