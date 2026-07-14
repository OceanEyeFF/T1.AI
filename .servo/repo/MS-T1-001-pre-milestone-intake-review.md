---
title: "MS-T1-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-T1-001"
proposed_title: "广义测试体系清理"
updated: "2026-07-14T17:22:00+08:00"
updated_by: "cursor-pre-milestone-intake-with-programmer-final-confirmation"
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
---

# MS-T1-001 Pre-Milestone Intake Review

## Intake Status

```yaml
intake_status: ready
programmer_confirmed: true
ready_for_init_milestone: true
confirmation_required: false
intake_skipped: false
skip_reason: null
accepted_risk: []
residual_risk_accepted: true
accepted_residual_risk:
  - cov_floor_numeric_value_deferred_to_A1_inventory
  - r3_formal_close_still_pending_process_debt
continuation_required: false
next_question_blocks_ready: false
decisions_locked: [D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed]
awaiting: init_milestone_instruction
```

## Request Summary

```yaml
request_summary: >
  MS-T1-001「广义测试体系清理」intake 已完成：T-heavy、先 T1 后 R4、Del-yes、
  Acc-balanced；programmer 已最终确认 brief。intake_status=ready；等待显式 Init
  指令后才可由 init-milestone-skill 写入/激活。建议 Init 前 formal close MS-R3。
```

## Observed Facts

- `origin/develop @ 296318b` 已含 MS-R3-001；pytest 基线曾 **397 passed / 0 failed**。
- `tests/`：约 45 扁平 `test_*.py`，~9.7k LOC；无 markers/分层配置。
- Programmer 确认 D1=**C / T-heavy**、D2=**S1 / 先 T1 后 R4**、D3=**Del-yes**、D4=**Acc-balanced**。
- Programmer **最终确认 brief（D5）**（2026-07-14T17:22+08:00）：同意 scope / non-goals / acceptance / candidate worktracks；`ready_for_init_milestone=true`。
- 仍禁止在未收到 Init 指令时创建/激活 milestone 或执行删测。

## Inferred Assumptions

- cov floor 精确数值属 A1 建议后再批；已接受为 residual risk。
- Init 前 formal close MS-R3 为推荐流程，非本 intake 自动动作。

## Unknowns

- ~~D1–D5~~ 已确认
- cov floor 精确数值（A1）
- R3 formal close 是否先于 Init（推荐先做）

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: D1
    status: answered
    answer: C — T-heavy
  - id: D2
    status: answered
    answer: S1 — 先 T1 后 R4
  - id: D3
    status: answered
    answer: Del-yes — 经批准可删/合并
  - id: D4
    status: answered
    answer: Acc-balanced — 结构为主 + 温和 cov 门禁
  - id: D5
    status: answered
    answer: 确认 brief — ready_for_init_milestone
    answered_at: 2026-07-14T17:22:00+08:00
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: R1
    severity: high
    description: T-heavy 假绿 / 回归信心短期波动 — 缓解：分阶段搬迁 + 对照全绿基线
  - id: R2
    severity: medium
    description: 删测误伤 — 缓解：Del-yes + inventory 批准门
  - id: R5
    severity: medium
    description: cov floor 过高逼注水 — 缓解：A1 后再定数值；不以 cov 为唯一成功标准
  - id: R4
    severity: low
    description: MS-R3 formal close 流程债
```

## Open Questions

```yaml
open_questions: []
answered_questions: [D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed]
unresolved_questions: []
```

## Recommended Answers

```yaml
recommended_answers:
  - id: D1
    answer: C — T-heavy
    status: programmer_confirmed
  - id: D2
    answer: S1 — 先 T1 后 R4
    status: programmer_confirmed
  - id: D3
    answer: Del-yes
    status: programmer_confirmed
  - id: D4
    answer: Acc-balanced
    status: programmer_confirmed
  - id: D5
    answer: 确认 brief
    status: programmer_confirmed
