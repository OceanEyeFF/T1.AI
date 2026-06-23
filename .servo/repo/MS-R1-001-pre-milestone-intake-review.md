---
title: "MS-R1-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
target_milestone_id: "MS-R1-001"
created: "2026-06-23T00:00:00+08:00"
created_by: "codex"
---

# MS-R1-001 Pre-Milestone Intake Review

## Intake Status

```yaml
intake_status: "ready"
programmer_confirmed: true
ready_for_init_milestone: true
confirmation_required: false
intake_skipped: false
skip_reason: null
accepted_risk: []
residual_risk_accepted: false
accepted_residual_risk: []
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
```

## Request Summary

```yaml
request_summary: >
  用户要求对模型层（src/ashare_lab/models/）执行与 stock_pools/ 同等的治理重构：
  建立 ModelABC 统一接口、模型注册表、自包含文件夹结构。
  当前模型代码存在三个问题：Transformer 是 400 行 monolithic 文件；
  LSTM 的 MtlLSTM 类在 3 个脚本中各有内联定义（且只存在于 develop 分支）；
  XGBoost 完全没有封装类，裸用 xgb.XGBRegressor。
  本 Milestone 从 develop 分支提取 LSTM/XGB 源码，统一为 ModelABC 实现，
  重构 Transformer，解耦下游脚本的硬编码 import。
```

## Observed Facts

`observed_facts`:

- `src/ashare_lab/models/transformer.py` 是唯一的正式模型文件（~400 行，含 MTLTransformer + TransformerConfig + PositionalEncoding + loss + factory）
- LSTM 模型 `class MtlLSTM(nn.Module)` 在 develop 分支的 3 个脚本中内联定义：`scripts/run_lstm_dim16_vs_dim19_market.py:70`、`scripts/run_lstm_rolling_retrain_dim19_regime.py:396`、`scripts/run_lstm_walkforward_sign_calibration.py:61`
- XGBoost 无封装类，脚本直接调用 `xgb.XGBRegressor()`
- 5 个脚本硬编码 `from ashare_lab.models.transformer import create_mtl_model`：train_mtl.py、train_model.py、evaluate_model.py、daily_pipeline.py、generate_daily_recommendations.py
- experiment configs 引用 lstm/xgb 但无对应 src 模型代码
- `src/ashare_lab/training/trainer.py` 名义上接受 nn.Module 但只测过 Transformer
- MS-R0-001 已完成（选股层治理），提供了统一的 StockPoolStrategy 接口作为参考模式

## Inferred Assumptions

`inferred_assumptions`:

- 3 份 MtlLSTM 副本的核心逻辑相似，可以收敛为一个统一实现
- XGBoost 需要的接口（train/predict/save/load）与 Transformer/LSTM 的 ModelABC 兼容
- 下游脚本的接口变更可通过统一 import 路径适配，不改变训练/评估逻辑

## Unknowns

`unknowns`:

- 3 份 MtlLSTM 之间的确切差异需在 R1-A1 审计中确认
- XGBoost 的 save/load 是否需要支持 GPU（当前模型不需要 GPU）
- `scripts/auto_tune_xgb.py` 通过 subprocess 调用脚本，重构后需验证兼容性

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: "D1"
    decision: "是否保留旧的内联模型定义（脚本内的 MtlLSTM 副本）作为参考，还是彻底删除？"
    why_required: "铲平范围影响 R1-A8 执行方式"
    blocks_ready: false
  - id: "D2"
    decision: "XGBoost/LSTM 是否需要支持 GPU 训练？"
    why_required: "ModelABC 接口设计需要确定设备抽象层"
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: "R1"
    kind: "scope_creep"
    severity: "medium"
    description: "从 develop 分支提取代码后，脚本适配可能导致超过 5 个文件的改动"
  - id: "R2"
    kind: "compatibility"
    severity: "low"
    description: "trainer.py 与 ModelABC 的耦合可能需要在 R1-A3 中同步调整"
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  gate_id: "MS-R1-001-intake"
  target_repo: "T1.AI"
  target_milestone_id: "MS-R1-001"
  trigger_source: "pre-milestone-intake"
  entry_verdict: "clear"
  scanner_evidence_ref: null
  complexity_signals: []
  operator_safety_policy:
    docker_compose_permission: "not_applicable"
    database_migration_permission: "not_applicable"
    deploy_network_permission: "not_applicable"
    destructive_cleanup_permission: "requires_approval"
    secrets_policy: "not_applicable"
    protected_paths: ["src/ashare_lab/models/", "src/ashare_lab/training/"]
    protected_branches: ["develop"]
    allowed_high_risk_command_modes: "pending_programmer_confirmation"
  dialog_review_questions: []
  milestone_blocking_decision:
    - "allow_create"
    - "allow_upsert"
    - "allow_activate"
    - "allow_derive_worktrack"
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: "not_needed"
    recommendation_type: "N/A"
    suggested_title: ""
    suggested_purpose: ""
    recommendation_reason: ""
    temporary_understanding_ref: null
    evidence_refs: []
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs: []
```

## Open Questions

无阻塞问题。用户在对话中已确认 milestone brief（8 个 worktrack），scope 和 non-goals 明确。

## Recommended Answers

```yaml
recommended_answers:
  D1:
    answer: "R1-A8 铲平时彻底删除脚本中的内联模型定义，不保留副本"
    impact_if_accepted: "代码干净，无歧义。如需回溯可从 git history 恢复"
    impact_if_rejected: "保留副本造成维护负担，新人困惑哪个是正确版本"
  D2:
    answer: "当前不需要 GPU 支持；ModelABC 接口保留 device 参数（默认 'cpu'），为未来扩展留空间"
    impact_if_accepted: "接口简洁，无 GPU 依赖复杂性"
    impact_if_rejected: "如果后续需要 GPU，需重新设计接口"
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - 从 develop 分支提取 LSTM/XGBoost 源码
    - 定义 ModelABC 抽象基类 + 模型 registry
    - Transformer 重构为自包含文件夹
    - LSTM 统一实现（收敛 3 份脚本差异）
    - XGBoost 封装实现
    - 下游脚本解耦（统一 import 路径）
    - 铲平旧的内联模型定义和裸 xgb 调用
    - 维护文档
  out_of_scope:
    - 不修改 Trainer 训练逻辑
    - 不调整超参数
    - 不训练新模型
    - 不修改实验配置中的旧池子引用
    - 不修改数据层 / 数据源
    - 不触发 TuShare 或其他外部 API 调用
