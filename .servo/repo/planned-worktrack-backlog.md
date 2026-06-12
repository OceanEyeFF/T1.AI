---
title: "Planned Worktrack Backlog"
artifact_type: "planned-worktrack-backlog"
updated: "2026-06-12T10:01:18+08:00"
updated_by: "harness-skill"
---

# Planned Worktrack Backlog

> Planned Worktracks are listed here before WorktrackScope.Init. Closed and resolved worktracks remain in `.servo/repo/worktrack-backlog.md`, whose contract only accepts `done / deferred / blocked / resolved`.

## Planned

### WT-S1-A1

- worktrack_id: WT-S1-A1
- milestone_id: MS-S1-001
- status: planned
- node_type: test/tooling
- title: random-label 防伪
- abstract_goal: 检查模型是否能在假标签上也得到好结果，防止泄漏或过拟合幻觉。
- concrete_operations: 添加或固化 random-label 防伪入口；让真实 OOS 预测与随机标签基线走同一评估口径；输出机器可读 pass/fail/continue-research 证据。
- model_impact: 如果随机标签也能产生高 IC / RankIC，说明模型或评估流程存在泄漏、过拟合或样本选择问题，三头预测不能被视为可信。
- quant_impact: 防止把偶然或泄漏产生的排序结果当成选股信号，避免后续 Top-N 推荐和回测被假好结果带偏。
- acceptance: random-label check can run locally in `py311-private`; report records per-horizon outcome and blocks promotion when random baseline looks too good.
- out_of_scope: long model training, alpha_score optimization, provider calls, commit/push.

### WT-S1-A2

- worktrack_id: WT-S1-A2
- milestone_id: MS-S1-001
- status: planned
- node_type: test/evaluation
- title: 行业 / 市值中性化评估
- abstract_goal: 判断三头预测是否只是行业或大小盘风格暴露，而不是真正的个股排序能力。
- concrete_operations: 定义行业 / 市值输入契约；对预测和标签做最小中性化或分组残差评估；输出中性化前后 IC / RankIC 对比。
- model_impact: 如果中性化后信号消失，说明模型可能主要学到行业轮动或市值风格，后续优化应转向特征/标签/股票池诊断。
- quant_impact: 避免策略实质上变成隐式押行业或大小盘，降低组合集中暴露和回测误判风险。
- acceptance: neutralization gate has documented inputs/outputs and a runnable minimal check or an explicit blocked-by-data report.
- out_of_scope: complex Barra-style risk model, production risk engine, alpha_score promotion, live trading.

### WT-S1-A3

- worktrack_id: WT-S1-A3
- milestone_id: MS-S1-001
- status: planned
- node_type: tooling/report-contract
- title: XGBoost 报告契约补齐
- abstract_goal: 让 XGBoost 与 LSTM 可以用同一报告协议公平比较。
- concrete_operations: 检查 XGBoost 报告生成路径；补齐 `evaluation_protocol`、OOS 窗口、股票池、指标、comparison panel 等字段；确保 `compare_ic_reports.py --check-protocol` 可消费。
- model_impact: 避免不同模型各用各的报告格式导致比较不可解释，为后续 LSTM / XGBoost / 轻量融合比较提供共同基线。
- quant_impact: 防止因为报告口径不同而误选模型，确保后续选股信号比较建立在同一 OOS 和同一指标上。
- acceptance: focused tests cover XGBoost report contract and protocol check; smoke report passes the shared checker.
- out_of_scope: full XGBoost retraining, model selection, alpha_score optimization.

### WT-S1-A4

- worktrack_id: WT-S1-A4
- milestone_id: MS-S1-001
- status: planned
- node_type: test/evaluation
- title: 同窗三头评估 smoke
- abstract_goal: 小规模验证 `pred_3d` / `pred_5d` / `pred_10d` 可以在同一 OOS 窗口、同一报告结构下比较。
- concrete_operations: 选择已有或轻量生成的 smoke 报告；运行 audit/compare/sanity 检查；逐 horizon 输出 IC / RankIC、月度稳定性和失败原因。
- model_impact: 先证明评估链路是通的，再决定是否值得花时间做真实训练优化。
- quant_impact: 避免长训后才发现报告不能比、窗口不一致或指标不可解释，降低研究迭代成本。
- acceptance: smoke comparison runs in `py311-private` without long training; report explicitly states smoke evidence is not performance breakthrough.
- out_of_scope: full-size training, production recommendation, model promotion.

### WT-S1-A5

- worktrack_id: WT-S1-A5
- milestone_id: MS-S1-001
- status: planned
- node_type: research/report
- title: 三头预测验收报告
- abstract_goal: 汇总每个 horizon 的可信度结论，回答三头预测是否值得进入后续训练优化。
- concrete_operations: 汇总 A1-A4 evidence；逐一判断 `pred_3d`、`pred_5d`、`pred_10d` 的 go / no-go / continue-research；记录失败原因更可能来自数据、标签、特征、模型还是评估契约。
- model_impact: 给下一轮训练优化提供明确入口：优化哪个头、为什么优化、先修数据/标签还是先调模型。
- quant_impact: 明确哪些预测头不应进入选股或决策研究，避免把不可信 horizon 混入后续策略评估。
- acceptance: final report contains per-horizon evidence table, anti-cheat outcomes, model/quant interpretation, and next-milestone recommendation.
- out_of_scope: alpha_score promotion, decision model implementation, live trading.
