---
title: "WT-T1-A1: 只读 inventory + 目标架构草案 + 搬迁/退役清单 + cov floor 建议"
artifact_type: "worktrack-contract"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A1"
status: "active"
node_type: "audit"
derived_from_milestone: true
created: "2026-07-14T17:38:00+08:00"
updated: "2026-07-14T17:38:00+08:00"
owner: "OceanEyeFF"
---

# WT-T1-A1 只读 inventory + 目标架构草案

## Control Signal

- worktrack_id: WT-T1-A1
- milestone_id: MS-T1-001
- derived_from_milestone: true
- status: active
- node_type: audit
- goal_summary: >
  只读产出测试面 inventory、目标分层架构草案、搬迁/退役清单与温和 cov floor 建议；
  禁止删测与目录搬迁。
- next_state_after_close: schedule/close → handoff WT-T1-A2（待 programmer 批退役清单后）
- execution_not_started: false
- inventory_published: true
- inventory_ref: .servo/worktrack/WT-T1-A1-inventory.md
- awaiting: programmer_approval_Del-A_Arch-v1_Cov-draft

## Metadata

- 工作追踪编号: WT-T1-A1
- 分支: milestone/MS-T1-001-test-suite-rewrite
- 基准分支: develop
- 基准引用: 476da6b98e5c7a9ad84df17764a54f4a331105b7
- 约定状态: active
- 负责人: OceanEyeFF
- 更新时间: 2026-07-14T17:38:00+08:00
- milestone_id: MS-T1-001

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-T1-001-test-suite-rewrite@476da6b98e5c7a9ad84df17764a54f4a331105b7
- worktrack_branch: milestone/MS-T1-001-test-suite-rewrite
- integration_target_ref: milestone/MS-T1-001-test-suite-rewrite
- closeout_target_ref: milestone/MS-T1-001-test-suite-rewrite
- final_baseline_branch: develop
- checkpoint_base_ref: 476da6b98e5c7a9ad84df17764a54f4a331105b7
- branch_action: use_existing_milestone_branch
- branch_action_reason: control-state one_development_branch_per_milestone；禁止为单个 worktrack 另开 feature 分支

## Milestone Binding

- milestone_id: MS-T1-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-T1-001.md
- decisions_locked: D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-T1-001-WT-T1-A1-intake-review.md
- repo_fundamentals: pass
- snapshot_freshness: pass
- milestone_purpose_alignment: pass
- historical_conflict_risk: medium
- worktrack_adjustment_recommendations: none
- add_remove_worktrack_recommendations: none
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 1
- latest_review_checkpoint: MS-T1-001-intake-2026-07-14T17:22:00+08:00
- effective_review_pass: true
- review_invalidated_by: none

## Node Type

- type: audit
- source_from_goal_charter: >
  Goal Charter Engineering Node Map 无独立 `audit` 类型；本 worktrack 按 milestone 声明
  `audit`，策略对齐 `research`（report/inventory artifact）+ 允许将报告提交到 milestone 分支。
- baseline_form: inventory-report-on-milestone-branch
- merge_required: yes（inventory 产物提交到 milestone 分支；合入 develop 待 milestone close）
- gate_criteria: >
  inventory 完整（迁/删/留/待定）+ 目标架构草案 + cov floor 建议 + 无删测/无搬迁动作
- if_interrupted_strategy: preserve-report-and-stop

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: A1 为只读审计/清单撰写，需紧贴 live tests/ 与 `.servo`，适合当前载体

## 任务目标

### Control Signal

- 目标摘要: 产出可审批的测试面 inventory、目标架构草案、退役/搬迁清单与 cov floor 建议。

### Supporting Detail

- 完整目标: 在不删除/不搬迁任何测例的前提下，扫描 `tests/`（及相关 conftest/fixtures），
  分类冗余/慢/脆弱/旧路径/弱断言，输出搬迁地图与 Del-yes 退役候选；起草 T-heavy 分层
  目标结构；给出 Acc-balanced 温和 cov floor 建议值（供后续批准）。

## 范围

### Control Signal

- 范围摘要: 只读扫描 + 写 inventory/架构草案；禁止删测与结构搬迁。

### Supporting Detail

- 扫描面至少覆盖:
  - `tests/test_*.py` 全量（约 45 文件）
  - 共享 fixtures / conftest（若有）
  - pytest 配置缺口（markers、路径、cov 插件用法）
  - 与 scripts/ 的耦合测、存在性/弱断言测
  - 相对 R4：依赖数据湖才能修的测例标 defer（预期少）
- 允许写入:
  - `.servo/worktrack/WT-T1-A1-*.md`（inventory / architecture draft）
  - 必要时极小范围更新本 contract / plan queue / control-state 进度字段

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不删测、不搬迁目录、不落 markers/cov 硬门禁、不启 A2–A4、不做 R4。

### Supporting Detail

- 任何测例删除 / 合并执行 / `git rm`
- 移动/重命名 `tests/` 目录结构
- 落地 pytest.ini markers 或 cov fail-under（仅建议）
- 改写 `src/` 业务逻辑
- TuShare 拉数 / 数据湖
- commit/push（除非 programmer 另批）
- 最终 milestone 验收

## 受影响模块

### Control Signal

- 关键影响模块: `.servo/worktrack/`（报告）；只读触及 `tests/`、`pyproject.toml`、相关 scripts

### Supporting Detail

- 只读: tests/, pyproject.toml, scripts/（被测引用）, docs/guides（若有测试约定）
- 写入: `.servo/worktrack/WT-T1-A1-inventory.md`（主交付）、架构草案、queue 指针

## 验收标准

- [x] 存在 inventory：每条候选含路径、分类（迁/删/留/待定）、理由摘要
- [x] 存在目标架构草案（分层目录 + fixtures/factories + markers 草图）
- [x] 存在温和 cov floor 建议（整体与/或核心包；标明待批）
- [x] 工作区无删测/搬迁类 diff（相对 checkpoint_base_ref）
- [x] 未越界进入 A2/A3/A4/R4

## 约束

- high_risk_command_mode: normal
- destructive_cleanup: forbidden in A1
- delete_policy: Del-yes 仅记录建议；执行属 A2
- acceptance_signal_policy: Acc-balanced（A1 只建议 floor）
- protected_paths: src/ ; .servo/goal-charter.md ; inputs/pools/ ; inputs/configs/profiles/ ; inputs/data/cache/tushare*
- inventory_ref: .servo/worktrack/WT-T1-A1-inventory.md

## 回滚条件

- 若误引入删测/搬迁 diff：立即还原，A1 gate fail
- 若发现必须调整 milestone worktrack 列表：停止并 handback RepoScope.Decide

## 计划中的下一状态

- A1 inventory + 架构草案已发布 → **等待 programmer 批准 Del-A / Arch-v1 / Cov-draft** → Init WT-T1-A2
