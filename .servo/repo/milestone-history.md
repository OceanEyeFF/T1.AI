---
title: "Milestone History"
artifact_type: "milestone-history"
updated: "2026-07-14T20:11:00+08:00"
updated_by: "cursor-with-programmer-acceptance"
---

# Milestone History

> Completed and superseded milestones are moved here from `.servo/repo/milestone-backlog.md`.

## Completed

### MS-T1-001

- milestone_id: MS-T1-001
- title: 广义测试体系清理（T-heavy）
- purpose: >
  对 tests/ 做架构级重写（分层、fixtures、markers、CI fast/full）；经批准退役死测；
  温和 cov 门禁；完成后再启动 MS-R4
- status: completed
- milestone_kind: goal-driven
- priority: 3
- depends_on_milestones: MS-R3-001
- precedes: MS-R4-001
- created_by: programmer
- created_at: 2026-07-14T17:24:00+08:00
- activated_at: 2026-07-14T17:24:00+08:00
- completed_at: 2026-07-14T20:11:00+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted
- updated: 2026-07-14T20:11:00+08:00
- updated_by: cursor-with-programmer-acceptance
- artifact_path: .servo/milestone/MS-T1-001.md
- pre_milestone_intake_review: .servo/repo/MS-T1-001-pre-milestone-intake-review.md
- decisions_locked: D1=C, D2=S1, D3=Del-yes, D4=Acc-balanced, D5=confirmed
- worktrack_list:
  - WT-T1-A1 (done): inventory + Arch-v1 + cov floor 建议
  - WT-T1-A2 (done): Del-A1 冗余 deployment structure 测例删除
  - WT-T1-A3 (done): Arch-v1 分层搬迁 + conftest/pythonpath
  - WT-T1-A4 (done): markers + fast/full/cov76 + testing guide + R4 handoff
- completion_signals: 5/5
- acceptance_criteria: 5/5
- pytest_full: 396/396
- pytest_fast: 277 passed / 119 deselected
- cov_total: ~78%; fail_under: 76
- branch: milestone/MS-T1-001-test-suite-rewrite
- merge_commit: eed3e24e154f03b66f5209cff542eb3a379708d2 on develop
- key_artifacts:
  - tests/{unit,integration,contract,support}/
  - docs/guides/testing_guide.md
  - scripts/run_tests_{fast,full,cov}.sh
  - .servo/worktrack/WT-T1-A1-inventory.md
  - .servo/worktrack/WT-T1-A4-r4-handoff.md
- final_note: >
  测试体系 T-heavy 清理完成并合入 develop。下一主线为 MS-R4-001（TuShare 数据湖）；
  新测例应按 Arch-v1 落入对应分层，勿恢复扁平 tests/ 根目录堆放。

### MS-R3-001

- milestone_id: MS-R3-001
- title: 旧文件深度清理
- purpose: 以治理模式（inventory→批准→分批删除）按 P3 偏瘦身默认分类清除过期文档/脚本/checkpoint；T2 分流 R2 遗留 2 fail；为后续测试体系与数据湖腾出干净仓库面
- status: completed
- milestone_kind: goal-driven
- priority: 2
- depends_on_milestones: MS-R2-001
- created_by: programmer
- created_at: 2026-06-23T03:00:00+08:00
- activated_at: 2026-07-14T11:35:00+08:00
- completed_at: 2026-07-14T17:24:00+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted
- updated: 2026-07-14T17:24:00+08:00
- updated_by: cursor-with-programmer-acceptance
- artifact_path: .servo/milestone/MS-R3-001.md
- pre_milestone_intake_review: .servo/repo/MS-R3-001-pre-milestone-intake-review.md
- worktrack_list:
  - WT-R3-A1 (done): inventory + 引用审计 + 2-fail 定性
  - WT-R3-A2 (done): 按批准清单分批删除/退役
  - WT-R3-A3 (done): F1/F2 路径修复；pytest 397/397
- completion_signals: 5/5 (CS5 N/A — no R4 defer)
- acceptance_criteria: 5/5
- pytest: 397/397
- branch: milestone/MS-R3-001-deep-cleanup
- merge_commit: 296318baeb27d4271986e51852ba4ade0abe0f02 on develop
- key_artifacts:
  - .servo/worktrack/WT-R3-A1-inventory.md
  - .servo/worktrack/WT-R3-A2-execution-log.md
  - .servo/worktrack/WT-R3-A3-closeout.md
  - stock_pool registry relative-path fix + market_state default registry `inputs/pools`
- final_note: >
  旧文件治理清理完成并合入 develop。R2 遗留 2 fail 均在 R3 侧修复，无 R4 defer。
  广义测试体系清理移交 MS-T1-001（先于 MS-R4-001）。

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

### MS-R1-001

