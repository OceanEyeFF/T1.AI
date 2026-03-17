# 分支整理与基线对齐审计（2026-03-11）

## 1. 审计范围

本次审计覆盖当前仓库内的 4 条本地工作分支与对应 worktree：

| 分支 | HEAD | worktree | 说明 |
|------|------|----------|------|
| `develop` | `e7558c4` | `/home/oceaneye/github/T1.AI` | 当前集成基线 |
| `feature/execution-layer-v2` | `bb52e50` | `/home/oceaneye/github/T1.AI-exec` | 执行层 Phase 0 方案分支 |
| `feature/model-3d-5d-10d-head` | `f6cb27a` | `/home/oceaneye/github/T1.AI-model-main` | `3d/5d/10d` 主模型分支 |
| `feature/model-d1-research` | `2ed1ed6` | `/home/oceaneye/github/T1.AI-model-d1` | `1d` 独立研究分支 |

补充观察：

- `worktree-execution-layer` 指向 `develop`，不是独立开发线。
- `feature/execution-layer-v2` 与 `feature/model-d1-research` worktree 中存在未跟踪目录 `.serena/`，不属于本次审计内容。

---

## 2. 当前分支画像

## 2.1 `feature/execution-layer-v2`

### 改动规模

- 相对 `develop` 独有提交：5
- 主要变更：11 个文件，约 `2308` 行新增
- 变更类型：几乎全部为文档与设计方案

### 主要产出

- 执行层分支计划：
  - `docs/research/execution_layer_branch_plan_20260309.md`
- 执行层 Phase 0-3 实施方案：
  - `docs/technical/execution_layer_phase_implementation.md`
- PortfolioManager 伪代码与日志 schema：
  - `docs/technical/portfolio_manager_algorithm.md`
- 单一评分输入设计决策：
  - `docs/technical/phase0_design_research_single_score_input.md`
- 动态工作记忆：
  - `docs/modules/execution_layer_working_memory.md`

### 成熟度判断

- 当前属于“设计冻结 / 方案沉淀”阶段。
- 尚未进入 `src/ashare_lab/strategy/portfolio.py`、`src/ashare_lab/backtest/engine.py` 等真实实现。
- 文档中 Phase 1-3 仍标记为 TODO 或待实施。

### 合并建议

- 不建议整分支直接并入，原因不是质量差，而是它还不是“实现分支”。
- 可作为执行层开发的设计基线保留。
- 若要回收价值，优先考虑“择优吸收文档”，而不是把该分支当作代码基线合并。

---

## 2.2 `feature/model-3d-5d-10d-head`

### 改动规模

- 相对 `develop` 独有提交：8
- 主要变更：34 个文件，约 `1690` 行新增、`146` 行删除
- 变更类型：代码 + 配置 + 文档 + 测试同时推进

### 主要产出

代码侧：

- 统一主线 schema：
  - `src/ashare_lab/trend_schema.py`
- 主线聚合层：
  - `src/ashare_lab/recommendation/trend_aggregation.py`
- 更接近交易行为的主线评估：
  - `src/ashare_lab/evaluation/trade_like_panel.py`
- 主线训练/推荐链路对齐：
  - `src/ashare_lab/models/transformer.py`
  - `src/ashare_lab/recommendation/engine.py`
  - `src/ashare_lab/training/mtl_finetune/__init__.py`
  - `scripts/run_lstm_rolling_retrain_dim19_regime.py`

文档侧：

- 主模型开发计划：
  - `docs/research/mainline_3510d_model_development_plan_20260310.md`
- 主模型开发复盘：
  - `docs/research/mainline_3510d_development_retrospective_20260310.md`

测试侧：

- `tests/test_trade_like_panel.py`
- `tests/test_trend_aggregation.py`
- `tests/test_trend_schema.py`

### 成熟度判断

- 已形成真实可运行能力，不再只是方案。
- 核心抽象较清晰：先统一 `3d/5d/10d` schema，再聚合为 `alpha_score`，再用统一 panel 做比较。
- 文档复盘已明确暴露本轮开发经验，具备被吸收为流程基线的价值。

### 验证情况

以下命令通过：

```bash
PYTHONPATH=src:. pytest -q \
  tests/test_trade_like_panel.py \
  tests/test_trend_aggregation.py \
  tests/test_trend_schema.py \
  tests/test_lstm_dynamic_heads.py \
  tests/test_multilevel_tuning.py
```

结果：`25 passed`

### 风险提示

- 直接执行 `pytest -q ...` 会因为新增模块未进入默认导入路径而报 `ModuleNotFoundError`。
- 这说明“测试运行入口”还没有被明确标准化，是后续流程必须补的基线项。

### 合并建议

