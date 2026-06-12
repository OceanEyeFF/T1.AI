# Research 文档

这一层放研究方法、评估工作流、训练策略和当前实验结论。

适合在这里回答的问题：

- 当前默认训练与评估口径是什么
- 主线模型与 `1d` 独立线的研究节奏分别是什么
- 某个实验结论是否已经足够稳定
- 伪信号和泄漏风险在哪里

## 推荐阅读顺序

1. [research_checklist.md](research_checklist.md)
2. [1d_independent_model_execution_strategy_20260309.md](1d_independent_model_execution_strategy_20260309.md)
3. [mainline_3510d_evaluation_gate_protocol.md](mainline_3510d_evaluation_gate_protocol.md)
4. [daily_cs_eval_workflow.md](daily_cs_eval_workflow.md)
5. [数据窗口结构的区别.md](%E6%95%B0%E6%8D%AE%E7%AA%97%E5%8F%A3%E7%BB%93%E6%9E%84%E7%9A%84%E5%8C%BA%E5%88%AB.md)
6. [多头输出和数据切分.md](%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md)
7. [警惕伪信号.md](%E8%AD%A6%E6%83%95%E4%BC%AA%E4%BF%A1%E5%8F%B7.md)
8. [1d_independent_model_research_plan.md](1d_independent_model_research_plan.md)
9. [future_roadmap_suggestions.md](future_roadmap_suggestions.md)
10. [multilevel_tuning_plan_20260307.md](multilevel_tuning_plan_20260307.md)
11. [mainline_3510d_development_retrospective_20260310.md](mainline_3510d_development_retrospective_20260310.md)

## 文档分组

- [research_checklist.md](research_checklist.md)：研究主清单与门禁
- [1d_independent_model_execution_strategy_20260309.md](1d_independent_model_execution_strategy_20260309.md)：`1d` 独立研究线的执行顺序与数据节奏
- [1d_independent_model_research_plan.md](1d_independent_model_research_plan.md)：`1d` 补充研究提纲
- [mainline_3510d_evaluation_gate_protocol.md](mainline_3510d_evaluation_gate_protocol.md)：主线 `3d/5d/10d` 可信评估和防伪门禁协议
- [daily_cs_eval_workflow.md](daily_cs_eval_workflow.md)：Daily-CS 评估流程
- [数据窗口结构的区别.md](%E6%95%B0%E6%8D%AE%E7%AA%97%E5%8F%A3%E7%BB%93%E6%9E%84%E7%9A%84%E5%8C%BA%E5%88%AB.md)：训练窗口与重训策略
- [多头输出和数据切分.md](%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md)：默认多头配置与固定切分数值
- [警惕伪信号.md](%E8%AD%A6%E6%83%95%E4%BC%AA%E4%BF%A1%E5%8F%B7.md)：伪信号与回测偏差风险
- [future_roadmap_suggestions.md](future_roadmap_suggestions.md)：最近一轮研究路线校准
- [multilevel_tuning_plan_20260307.md](multilevel_tuning_plan_20260307.md)：LSTM / XGBoost 多级别自动微调方案
- [mainline_3510d_development_retrospective_20260310.md](mainline_3510d_development_retrospective_20260310.md)：本轮 `3d/5d/10d` 主模型分支开发复盘

## 当前默认研究口径

- 默认主线仍是 `3d/5d/10d`，不是 `1d`。
- `1d` 当前只作为独立短周期研究线推进，不进入默认主线打分。
- 默认推荐打分先把 `pred_3d/pred_5d/pred_10d` 聚合为单一 `alpha_score`，默认权重 `0.2 / 0.4 / 0.4`。
- 默认训练节奏仍以 `weekly retrain + daily inference + maturity-gated training pool + walk-forward evaluation` 为主。
- 多级微调仍采用配置文件驱动，但不能覆盖模型线边界规则。
- 任何 `1d` 结论进入默认流程前，都必须先同步到 `overview` / `modules` / `interfaces` 层。

## 历史实验

旧实验报告与旧消融文档已不再作为默认入口。
如需追溯历史过程，应从版本历史检索。

## 使用边界

- 研究层不直接改写接口层与执行层默认定义。
- 若研究结论已经成为当前默认口径，必须同步更新 [../README.md](../README.md)、[../../NEXT_STEPS.md](../../NEXT_STEPS.md) 或对应模块文档。
