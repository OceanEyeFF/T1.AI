---
title: "Milestone History"
artifact_type: "milestone-history"
updated: "2026-06-22T12:45:00+08:00"
updated_by: "codex-with-programmer-acceptance"
---

# Milestone History

> Completed and superseded milestones are moved here from `.servo/repo/milestone-backlog.md`.

## Completed

### MS-S2-001

- milestone_id: MS-S2-001
- title: 股票池分层定义与注册契约
- purpose: 把后续研究所需的股票池分层从口头方向固化为可版本化、可导出、可被训练/评估链路引用的 registry contract，为后续大盘低控盘概率池 3/5/10d 复验提供稳定输入。
- status: completed
- milestone_kind: goal-driven
- priority: 3
- depends_on_milestones: MS-S1-001
- created_by: programmer-confirmed-codex
- created_at: 2026-06-22T09:21:03+08:00
- completed_at: 2026-06-22T12:45:00+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted
- commit: 98ef372 on milestone/MS-S2-001-stock-pool-stratification
- updated: 2026-06-22T12:45:00+08:00
- updated_by: codex-with-programmer-acceptance
- artifact_path: .servo/milestone/MS-S2-001.md
- downstream_contract: docs/modules/downstream_revalidation_input_contract_MS_S2_001.md
- closing_report: .servo/worktrack/s2-a4-milestone-closing-report.md
- worktrack_list:
  - WT-S2-A1 (done): 股票池分层 taxonomy 与 proxy 边界冻结
  - WT-S2-A2 (done): TuShare cache-first 获取策略、限流测试与 registry schema 差距检查
  - WT-S2-A2-next (done): A1 产出压缩与 A3 输入窄化
  - WT-S2-A3 (done): 首批样例池构造、注册与导出 smoke
  - WT-S2-A4 (done): 下游复验输入契约、请求预算与收尾报告
- completion_signals: 11/11 (100%)
- acceptance_criteria: 9/10 (90%, 1 N/A)
- key_artifacts:
  - custom_liquid_large_proxy_v1 (5 symbols, non-research)
  - custom_low_control_proxy_candidate_v1 (3 symbols, research-only)
  - 3 contract docs (taxonomy, A3 input, downstream reval)
  - 14 TuShare strategy tests
- final_note: No model was trained or promoted. All work cache-only; no quota-consuming TuShare calls made. Downstream milestone should consume the revalidation input contract for 3/5/10d large-cap low-control-proxy revalidation.

### MS-R0-001

- milestone_id: MS-R0-001
- title: 选股侧重构
- purpose: 清除无方法论的旧选股方式，以多维度评分作为唯一选股底座，建立"策略自包含 + 三层独立"的模块架构。
- status: completed
- milestone_kind: goal-driven
- priority: 4
- depends_on_milestones: MS-S2-001
- created_by: programmer-confirmed-codex
- created_at: 2026-06-22T15:15:00+08:00
- completed_at: 2026-06-23T00:00:00+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted
- worktracks: WT-R0-A1 (铲平), WT-R0-A2 (架子), WT-R0-A3 (落成), WT-R0-A4 (文档) — 4/4 completed
- branch: milestone/MS-S2-001-stock-pool-stratification (shared with MS-S2-001; commit 98ef372)
- acceptance_criteria: 6/6
- completion_signals: 8/8
- pytest: 402/402
- updated: 2026-06-23T00:00:00+08:00
- updated_by: codex-with-programmer-acceptance
- artifact_path: .servo/milestone/MS-R0-001.md
- key_artifacts:
  - stock_pools/base.py (StockPoolStrategy ABC + PoolCandidate)
  - stock_pools/low_manipulation/strategy.py (LowManipulationStrategy)
  - stock_pools/low_manipulation/config.toml
  - docs/modules/stock_pool_maintenance_guide.md
  - configs/stock_pools/custom_low_manipulation_v1 (唯一的 registry 池)
- final_note: 选股层从四套方法收敛为唯一方法论。三层架构建立。Pipeline 层实验配置仍引用旧池，留给下个 milestone 处理。

### MS-S1-001

- milestone_id: MS-S1-001
- title: 主线三头预测可信度评估与报告契约
- purpose: 先判断 `pred_3d` / `pred_5d` / `pred_10d` 三个主线预测头本身是否有稳定预测能力，并把防伪检查与报告契约固化为后续训练优化前的执行门禁。
- status: completed
- milestone_kind: goal-driven
- priority: 2
- depends_on_milestones: MS-S0-001
- created_by: programmer-confirmed-harness
- created_at: 2026-06-12T10:01:18+08:00
- completed_at: 2026-06-17T14:00:13+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted_with_residual_risk
- updated: 2026-06-17T14:00:13+08:00
- updated_by: harness-skill
- artifact_path: .servo/milestone/MS-S1-001.md
- final_report: .servo/worktrack/S1-A5-final-three-head-acceptance-report.md
- post_ms_s1_direction_note: .servo/repo/post-ms-s1-direction-note.md
- worktrack_list:
  - WT-S1-A1 (done): random-label 防伪
    - result: random-label smoke passes 3d/5d/10d on quick8 OOS.
    - residual_risk: quick8 smoke is not promotion evidence; h5 time-reverse sanity still failed.
  - WT-S1-A2 (done): 行业 / 市值中性化评估
    - result: industry-neutral smoke is runnable and turns 5d/10d positive baseline evidence negative/cautionary.
    - residual_risk: size neutralization remains blocked by missing size input.
  - WT-S1-A3 (done): XGBoost 报告契约补齐
    - result: future XGBoost reports can emit `evaluation_protocol` and `comparison_panel`.
    - residual_risk: historical fastpilot XGB report still lacks OOS parquet path.
  - WT-S1-A4 (done): 同窗三头评估 smoke
    - result: same-window strict daily-CS smoke is blocked by missing fastpilot OOS parquet paths.
    - residual_risk: no accepted same-window model comparison metrics from current artifacts.
  - WT-S1-A5 (done): 三头预测验收报告
    - result: final report concludes `continue-research / blocked-by-data`.
    - residual_risk: no `pred_3d`, `pred_5d`, `pred_10d`, or `alpha_score` signal is promoted.
- final_note: No model is promoted; next research should split stock-pool stratification and large-cap low-control-probability 3/5/10d revalidation into separate Milestones.

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