- 适合作为第一优先级并入 `develop` 的代码分支。
- 理由：代码、文档、测试三者闭环相对完整，且 `develop` 当前是其祖先，可先吸收主线抽象。

---

## 2.3 `feature/model-d1-research`

### 改动规模

- 相对 `develop` 独有提交：5
- 主要变更：34 个文件，约 `3909` 行新增、`88` 行删除
- 变更类型：研究配置、训练脚本、比较脚本、门禁文档、测试

### 主要产出

配置与训练侧：

- `1d` 独立数据/实验配置：
  - `configs/datasets/1d_independent/*.toml`
  - `configs/experiments/1d_independent/*.toml`
- `1d` 滚动训练与稳定性脚本：
  - `scripts/run_xgboost_rolling_retrain_1d_direction.py`
  - `scripts/run_xgboost_1d_direction_hparam_grid.py`
  - `scripts/run_xgboost_1d_direction_small_grid.py`
  - `scripts/run_xgboost_1d_direction_stability_review.py`

评估与比较侧：

- 扩展统一比较脚本：
  - `scripts/compare_ic_reports.py`
- 扩展主线 XGB 滚动脚本的 horizon 口径处理：
  - `scripts/run_xgboost_rolling_retrain_regime.py`

文档侧：

- `1d` 实验协议：
  - `docs/research/1d_experiment_protocol.md`
- `1d` 审计结论：
  - `docs/research/model_d1_audit_20260309.md`
- 模型层分支计划：
  - `docs/research/model_research_branch_plan_20260309.md`

### 成熟度判断

- 该分支不是“把 `1d` 并入主线”，而是“把 `1d` 研究流程单列出来并冻结边界”。
- 最有价值的产物不是 `1d` 本身，而是：
  - 实验协议卡片化；
  - 股票池 / 特征组命名规则；
  - 同窗比较与门禁规则；
  - “`1d` 不污染主线”的边界冻结。

### 验证情况

以下命令通过：

```bash
pytest -q \
  tests/test_xgb_1d_direction.py \
  tests/test_xgb_1d_hparam_grid.py \
  tests/test_xgb_1d_small_grid.py \
  tests/test_xgb_1d_stability_review.py \
  tests/test_xgb_dynamic_horizons.py \
  tests/test_compare_ic_reports.py
```

结果：`39 passed`

### 合并建议

- 建议在主模型分支并入后，再处理该分支。
- 不建议先于主模型分支合并，原因是它与主模型分支在研究入口和 XGB 主脚本上存在交叉改动。

---

## 3. 分支间冲突热点

## 3.1 `feature/model-3d-5d-10d-head` vs `feature/model-d1-research`

已确认的冲突热点：

- `docs/README.md`
- `docs/research/README.md`
- `scripts/run_xgboost_rolling_retrain_regime.py`

冲突性质：

- 前两者属于“入口文档顺序与导航描述”冲突，逻辑上可并存，但需要人工整合。
- 最后一项属于真实代码冲突：
  - 主模型分支在该脚本中引入主线 schema / 聚合相关约束；
  - `1d` 分支在该脚本中增强 horizon 配置与比较口径；
  - 不能机械保留任一侧，需要手工合并。

## 3.2 `feature/execution-layer-v2` vs 其他分支

与主模型分支有重叠的文件：

- `NEXT_STEPS.md`
- `ROADMAP.md`
- `docs/README.md`
- `docs/modules/README.md`

与 `1d` 分支有重叠的文件：

- `docs/README.md`

冲突性质：

- 基本都是入口文档与导航项冲突。
- 由于执行层分支本身仍是方案阶段，不应优先争夺这些入口文件的默认口径。

---

## 4. 推荐整理顺序

## 4.1 第一阶段：先统一可运行代码基线

推荐顺序：

1. 先并入 `feature/model-3d-5d-10d-head`
2. 再让 `feature/model-d1-research` 对齐新的 `develop`
3. 最后处理 `feature/execution-layer-v2`

理由：

- 主模型分支已经产出真实代码能力，是“平台级主线抽象”；
- `1d` 分支的定位应建立在“主线已稳定”之上；
- 执行层分支目前更像下一轮开发的设计包，不是当前实现基线。

## 4.2 第二阶段：把 `1d` 经验吸收为研究基线

`feature/model-d1-research` 的合并目标不应理解为“合并 `1d` 进主线”，而应是：

- 吸收 `1d` 实验协议；
- 吸收 `1d` 研究边界与命名规范；
- 吸收统一比较脚本与门禁规则；
- 保留“`1d` 继续独立研究，不进入默认主线”的结论。

## 4.3 第三阶段：把执行层方案从“分支工作记忆”转成“项目基线文档”

