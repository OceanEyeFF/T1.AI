---
title: "MS-T1-001 / WT-T1-A1 Intake Review"
artifact_type: "worktrack-intake-review"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A1"
updated: "2026-07-14T17:38:00+08:00"
owner: "OceanEyeFF"
---

# MS-T1-001 / WT-T1-A1 Intake Review

## Control Signal

- selected_worktrack_id: WT-T1-A1
- selected_worktrack_title: 只读 inventory + 目标架构草案 + 搬迁/退役清单 + cov floor 建议
- target_milestone_id: MS-T1-001
- derived_from_milestone: true
- active_milestone_ref: .servo/milestone/MS-T1-001.md
- active_milestone_branch: milestone/MS-T1-001-test-suite-rewrite
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- milestone_review_gate_ready: true
- latest_review_status: effective_pass
- milestone_review_count: 1
- latest_review_checkpoint: MS-T1-001-intake-2026-07-14T17:22:00+08:00
- effective_review_pass: true
- review_invalidated_by: none
- next_route: WorktrackScope.Init / Schedule for WT-T1-A1

## Repo Fundamentals

- repo_fundamentals: pass
- active_milestone: MS-T1-001
- milestone_status: active
- baseline_branch: develop
- milestone_branch: milestone/MS-T1-001-test-suite-rewrite
- current_branch: milestone/MS-T1-001-test-suite-rewrite
- checkpoint_ref: 476da6b98e5c7a9ad84df17764a54f4a331105b7
- goal_alignment: >
  WT-T1-A1 是 T-heavy 测试体系清理的只读 inventory 步：产出测试面地图、
  目标架构草案、搬迁/退役清单与温和 cov floor 建议；禁止删测与结构搬迁。
- prohibited_actions:
  - 任何测例删除 / 合并执行 / git rm（含「建议删」项）
  - WT-T1-A2 / A3 / A4 范围工作（删测、分层搬迁、markers/cov 落地）
  - TuShare 数据湖 / 配额消耗拉取（MS-R4）
  - 改写 `src/` 业务行为
  - 模型重训、信号晋升、push、final milestone acceptance
  - 新建 per-feature 分支（one-development-branch-per-milestone）

## Snapshot Freshness

- snapshot_freshness: pass
- evidence_refs:
  - .servo/control-state.md
  - .servo/milestone/MS-T1-001.md
  - .servo/repo/milestone-backlog.md
  - .servo/repo/MS-T1-001-pre-milestone-intake-review.md
  - git HEAD milestone/MS-T1-001-test-suite-rewrite @ 476da6b
- caveat: MS-R3 已 formal close；A1 仅写 inventory/架构草案到 `.servo/worktrack/`，不改 tests/ 结构。

## Milestone Purpose Alignment

- milestone_purpose_alignment: pass
- worktrack_role: >
  为 T-heavy + Del-yes + Acc-balanced 建立可审批 inventory 与目标架构草案；
  是 A2 破坏性删测与 A3 搬迁的唯一合法前置。
- covers_completion_signals:
  - CS1（inventory + 批准记录可追溯）的 inventory / 建议清单部分
  - CS4 的 cov floor **建议值**（数值锁定与落地在 A4）
- does_not_cover:
  - CS2 新结构回归全绿（A3/A4）
  - CS3 markers/文档终态（A4）
  - CS4 cov 门禁落地（A4）
  - CS5 R4 延后交接终稿（A4）
  - 经批准的实际删测（A2）

## Historical Conflict Risk

- historical_conflict_risk: medium
- prior_context:
  - tests/ 约 45 扁平文件、~9.7k LOC；无 markers/分层配置。
  - R3 已清路径债并全绿；T-heavy 重写窗口合理但假绿风险高。
  - Del-yes 误删靠清单批准门缓解；A1 不得越权删除。
- conflict_controls:
  - A1 只读扫描 + 写 inventory / 架构草案
  - 「建议删」必须附理由；仍有契约价值的标「保留」或「待定」
  - cov floor 只给建议区间/数值草案，不落硬门禁

## Worktrack Adjustment Recommendations

- worktrack_adjustment_recommendations: none
- add_remove_worktrack_recommendations: none
- reason: A1 已在 confirmed milestone worktrack_list 首位；与 D1–D5 一致，无需增删重排。

## Verdict

- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true
- blockers: none
- programmer_trigger: 「Init WT-T1-A1（只读 inventory）」
