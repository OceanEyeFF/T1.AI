# 文档清单（按颗粒度 + 状态标记）

更新时间：2026-03-11
说明：本清单按"粗颗粒 → 中颗粒 → 细颗粒 → 研究 → 任务 → 归档"列出仓库文档。

**状态标记：**
- `active` — 正在使用的基线文档
- `frozen` — 已冻结快照，不应修改
- `stale` — 可能过期，待确认
- `archived` — 已移入 archive/

---

## 1. 总入口

- `README.md` — `active` — 文档导航
- `INVENTORY.md` — `active` — 本清单

## 2. Overview

- `overview/README.md` — `active` — 层级导航
- `overview/doc_governance.md` — `active` — 文档命名与颗粒度规则
- `overview/doc_lifecycle_rules_20260311.md` — `active` — 文档生命周期、归档、权限规则
- `overview/merge_audit_checklist_20260311.md` — `active` — 跨分支合入审核标准（G1 产出）
- `overview/branch_consolidation_audit_20260311.md` — `frozen` — 分支整理审计快照
- `overview/post_mainline_sync_optimization_plan_20260311.md` — `active` — 主模型同步后优化计划
- `overview/dual_window_evaluation_baseline_20260311.md` — `active` — 双窗口评估基线
- `overview/config_and_artifact_naming_20260311.md` — `active` — 配置与实验产物命名/版本规范（G4 产出）
- `overview/shared_layer_inventory_20260311.md` — `active` — 1d/3d|5d|10d 公用层盘点（G3 产出）
- `overview/branch_baseline_conflict_analysis_20260311.md` — `active` — 分支与基线文档冲突分析（治理期后）
- `overview/topic_maps.md` — `active` — 主题映射索引
- `overview/topic_gaps.md` — `active` — 主题缺口索引
- `overview/future_state_blueprint.md` — `active` — 项目未来蓝图
- `overview/project_update_plan_2026Q1.md` — `active` — 2026Q1 项目更新计划
- `overview/ai_finance_external_benchmark_2026.md` — `active` — AI 金融外部对标

根目录补充入口：

- `../README.md` — `active` — 项目总入口
- `../NEXT_STEPS.md` — `active` — 当前执行入口
- `../ROADMAP.md` — `active` — 长期路线入口

## 3. Modules

- `modules/README.md` — `active` — 层级导航
- `modules/system_io_and_architecture_spec.md` — `active` — 系统 I/O 与架构分层
- `modules/model_line_boundaries_1d_vs_3510d_20260309.md` — `active` — 模型线边界
- `modules/stock_pool_module_baseline_20260311.md` — `active` — 股票池模组基线
- `modules/stock_pool_module_development_plan_20260311.md` — `active` — 股票池模组开发计划
- `modules/stock_pool_registry_baseline_20260311.md` — `active` — 股票池 Registry 基线
- `modules/production_scheduler.md` — `active` — 生产调度
- `modules/data_sources.md` — `active` — 数据源
- `modules/news_sources.md` — `active` — 新闻数据源

## 4. Interfaces

- `interfaces/README.md` — `active` — 层级导航
- `interfaces/setup.md` — `active` — 环境配置
- `interfaces/constraints.md` — `active` — 交易约束
- `interfaces/objectives.md` — `active` — 验收目标
- `interfaces/data_contract.md` — `active` — 数据契约
- `interfaces/protocol.md` — `active` — 交易协议

## 5. Research

- `research/README.md` — `active` — 层级导航
- `research/research_checklist.md` — `active` — 研究主清单与门禁
- `research/1d_independent_model_execution_strategy_20260309.md` — `active` — 1d 独立研究执行策略
- `research/1d_independent_model_research_plan.md` — `active` — 1d 研究提纲
- `research/daily_cs_eval_workflow.md` — `active` — Daily-CS 评估流程
- `research/future_roadmap_suggestions.md` — `active` — 研究路线校准（当前版）
- `research/mainline_3510d_model_development_plan_20260310.md` — `active` — 主模型开发计划
- `research/mainline_3510d_development_retrospective_20260310.md` — `frozen` — 主模型开发复盘快照
- `research/multilevel_tuning_plan_20260307.md` — `active` — 多级微调方案
- `research/数据窗口结构的区别.md` — `active` — 训练窗口与重训策略
- `research/多头输出和数据切分.md` — `active` — 多头配置与数据切分
- `research/警惕伪信号.md` — `active` — 伪信号风险
- `research/选股池方法论.md` — `active` — 选股池方法论
- `research/高频与日频模型分析.md` — `active` — 高频与日频模型分析
- `research/A股短中线预测IC提升方案：诊断与可执行研究计划.pdf` — `frozen` — 外部研究参考
- `research/A股短中线多头预测的 IC 提升与评估体系可执行研究计划.pdf` — `frozen` — 外部研究参考

## 6. Branch Tasks

- `branch_tasks/README.md` — `active` — 分支任务索引
- `branch_tasks/develop.md` — `active` — develop 分支任务
- `branch_tasks/develop_governance_backlog_20260311.md` — `active` — develop 治理总清单
- `branch_tasks/feature_model_d1_research.md` — `active` — 1d 研究分支任务
- `branch_tasks/feature_execution_layer_v2.md` — `active` — 执行层分支任务
- `branch_tasks/feature_model_3d_5d_10d_head.md` — `frozen` — 3d/5d/10d 分支任务（已同步/待归档）

## 7. Archive

- `archive/README.md` — `active` — 归档索引
- `archive/long_term/README.md` — `active` — 长期归档索引
- `archive/short_term/README.md` — `active` — 短期归档索引
- `archive/long_term/future_roadmap_suggestions_20260307.md` — `archived` — 旧版路线建议
- `archive/g1_validation_20260311/g1_validation_plan_20260311.md` — `archived` — G1 验证方案
- `archive/g1_validation_20260311/g1_validation_exec_guide.md` — `archived` — G1 验证执行指引
- `archive/g1_validation_20260311/g1_validation_findings.md` — `archived` — G1 验证发现
- `archive/g1_validation_20260311/develop_reviewer_notes.md` — `archived` — G1 develop 复核记录
- `archive/g1_validation_20260311/execution_layer_v2_self_check.md` — `archived` — G1 自查记录
- `archive/ic_reform_completed_20260305/IC评估体系最小改造清单与计划.md` — `archived` — IC 改造清单
- `archive/ic_reform_completed_20260305/IC评估体系改造Prompt包.md` — `archived` — IC 改造 Prompt 包