建议动作：

- 保留执行层方案文档；
- 不急于把整个分支当成功能分支并入；
- 等真实实现开始后，再开新提交或新分支承接 Phase 1-3；
- 实现完成后，按代码 + 测试 + 验收报告回并。

---

## 5. 推荐的合并策略

## 5.1 `feature/model-3d-5d-10d-head`

建议：

- 作为首个代码分支并入 `develop`
- 合并后立即在 `develop` 跑一次与该分支相同的最小测试集

目标：

- 固定主线 schema
- 固定 `alpha_score` 聚合契约
- 固定 trade-like panel 的主评估口径

## 5.2 `feature/model-d1-research`

建议：

- 不直接硬并
- 先把 `develop` 的新主线吸收进该分支，手工处理三类冲突：
  - 文档入口
  - `docs/research/README.md`
  - `scripts/run_xgboost_rolling_retrain_regime.py`

目标：

- 把 `1d` 的“协议、门禁、审计和实验工具”收进主基线
- 不把 `1d` 误写成新的默认主线

## 5.3 `feature/execution-layer-v2`

建议：

- 先不做整分支合并
- 仅将其中已经明确有价值的文档择优吸收
- 真实实现开始后，另起实现任务与验收测试

目标：

- 保留执行层设计资产
- 避免“只有方案，没有代码”的分支提前污染主基线

---

## 6. 这次整理应沉淀的流程基线

## 6.1 分支启动当天必须先做三件事

1. 先写专项计划文档，不让 `NEXT_STEPS.md` 承担具体执行顺序。
2. 先冻结术语边界与 source of truth 文档。
3. 先写“本分支不做什么”，避免任务中途越界。

## 6.2 代码分支与方案分支分开管理

- 纯设计 / 方案 / working memory 分支，不直接视为可合并代码分支。
- 代码分支必须至少具备：
  - 实现；
  - 测试；
  - 验收口径；
  - 文档同步。

## 6.3 评估口径必须唯一

- 主模型线：固定唯一主评估 panel，不允许旧口径继续挂在默认入口争夺解释权。
- `1d` 研究线：固定实验卡片、同窗比较、门禁阈值。
- 执行层：固定决策日志、交易日志、诊断摘要三类产物，再进入代码实现。

## 6.4 默认配置状态必须显式标注

建议统一使用类似字段：

- `model_track`
- `config_profile`
- `config_status`

状态至少区分：

- `baseline`
- `candidate-best`
- `frozen-best`

## 6.5 测试运行入口必须标准化

当前已经暴露的问题：

- 新增 `src/ashare_lab/...` 模块后，裸跑 `pytest -q` 可能无法导入分支内新增代码。

建议固定至少一种团队约定：

```bash
PYTHONPATH=src:. pytest -q ...
```

或：

```bash
python -m pytest -q ...
```

若后续采用 editable install，也应把安装与验证动作写进统一开发流程，而不是靠个人记忆。

## 6.6 热点入口文档尽量只做“导航层更新”

本轮冲突最多的文件，几乎都是：

- `README.md`
- `NEXT_STEPS.md`
- `ROADMAP.md`
- `docs/README.md`
- `docs/research/README.md`
- `docs/modules/README.md`

建议：

- 这些文件只保留导航、边界、默认入口；
- 具体执行顺序、实验细节、复盘经验，一律下沉到专项文档；
- 避免每条分支都去抢入口页的细节描述。

---

## 7. 建议的下一步动作

1. 先把 `feature/model-3d-5d-10d-head` 作为首个代码基线候选处理。
2. 在合并前，明确团队统一测试入口，避免导入路径再反复踩坑。
3. 合并主模型分支后，再处理 `feature/model-d1-research` 的三处冲突文件。
4. 从 `feature/execution-layer-v2` 中只吸收设计文档，不把它误当成功能已完成分支。
5. 后续若启动执行层真实实现，应基于当前设计文档新开实现任务，而不是继续在“工作记忆分支”上无限堆叠。

---

## 8. 最终结论

当前三条活跃工作线不应被等价对待：

- `feature/model-3d-5d-10d-head`：应优先进入 `develop`，作为主模型能力基线；
- `feature/model-d1-research`：应在主模型基线稳定后吸收其研究协议和工具链；
- `feature/execution-layer-v2`：应视为设计资产分支，先保留方案价值，再等待真实实现落地。

如果目标是“对齐工作进度基线 + 整合经验 + 固化流程”，最合适的方式不是一次性粗暴合并所有分支，而是：

1. 先吸收已形成代码闭环的能力；
2. 再吸收研究协议与边界规则；
3. 最后把方案分支转为下一轮实现的明确输入。
