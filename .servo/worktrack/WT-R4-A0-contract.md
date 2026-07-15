---
title: "WT-R4-A0: 新策略准则草案 + ≤100 池导出（registry）+ 与旧池差异说明"
artifact_type: "worktrack-contract"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A0"
status: "active"
node_type: "feature"
derived_from_milestone: true
created: "2026-07-15T09:12:00+08:00"
updated: "2026-07-15T13:50:00+08:00"
owner: "OceanEyeFF"
---

# WT-R4-A0 research_liquidity_quality 池策略 + registry 导出

## Control Signal

- worktrack_id: WT-R4-A0
- milestone_id: MS-R4-001
- derived_from_milestone: true
- status: active
- implementation_status: complete_awaiting_gate_close
- node_type: feature
- strategy_thesis: research_liquidity_quality
- strategy_folder: research_liquidity_quality
- soft_target_size: 80
- hard_cap: 100
- goal_summary: >
  实现可审计的 research_liquidity_quality 策略（主板可研究/可交易卫生筛），
  cache-first 选出 ≤80（硬上限 100）的可版本化池并 registry 导出，产出相对
  旧 low_manipulation 的差异说明。
- next_state_after_close: handoff WT-R4-A1（湖/源合同 + 日/RPM 上限建议）
- execution_not_started: false
- strategy_brief_ref: .servo/worktrack/WT-R4-A0-strategy-brief.md
- t1_status: completed
- t2_status: completed
- t3_status: completed
- t4_status: completed
- t5_status: completed
- t6_status: completed
- t3_selected_count: 61
- t3_data_gaps_ref: .servo/worktrack/WT-R4-A0-data-gaps.md
- t3_run_notes_ref: .servo/worktrack/WT-R4-A0-t3-select-run-notes.json
- t4_export_notes_ref: .servo/worktrack/WT-R4-A0-t4-export-notes.md
- t5_diff_ref: .servo/worktrack/WT-R4-A0-diff-vs-low-manipulation.md
- closeout_ref: .servo/worktrack/WT-R4-A0-closeout.md
- gate_evidence_ref: .servo/worktrack/WT-R4-A0-gate-evidence.md
- stock_pool_id: custom_research_liquidity_quality_v1
- stock_pool_version: "1"
- registry_path: inputs/pools/research_liquidity_quality/config.toml
- strategy_impl_ref: src/ashare_lab/stock_pool/research_liquidity_quality/
- unit_tests_ref: tests/unit/stock_pool/test_research_liquidity_quality_strategy.py
- unit_tests_result: 15 passed tests/unit/stock_pool/ (py311-private)
- smoke_result: cache-first select idempotent; count=61<=100
- awaiting: WorktrackScope.Judging (gate) then Close; commit/push approval-gated

## Metadata

- 工作追踪编号: WT-R4-A0
- 分支: milestone/MS-R4-001-tushare-datalake
- 基准分支: develop
- 基准引用: aa2b14c1cd109e67e5eb48314572e03da1a4e750
- 约定状态: active
- 负责人: OceanEyeFF
- 更新时间: 2026-07-15T09:12:00+08:00
- milestone_id: MS-R4-001

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-R4-001-tushare-datalake@aa2b14c1cd109e67e5eb48314572e03da1a4e750
- worktrack_branch: milestone/MS-R4-001-tushare-datalake
- integration_target_ref: milestone/MS-R4-001-tushare-datalake
- closeout_target_ref: milestone/MS-R4-001-tushare-datalake
- final_baseline_branch: develop
- checkpoint_base_ref: aa2b14c1cd109e67e5eb48314572e03da1a4e750
- branch_action: use_existing_milestone_branch
- branch_action_reason: >
  control-state one_development_branch_per_milestone；禁止为单个 worktrack 另开
  feature 分支。与 MS-T1 worktrack Init 先例一致。

## Milestone Binding

- milestone_id: MS-R4-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-R4-001.md
- decisions_locked: >
  D1=B, D1b=P1, D1c=C2_cap100, D2=L2, D3=R1, CG2=M1,
  D4=lake_qa, D5=tushare_primary, A0_Q1=T1_research_liquidity_quality

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-R4-001-WT-R4-A0-intake-review.md
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

## Node Type

- type: feature
- source_from_goal_charter: Goal Charter Engineering Node Map → feature
- source_from_milestone: worktrack_list WT-R4-A0 node_type=feature
- baseline_form: commit-on-milestone-branch
- merge_required: yes（合入 develop 待 milestone close / programmer checkpoint）
- gate_criteria: >
  可审计准则文档 + strategy 实现 + registry 导出（count≤100，目标≤80）+
  旧池差异报告 + 无 silent full-campaign / 无 token 入仓 + 基础测试或可复现 smoke