```

## Non Goals

```yaml
non_goals:
  - 不追求模型性能提升
  - 不引入新模型架构
  - 不改变训练/评估 pipeline 的控制流
  - 不修改 experiment configs 中的 stock_pool_id
```

## Acceptance Signals

```yaml
acceptance_signals:
  - transformer_refactored: Transformer 拆分为 model.py + config.toml + checkpoints/，适配 ModelABC
  - lstm_unified: 3 份脚本内联 MtlLSTM 收敛为一个 models/lstm/model.py 实现
  - xgboost_wrapped: XGBoost 有正式封装类，实现 ModelABC 接口
  - model_abc_defined: ModelABC 抽象基类定义完成（train/predict/save/load）
  - registry_ready: 模型注册表可用（config → 实例）
  - downstream_adapted: 5 个下游脚本统一使用新 import 路径
  - old_code_removed: 脚本内联模型定义、裸 xgb 调用已清除
  - docs_written: models/ 维护文档已编写
  - tests_pass: 现有 pytest 全部通过
  - trainer_unaffected: Trainer 功能不受影响
```

## Suggested Milestone Brief

```yaml
suggested_milestone_brief:
  title: "MS-R1-001 模型层提取与统一治理"
  purpose: >
    将散落在脚本和 monolithic 文件中的模型代码（Transformer/LSTM/XGBoost）
    提取为统一 ModelABC 接口的自包含实现，建立模型注册表，
    解耦下游脚本的硬编码依赖。
  milestone_kind: "goal-driven"
  priority: 4
  depends_on_milestones: ["MS-R0-001"]
  candidate_worktracks:
    - worktrack_id: "WT-R1-A1"
      title: "从 develop 提取 LSTM/XGB 源码 + 审计 MtlLSTM 差异"
      purpose: "提取 3 份 MtlLSTM 副本和 XGBoost 脚本，分析差异，确认可收敛范围"
    - worktrack_id: "WT-R1-A2"
      title: "定义 ModelABC 接口 + 模型 registry"
      purpose: "建立模型抽象基类和注册表，设定统一接口契约"
    - worktrack_id: "WT-R1-A3"
      title: "Transformer 重构"
      purpose: "从 transformer.py 拆出 model.py + config.toml，适配 ModelABC"
    - worktrack_id: "WT-R1-A4"
      title: "LSTM 统一实现"
      purpose: "收敛 3 份脚本差异为一个 models/lstm/model.py 实现"
    - worktrack_id: "WT-R1-A5"
      title: "XGBoost 封装实现"
      purpose: "封装 xgb.XGBRegressor 为 XGBoostModel(ModelABC)"
    - worktrack_id: "WT-R1-A6"
      title: "下游脚本解耦"
      purpose: "5 个脚本统一使用新 import 路径替代硬编码"
    - worktrack_id: "WT-R1-A7"
      title: "维护文档"
      purpose: "编写 models/ 模块维护指南"
    - worktrack_id: "WT-R1-A8"
      title: "铲平旧实现"
      purpose: "清除脚本内联模型定义、裸 xgb 调用、旧 import 路径"
  completion_signals:
    - transformer_refactored
    - lstm_unified
    - xgboost_wrapped
    - model_abc_defined
    - registry_ready
    - downstream_adapted
    - old_code_removed
    - docs_written
    - tests_pass
    - trainer_unaffected
  acceptance_criteria:
    - "models/ 下每种模型是自包含子文件夹（model.py + config.toml）"
    - "ModelABC 定义在 models/base.py，所有模型继承它"
    - "模型注册表可通过 config 创建任意模型实例"
    - "5 个下游脚本不再硬编码具体模型类的 import"
    - "脚本中不再存在内联模型定义"
    - "现有 pytest 全部通过"
  completion_threshold_pct: 100
```

## Confirmation State

```yaml
confirmation_state:
  confirmation_required: false
  programmer_confirmed: true
  confirmed_answers: ["D1: 彻底删除旧内联定义", "D2: 当前不需要 GPU 支持"]
  residual_risk: []
  residual_risk_accepted: false
  accepted_residual_risk: []
```

## Handoff To Init Milestone

```yaml
handoff_to_init_milestone:
  allowed: true
  handoff_reason: "programmer confirmed milestone brief with 8 worktracks; no blocking questions remain"
  required_inputs: []
  blocked_by: []
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  target_milestone_id: "MS-R1-001"
  review_status: "effective_pass"
  milestone_review_count_increment: 1
  latest_review_status: "effective_pass"
  latest_review_checkpoint: "MS-R1-001-intake-2026-06-23T00:00:00+08:00"
  latest_review_ref: ".servo/repo/MS-R1-001-pre-milestone-intake-review.md"
  effective_review_pass: true
  review_invalidated_by: {}
  blockers: []
```
