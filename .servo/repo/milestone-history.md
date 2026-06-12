---
title: "Milestone History"
artifact_type: "milestone-history"
updated: "2026-06-12T01:28:03+08:00"
updated_by: "harness-skill"
---

# Milestone History

> Completed and superseded milestones are moved here from `.servo/repo/milestone-backlog.md`.

## Completed

### MS-S0-001

- milestone_id: MS-S0-001
- title: 主线预测可信评估与优化闭环
- purpose: 证明或否定当前 `3d/5d/10d` 主线预测是否具备可作为默认 `alpha_score` 的可信基础，并建立后续优化闭环。
- status: completed
- milestone_kind: goal-driven
- priority: 1
- depends_on_milestones: MS-ENV-000
- created_by: programmer-confirmed-harness
- created_at: 2026-06-10T11:49:54+08:00
- completed_at: 2026-06-12T01:28:03+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted_with_residual_risk
- updated: 2026-06-12T01:28:03+08:00
- updated_by: harness-skill
- artifact_path: .servo/milestone/MS-S0-001.md
- composite_acceptance_report: .servo/milestone/MS-S0-001-composite-acceptance.md
- worktrack_list:
  - WT-A2-001 (done): 可信评估范式与伪信号排查
    - result: Evaluation protocol and anti-false-signal gate were frozen for mainline 3d/5d/10d credibility review.
    - residual_risk: random-label CLI and industry / market-cap neutralization remain follow-up anti-cheat gaps.
  - WT-A3-001 (done): 预测优化实验队列
    - result: Optimization queue and dry-run manifest were organized under the A2 protocol without model retraining.
    - residual_risk: actual training/evaluation execution remains a later approved milestone.
  - WT-B0-001 (done): 1d 日内数据源可用性验证
    - result: 1d modeling remains blocked until live minute-data permission, history depth, field quality, and replay proof are verified.
    - residual_risk: TuShare `stk_mins` is the primary candidate; AkShare remains smoke-only for this repo.
  - WT-C0-001 (done): 决策模型 I/O 草案
    - result: Decision-model C0 I/O draft and signal maturity guards were captured without trading implementation.
    - residual_risk: C1/C2/C3 implementation and canonical docs promotion require later approval.
- final_note: No model is promoted; `alpha_score` remains a candidate research signal until later gates pass.

### MS-ENV-000

- milestone_id: MS-ENV-000
- title: Conda 环境可用性验证
- purpose: 验证当前机器上的 conda 环境是否仍能支持 T1.AI 的基本开发、导入、测试和后续研究工作；最终确认 `py311-private` 是当前 canonical conda 环境。
- status: completed
- milestone_kind: goal-driven
- priority: 0
- depends_on_milestones: none
- created_by: programmer-confirmed-harness
- created_at: 2026-06-11T11:34:36+08:00
- completed_at: 2026-06-11T16:40:59+08:00
- accepted_by: OceanEyeFF
- updated: 2026-06-11T16:40:59+08:00
- updated_by: harness-skill
- artifact_path: .servo/milestone/MS-ENV-000.md
- composite_acceptance_report: .servo/milestone/MS-ENV-000-composite-acceptance.md
- worktrack_list:
  - WT-ENV-001 (done): Conda 环境盘点与最小 smoke 验证
    - result: `py311-private` is canonical and passes import smoke, project imports, env guard, ruff availability, and minimal pytest.
    - residual_risk: local GTX 1080 Ti / `sm_61` is not supported by the current PyTorch wheel; CPU lane accepted as sufficient.

## Superseded

- none