- if_interrupted_strategy: checkpoint-or-recover

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: >
  A0 需紧贴 stock_pool/registry、cache 布局与 `.servo` 合同边界；高共享、低并行价值，
  适合当前载体。live pull 仍 L2+M1 门控，默认 cache-first。

## 任务目标

### Control Signal

- 目标摘要: 落地 research_liquidity_quality 策略与 ≤80 可版本化池（硬上限 100），并说明相对旧池差异。

### Supporting Detail

- 完整目标: >
  编写可审计准则（维度、硬过滤、规模、非目标）；实现
  `src/ashare_lab/stock_pool/research_liquidity_quality/`（strategy + config）；
  在现有 tushare_* cache 上 cache-first 选股；经 registry API 导出三件套；
  产出相对 low_manipulation / custom_low_manipulation_v1 的差异报告；
  缺数据缺口列表化留给 A3，不启动 silent live 战役。

## 范围

### Control Signal

- 范围摘要: 新策略准则 + 实现 + cache-first 选股 + registry 导出 + 旧池 diff；禁止全市场拉数与训练。

### Supporting Detail

- 允许写入:
  - `src/ashare_lab/stock_pool/research_liquidity_quality/`
  - registry 导出产物（`configs/stock_pools/` 或策略约定路径，经 registry API）
  - `.servo/worktrack/WT-R4-A0-*.md`（brief、diff、缺口清单、进度）
  - 聚焦测试：`tests/unit/` 或 `tests/integration/` 下与策略/registry 相关用例
  - 必要时极小范围更新本 contract / plan queue / control-state / milestone progress
- 允许只读:
  - 现有 `tushare_*` cache、`low_manipulation` 策略与 pool、stock_pool 指南
- 数据策略:
  - cache-first（R1）
  - 默认禁止 live；若某步确需有限探测，须 L2+M1 显式批准且记证据

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不做 A1–A4 主体、全市场/full-campaign、训练晋升、删 AkShare、未批 live。

### Supporting Detail

- A1 日/RPM 数值最终批准与湖合同终稿
- A2 加载路径重构 / contract 测试主体
- A3 limited-live 增量补洞战役
- A4 derived + 质量审计终稿
- X×Y×Z 训练、模型重训、alpha_score 晋升
- 全市场 silent full-campaign；把旧 low_manipulation 当最终 universe
- 删除 AkShare 代码
- commit/push（除非 programmer 另批）
- 最终 milestone 验收

## 受影响模块

### Control Signal

- 关键影响模块: `src/ashare_lab/stock_pool/`、registry 导出、`.servo/worktrack/WT-R4-A0-*`、聚焦测试

### Supporting Detail

- 写入: stock_pool/research_liquidity_quality/, configs/stock_pools/ (via API), .servo/worktrack/, tests/
- 只读: inputs/data/cache/tushare_*, inputs/pools/low_manipulation/, docs/guides/stock_pool_maintenance_guide.md

## 计划中的下一状态

- closeout 后: WT-R4-A1 intake/init（不自动越界）

## 验收标准

- [x] 存在可审计准则文档（命题、维度/硬过滤、软目标 80、硬上限 100、非目标）— WT-R4-A0-strategy-brief.md
- [x] 存在 `research_liquidity_quality` Strategy 实现 + config
- [x] registry 导出池 symbols_count ≤100，且尽量 ≤80；可复现加载 — count=61（soft deficit documented）
- [x] 存在相对旧 low_manipulation 的差异报告（交集/仅新/仅旧 + 叙事）— WT-R4-A0-diff-vs-low-manipulation.md
- [x] 缺 cache 缺口已列表化（若不需补洞可为 empty）— WT-R4-A0-data-gaps.md
- [x] 无 token 入仓；无未批准 live/full-campaign
- [x] 至少有聚焦单测或可复现 smoke 证明策略/registry 合同 — T6 (15 unit + cache smoke)

## 约束

- 硬上限 100；软目标 80
- M1/normal；L2 政策下 A0 默认 cache-first
- 旧池仅对照，不得升格为最终 universe
- one milestone development branch；不另开 feature 分支

## 回滚条件

- 策略实现不可复现或违规 live/泄露 token → 停止并 recover
- 导出池超过硬上限或无法经 registry API 复现 → 不得宣告完成

## Linked Artifacts

- plan_task_queue: .servo/worktrack/WT-R4-A0-plan-task-queue.md
- intake_review: .servo/worktrack/MS-R4-001-WT-R4-A0-intake-review.md
- milestone: .servo/milestone/MS-R4-001.md
- t1_handoff: .servo/worktrack/WT-T1-A4-r4-handoff.md