```

## Scope Boundary

### In Scope

- 测试面 inventory + 目标架构草案 + 搬迁/退役清单（含 cov floor 建议值）
- 经批准删除/合并死测、重复测、无断言弱测
- `tests/` 目录与命名分层重写；共享 fixtures/factories
- pytest markers + CI/本地 fast/full 分层
- 温和覆盖率门禁（floor 数值 A1 后锁定）
- R4 延后交接：MS-R4 在 T1 完成后再激活

### Non Goals / out_of_scope

- TuShare 数据湖构建或大规模拉数（MS-R4）
- 业务功能开发 / 模型重训 / 信号晋升
- 未批准删测；为冲 cov 注水
- 改写 `src/` 业务行为（测试适配除外）

## Acceptance Signals

- CS1: inventory + 搬迁/退役批准记录可追溯
- CS2: 新结构下约定回归（fast 与/或 full）全绿，或失败均有记录
- CS3: markers、分层约定、文档一致
- CS4: 温和 cov floor 已落盘且通过（数值经 A1 建议 + 批准）
- CS5: R4 延后交接文档存在；未越界执行 R4

## Suggested Milestone Brief

```yaml
suggested_milestone_brief:
  milestone_id: MS-T1-001
  title: 广义测试体系清理（T-heavy）
  purpose: >
    在 R2/R3 全绿基线上，对 tests/ 做架构级重写（分层目录、fixtures/factories、
    markers、CI fast/full），经批准退役死测/重复测，并落地温和覆盖率门禁；
    完成后再启动 MS-R4-001 数据湖。
  milestone_kind: goal-driven
  status: draft_confirmed_awaiting_init
  depends_on_milestones: [MS-R3-001]
  precedes: [MS-R4-001]
  priority: ahead_of_MS-R4-001
  decisions_locked: [D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed]
  cleanup_depth_policy: T-heavy
  schedule_policy: T1_before_R4
  delete_policy: Del-yes_approval_gated
  acceptance_signal_policy: Acc-balanced
  candidate_worktracks:
    - WT-T1-A1: 只读 inventory + 目标架构草案 + 搬迁/退役清单 + cov floor 建议
    - WT-T1-A2: 按批准清单删除/合并（破坏性，需批）
    - WT-T1-A3: 目录分层搬迁 + fixtures/factories（行为等价）
    - WT-T1-A4: markers + CI 分层 + cov 门禁落地 + 文档 + R4 延后交接
  completion_signals:
    - inventory_and_approvals_traceable
    - layered_regression_green
    - markers_docs_consistent
    - mild_cov_floor_enforced
    - r4_deferred_handoff_present
  acceptance_criteria:
    - no_unapproved_test_deletion
    - no_r4_datalake_work
    - cov_not_sole_success_metric
    - behavior_equivalence_on_migrated_tests
```

## Confirmation State

```yaml
confirmation_required: false
programmer_confirmed: true
ready_for_init_milestone: true
intake_skipped: false
```

## Continuation State

```yaml
continuation_state:
  continuation_required: false
  answered_questions: [D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed]
  unresolved_questions: []
  next_required_question: null
  next_question_blocks_ready: false
  checkpoint: MS-T1-001-intake-2026-07-14T17:22:00+08:00
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  entry_verdict: not_applicable
operator_safety_policy:
  destructive_cleanup: approval_gated
  high_risk_command_mode: normal_until_explicitly_changed
milestone_blocking_decision: clear_for_init_after_explicit_instruction
reinforcement_milestone_recommendation:
  needed: false
  recommendation_status: not_needed
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  review_status: effective_pass
  effective_review_pass: true
  milestone_review_count: 1
  latest_review_checkpoint: MS-T1-001-intake-2026-07-14T17:22:00+08:00
  review_invalidated_by: null
```

## Handoff To Init Milestone

```yaml
handoff_to_init_milestone: true
block_reason: null
note: >
  Intake ready. Do NOT create/activate until programmer issues explicit Init.
  Recommended: formal close MS-R3-001 before Init MS-T1-001.
```

## Skip Record

```yaml
intake_skipped: false
```
