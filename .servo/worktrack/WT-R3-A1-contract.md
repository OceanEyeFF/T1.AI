---
title: "WT-R3-A1: inventory + 引用审计 + 2-fail 定性"
artifact_type: "worktrack-contract"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A1"
status: "active"
node_type: "audit"
derived_from_milestone: true
created: "2026-07-14T11:55:00+08:00"
updated: "2026-07-14T11:55:00+08:00"
owner: "OceanEyeFF"
---

# WT-R3-A1 inventory + 引用审计 + 2-fail 定性

## Control Signal

- worktrack_id: WT-R3-A1
- milestone_id: MS-R3-001
- derived_from_milestone: true
- status: active
- node_type: audit
- goal_summary: 只读产出删除/保留/待定 inventory + 引用审计 + R2 遗留 2-fail 定性（T2）；禁止删除。
- next_state_after_close: schedule/close → handoff WT-R3-A2（待 programmer 批清单后）
- execution_not_started: true
- runtime_dispatch_mode: current-carrier

## Metadata

- 工作追踪编号: WT-R3-A1
- 分支: milestone/MS-R3-001-deep-cleanup
- 基准分支: develop
- 基准引用: 6511d8c1f033d60c6eee43847b4682bcbcdbc262
- 约定状态: active
- 负责人: OceanEyeFF
- 更新时间: 2026-07-14T11:55:00+08:00
- milestone_id: MS-R3-001

## Branch Policy

- baseline_branch: develop
- branch_source_ref: milestone/MS-R3-001-deep-cleanup@6511d8c1f033d60c6eee43847b4682bcbcdbc262
- worktrack_branch: milestone/MS-R3-001-deep-cleanup
- integration_target_ref: milestone/MS-R3-001-deep-cleanup
- closeout_target_ref: milestone/MS-R3-001-deep-cleanup
- final_baseline_branch: develop
- checkpoint_base_ref: 6511d8c1f033d60c6eee43847b4682bcbcdbc262
- branch_action: use_existing_milestone_branch
- branch_action_reason: control-state one_development_branch_per_milestone；禁止为单个 worktrack 另开 feature 分支

## Milestone Binding

- milestone_id: MS-R3-001
- derived_from_milestone: true
- milestone_artifact: .servo/milestone/MS-R3-001.md
- decisions_locked: D1=B, D2=T2, D3=P3, D4=confirmed

## Worktrack Intake Review

- worktrack_intake_review: .servo/worktrack/MS-R3-001-WT-R3-A1-intake-review.md
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
- latest_review_checkpoint: MS-R3-001-intake-2026-07-14T11:30:00+08:00
- effective_review_pass: true
- review_invalidated_by: none

## Node Type

- type: audit
- source_from_goal_charter: >
  Goal Charter Engineering Node Map 无独立 `audit` 类型；本 worktrack 按 milestone 声明
  `audit`，策略对齐 `research`（report/inventory artifact）+ 允许将报告提交到 milestone 分支。
- baseline_form: inventory-report-on-milestone-branch
- merge_required: yes（inventory 产物提交到 milestone 分支；合入 develop 待 milestone close）
- gate_criteria: inventory 完整（删/留/待定）+ 引用审计摘要 + 2-fail 定性记录 + 无删除动作
- if_interrupted_strategy: preserve-report-and-stop

## Execution Policy

- runtime_dispatch_mode: current-carrier
- dispatch_mode_source: worktrack-contract
- fallback_reason: A1 为只读审计/清单撰写，需紧贴 live `.servo` 与路径扫描，适合当前载体

## 任务目标

### Control Signal

- 目标摘要: 产出可审批的清理 inventory，并对 R2 遗留 2 fail 做 T2 定性。

### Supporting Detail

- 完整目标: 在不删除任何文件的前提下，按 P3 默认分类扫描候选面，做引用审计，输出
  「建议删 / 保留 / 待定」清单；对 2 个旧路径失败测试定性为 R3 可处置或 defer R4。

## 范围

### Control Signal

- 范围摘要: 只读扫描 + 写 inventory/定性报告；禁止删除与代码修复（除报告本身）。

### Supporting Detail

- 扫描面至少覆盖:
  - `docs/archive/`、`docs/research/`（P3 过时材料默认建议删）
  - `workspace/checkpoints/`（未引用旧权重默认建议删）
  - `scripts/` one-off / 无引用脚本
  - 过时实验 TOML、AkShare 探针缓存
  - R2 遗留 2 pytest 失败的根因定性（T2）
- 允许写入:
  - `.servo/worktrack/WT-R3-A1-*.md`（inventory / triage 报告）
  - 必要时极小范围更新本 contract / plan queue / control-state 进度字段

## 非目标（不做的事）

### Control Signal

- 非目标摘要: 不删除、不修业务代码、不做数据湖、不启 A2/A3。

### Supporting Detail

- 任何破坏性删除 / `git rm` / 清空目录
- 修复或重写 `src/` 业务逻辑
- 为修测而重建数据集 / TuShare 拉取
- 批准清单或执行 A2 删除
- commit/push（除非 programmer 另批）
- 最终 milestone 验收

## 受影响模块

### Control Signal

- 关键影响模块: `.servo/worktrack/`（报告）；只读触及 docs/scripts/workspace/inputs/tests

### Supporting Detail

- 只读: docs/, scripts/, workspace/checkpoints/, inputs/, tests/, configs under inputs/
- 写入: `.servo/worktrack/WT-R3-A1-inventory.md`（主交付）、定性附录、queue/evidence 指针

## 验收标准

- [x] 存在 inventory 文档，每条候选含：路径、默认桶（P3）、引用证据摘要、建议（删/留/待定）
- [x] 受保护路径未进入「建议删」或已标注为受保护保留
- [x] 2-fail 定性记录完整：每个 fail 的根因类别 + R3 可处置 / defer R4
- [x] 工作区无删除类 diff（相对 checkpoint_base_ref）
- [x] 未越界进入 A2/A3/R4

## 约束

- high_risk_command_mode: normal
- destructive_cleanup: forbidden in A1（honored — no deletes）
- protected_paths: src/ ; .servo/goal-charter.md ; inputs/pools/ ; inputs/configs/profiles/ ; inputs/data/cache/tushare*
- inventory_ref: .servo/worktrack/WT-R3-A1-inventory.md

## 回滚条件

- 若误引入删除 diff：立即还原，A1 gate fail
- 若发现必须调整 milestone worktrack 列表：停止并 handback RepoScope.Decide

## 计划中的下一状态

- A1 inventory 已发布 → **等待 programmer 批准删除批次** → Init WT-R3-A2；F1/F2 归 A3 路径修复