- milestone_id: MS-R1-001
- title: 模型层提取与统一治理
- purpose: 将散落在脚本和 monolithic 文件中的模型代码提取为统一 ModelABC 接口的自包含实现
- status: completed
- milestone_kind: goal-driven
- priority: 4
- depends_on_milestones: MS-R0-001
- created_by: codex-with-programmer-confirmation
- created_at: 2026-06-23T00:00:00+08:00
- completed_at: 2026-06-23T02:00:00+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted
- updated: 2026-06-23T02:00:00+08:00
- updated_by: codex-with-programmer-acceptance
- artifact_path: .servo/milestone/MS-R1-001.md
- pre_milestone_intake_review: .servo/repo/MS-R1-001-pre-milestone-intake-review.md
- worktrack_list:
  - WT-R1-A1 (done): 从 develop 提取 LSTM/XGB 源码并审计差异
  - WT-R1-A2 (done): 定义 ModelABC 接口 + 模型 registry
  - WT-R1-A3 (done): Transformer 重构
  - WT-R1-A4 (done): LSTM 统一实现
  - WT-R1-A5 (done): XGBoost 封装实现
  - WT-R1-A6 (done): 下游脚本解耦
  - WT-R1-A7 (done): 维护文档
  - WT-R1-A8 (done): 铲平旧实现
- completion_signals: 10/10 (100%)
- acceptance_criteria: 6/6 (100%)
- pytest: 397/397
- branch: milestone/MS-R0-R1-stock-model-governance
- commit: 5da7cde
- key_artifacts:
  - models/base.py (ModelABC + TrainingData/PredictionData/Result)
  - models/registry.py (register_model/create_model/create_model_from_toml)
  - models/transformer/ (ModelABC wrapper + _mtl_transformer backend + config.toml)
  - models/lstm/ (MtlLSTM + LSTMModel + config.toml)
  - models/xgboost/ (XGBoostModel + XgbConfig + config.toml)
  - models/transformer.py (backward-compat re-export layer)
  - docs/guides/models_maintenance_guide.md
- final_note: 3 models unified under ModelABC interface with registry. Backward-compat preserved. No model retrained.

### MS-R2-001

- milestone_id: MS-R2-001
- title: Repo 目录排布重构 — inputs/workspace/outputs 三区模型
- purpose: 将一级目录从 21 收敛到 8，建立三区模型，推倒重建 docs/，固化 WORK_RULES
- status: completed
- milestone_kind: goal-driven
- priority: 3
- depends_on_milestones: MS-R1-001
- created_by: codex-with-programmer-confirmation
- created_at: 2026-06-23T02:00:00+08:00
- completed_at: 2026-06-23T04:00:00+08:00
- accepted_by: OceanEyeFF
- acceptance_verdict: accepted
- updated: 2026-06-23T04:00:00+08:00
- updated_by: codex-with-programmer-acceptance
- artifact_path: .servo/milestone/MS-R2-001.md
- pre_milestone_intake_review: .servo/repo/MS-R2-001-pre-milestone-intake-review.md
- worktrack_list:
  - WT-R2-A1 (done): 全量路径引用审计 → change-impact map
  - WT-R2-A2 (done): inputs/ 区落成
  - WT-R2-A3 (done): workspace/ 区落成
  - WT-R2-A4 (done): outputs/ 区落成
  - WT-R2-A5 (done): 历史残留清理
  - WT-R2-A6 (done): 路径引用全量修复 (~60 files)
  - WT-R2-A7 (done): .gitignore + __pycache__
  - WT-R2-A8 (done): pytest 回归 (395/397)
  - WT-R2-A9 (done): 文档跟进 — README/CLAUDE
  - WT-R2-A10 (done): docs/ 推倒重建 + 空壳 README + WORK_RULES
  - WT-R2-A11 (done): 根 README 重写 + CLAUDE.md 移除
- completion_signals: 11/11 (100%)
- pytest: 395/397 (2 fail = 旧数据集路径, 后续 Milestone 修复)
- branch: milestone/MS-R2-001-repo-restructure
- key_artifacts:
  - 一级目录: 21 → 8
  - docs/ 重建为 architecture/ reference/ guides/ research/ archive/
  - docs/WORK_RULES.md (9 章全局工作规则)
  - docs/architecture/ (4 docs: pipeline_flow, xyz_test_matrix, model_registry, repo_structure_guide)
  - docs/reference/ (2 docs: data_contract, stock_pool_schema)
  - docs/guides/ (3 docs: daily_pipeline_ops, stock_pool_maintenance, models_maintenance)
  - 7 空壳目录 README.md
  - CLAUDE.md 已删除
  - README.md 重写
- final_note: 三区模型已落成。experiments/ models/ logs/ output/ data/ configs/ 不再作为一级目录。激进清理删除了所有旧 AkShare 产物。2 个测试失败依赖旧数据集路径，待 MS-R3-001 / MS-R4-001 解决。

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
