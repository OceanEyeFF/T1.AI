# 1d / 3d|5d|10d 公用层盘点（2026-03-11）

## 1. 背景与目的

本文档是 `develop` 治理期 G3 专题产物，对 `src/ashare_lab/` 下 1d 研究线与 3d|5d|10d 主线的代码重叠做一次系统盘点。

**核心目标：**

- 搞清哪些代码两条线完全共享、哪些已经分岔；
- 判断分岔原因是 contract 层面的差异还是只是机械性重构；
- 给出"能抽象 / 需等 contract 统一 / 不应抽象"的分类和优先级。

**不做的事：**

- 不在本文档里实施抽象；
- 不把两条线强行合成一条。

---

## 2. 分支拓扑与合并状态

```
develop (当前)
  ├─ 已吸收 feature/model-3d-5d-10d-head（fast-forward）
  │   引入：trend_schema.py, trade_like_panel.py, trend_aggregation.py
  │   重构：6 个共享文件改用 trend_schema 常量
  │
  ├─ feature/model-d1-research（未合并）
  │   独有：configs/datasets/1d_independent/, 4 个 xgb_1d 脚本, 5 个 1d 测试
  │   共享基底：与 develop 吸收 3d-5d-10d-head 前的版本一致
  │
  └─ feature/execution-layer-v2（未合并）
      共享基底：与 1d 完全一致（所有分歧文件逐字节相同）
      独有：执行层设计文档
```

**关键结论：** 三个分支共享同一份"旧基底"。所有代码分歧的唯一根因是 `feature/model-3d-5d-10d-head` 合入 develop 时引入的 `trend_schema.py` 重构。1d 和 execution-layer-v2 之间不存在任何 src/ 代码差异。

---

## 3. 代码重叠点清单

### 3.1 统计总览

| 类别 | 文件数 | 完全一致 | 有分歧 | 仅 develop | 仅 1d |
|------|--------|----------|--------|------------|-------|
| src/ashare_lab/ | 55 | 44 | 6 | 3+1(stock_pool) | 0 |
| configs/ | ~10 | ~6 | 1 | 0 | 6 |
| scripts/ | ~36 | ~26 | 10 | 0 | 4 |
| tests/ | ~42 | ~34 | 3 | 3 | 5 |

### 3.2 src/ashare_lab/ 逐模块状态

#### 完全一致（可直接共享）

| 模块 | 文件 | 状态 |
|------|------|------|
| `data/` | akshare_source.py, index_source.py, odp_source.py, tushare_source.py | ✅ 全部一致 |
| `features/` | base.py, momentum.py, price_slope.py, technical.py, volume.py | ✅ 全部一致 |
| `labels/` | excess_return.py | ✅ 一致 |
| `dataset/` | builder.py, sequence_builder.py, sequence_builder/__init__.py | ✅ 一致 |
| `evaluation/` | metrics.py, sanity_checks.py | ✅ 一致 |
| `training/` | trainer.py, mtl_finetune.py | ✅ 一致 |
| `recommendation/` | history.py, validator.py | ✅ 一致 |
| `backtest/` | book.py, engine.py | ✅ 全部一致 |
| `pipeline/` | orchestrator/, monitoring/ | ✅ 全部一致 |
| `strategy/` | portfolio.py, signal.py | ✅ 全部一致 |
| `strategies/` | momentum.py | ✅ 一致 |
| 顶层 | types.py, universe.py, utils.py, reporting.py | ✅ 全部一致 |

**共 44 个文件完全一致，覆盖 80% 的代码库。**

#### 有分歧（6 个文件）

| 文件 | diff 行数 | 分歧根因 | 语义差异 |
|------|-----------|----------|----------|
| `labels/multi_horizon.py` | 37 | develop 引入 trend_schema 常量 | **无** — 两边默认 horizons 都是 (3,5,10) |
| `dataset/sequence_parquet.py` | 43 | develop 用 trend_schema.infer_label_cols | **无** — 两边都要求 label_3d/5d/10d |
| `models/transformer.py` | 165 | develop 用 schema 常量 + ModuleDict | **无** — 同样 3 个头，同样输入输出 |
| `training/mtl_finetune/__init__.py` | 74 | develop 用 schema 常量 | **无** — evaluate() 产出同样的 ic_3d/5d/10d |
| `recommendation/__init__.py` | 55 | develop 多导出 trend_aggregation | **有** — develop 多了聚合排名能力 |
| `recommendation/engine.py` | 131 | develop 多了 generate_trend_recommendations | **有** — develop 多了主线聚合推荐方法 |

#### 仅 develop 有（4 个文件）

| 文件 | 行数 | 角色 |
|------|------|------|
| `trend_schema.py` | 71 | 主线 3d/5d/10d horizon 常量中心化 |
| `evaluation/trade_like_panel.py` | 289 | 主线 trade-like 评估面板 |
| `recommendation/trend_aggregation.py` | 191 | 主线多 horizon 聚合排名 |
| `stock_pool/__init__.py` | 入口包 | 股票池 registry / export 入口（S1 minimal） |

#### 仅 1d 有

| 类别 | 文件 |
|------|------|
| configs | `configs/datasets/1d_independent/` (4 个 toml) |
| configs | `configs/experiments/1d_independent/` (4 个 toml) |
| configs | `configs/datasets/sequence_dataset_xgb_d1_close_candidate.toml` |
| configs | `configs/experiments/xgb_rolling_d1_close_candidate.toml` |
| scripts | `run_xgboost_1d_direction_hparam_grid.py` |
| scripts | `run_xgboost_1d_direction_small_grid.py` |
| scripts | `run_xgboost_1d_direction_stability_review.py` |
| scripts | `run_xgboost_rolling_retrain_1d_direction.py` |
| tests | `test_xgb_1d_direction.py`, `test_xgb_1d_hparam_grid.py` |
| tests | `test_xgb_1d_small_grid.py`, `test_xgb_1d_stability_review.py` |
| tests | `test_xgb_dynamic_horizons.py` |

### 3.3 scripts/ 分歧详情

| 脚本 | diff 行数 | 分歧性质 |
|------|-----------|----------|
| `compare_ic_reports.py` | 382 | **1d 更通用** — 引入 horizon-generic IC 提取，develop 仍硬编码 3d/5d/10d |
| `run_xgboost_rolling_retrain_regime.py` | 410 | 主要是 trend_schema 引用差异 |
| `run_lstm_rolling_retrain_dim19_regime.py` | 291 | 同上 |
| `train_mtl.py` | 30 | trend_schema 引用 + 注释措辞 |
| `build_sequence_dataset_market_state.py` | 46 | trend_schema 引用 |
| 其余 5 个 run_*.py | 12~24 | 均为 trend_schema 引用 |

> 注：`build_sequence_dataset_market_state.py` 这里的分歧仍以 trend_schema 引用为主；截至 2026-03-24，stock_pool 接线已补齐，不再是空壳入口问题。

---

## 4. Contract 一致性判断

### 4.1 输入 Contract（特征格式）

| 维度 | develop (3d\|5d\|10d) | 1d 研究 | 一致性 |
|------|----------------------|---------|--------|
| 特征列格式 | `{name}_t{0..seq_len-1}` | 同 | ✅ 一致 |
| 特征模块 | features/ 全部一致 | 同 | ✅ 一致 |
| 数据源适配 | data/ 全部一致 | 同 | ✅ 一致 |
| 股票池过滤 | universe.py 一致 | 同 | ✅ 一致 |

**结论：输入 contract 完全一致，无需任何适配。**

### 4.2 标签 / 输出 Contract（关键分歧点）

| 维度 | develop (3d\|5d\|10d) | 1d 研究 | 一致性 |
|------|----------------------|---------|--------|
| 默认 horizon | `(3, 5, 10)` via trend_schema | `(3, 5, 10)` hardcoded | ⚠️ 值相同，机制不同 |
| 标签列名 | `label_3d, label_5d, label_10d` | 同 | ✅ 值一致 |
| 预测列名 | `pred_3d, pred_5d, pred_10d` | 同 | ✅ 值一致 |
| 1d 标签需求 | ❌ 不支持 `label_1d` | ✅ 需要 `label_1d` | ❌ **不一致** |
| horizon 参数化 | ❌ 固定 PRIMARY_TREND_HORIZONS | ⚠️ hardcoded 但实际上 1d 脚本独立运行 | ❌ **不一致** |

**结论：**

- 当 1d 线仅使用 `(3,5,10)` 时，两边 contract 实质一致；
- 当 1d 线需要 `label_1d` 做独立预测时，标签 / 模型头 contract 不一致；
- `trend_schema.py` 当前设计是 **主线专用**（固定 3/5/10），不是 horizon-generic 公用层。

### 4.3 评估 Contract

| 维度 | develop (3d\|5d\|10d) | 1d 研究 | 一致性 |
|------|----------------------|---------|--------|
| IC 计算 | metrics.py 一致 | 同 | ✅ 一致 |
| Sanity checks | sanity_checks.py 一致 | 同 | ✅ 一致 |
| IC 报告比较 | hardcoded 5d/10d | **horizon-generic** (可配 --primary-horizons) | ⚠️ **1d 更通用** |
| trade_like_panel | develop-only | 无 | N/A（主线专属） |

**结论：** 基础评估 contract 一致。但 `compare_ic_reports.py` 的 1d 版本已经做了 horizon-generic 改造，**比 develop 版本更适合作为公用层基础**。

---

## 5. 抽象层分类

### 5.1 可立即共享（无需任何改动）

这些模块两条线代码完全一致，已经是事实上的公用层：

| 模块 | 文件数 | 说明 |
|------|--------|------|
| `data/` | 4 | 数据源适配器 |
| `features/` | 5 | 全部特征工程 |
| `labels/excess_return.py` | 1 | 超额收益标签 |
| `dataset/builder.py, sequence_builder/` | 3 | 数据集构建器 |
| `evaluation/metrics.py, sanity_checks.py` | 2 | IC 计算 + 防伪门禁 |
| `training/trainer.py` | 1 | 训练器 |
| `recommendation/history.py, validator.py` | 2 | 推荐历史 + 验证器 |
| `backtest/`, `pipeline/`, `strategy/`, `strategies/` | 12 | 回测/管道/策略 |
| `types.py, universe.py, utils.py, reporting.py` | 4 | 基础类型/工具 |
| **合计** | **34** | **占 src/ 总文件数 62%** |

### 5.2 需等 contract 统一后抽象

这些文件当前存在分歧，但分歧根因单一（trend_schema），统一 contract 后可抽象：

| 文件 | 统一方向 | 前置条件 |
|------|----------|----------|
| `labels/multi_horizon.py` | horizons 参数化（不再固定 3/5/10） | trend_schema 升级为可配置 |
| `dataset/sequence_parquet.py` | label 推断逻辑改为 horizon-agnostic | trend_schema 升级 |
| `models/transformer.py` | MTLTransformer 头数量参数化 | 两条线同意统一模型接口 |
| `training/mtl_finetune/__init__.py` | evaluate() 按 horizon 列表动态生成指标 | 同上 |
| `scripts/compare_ic_reports.py` | **采用 1d 版本的 horizon-generic 实现** | 两条线确认 horizon-generic 是公共需求 |
| `scripts/train_mtl.py` | 移除 trend_schema 硬依赖 | trend_schema 升级 |

**统一路径建议：**

将 `trend_schema.py` 从"主线 3d/5d/10d 固定常量"升级为"可参数化的 horizon schema"：

```python
# 当前 develop 版本（固定主线）
PRIMARY_TREND_HORIZONS = (3, 5, 10)

# 建议升级方向（参数化公用层）
def make_horizon_schema(horizons: tuple[int, ...]) -> HorizonSchema:
    ...

MAINLINE_SCHEMA = make_horizon_schema((3, 5, 10))
D1_SCHEMA = make_horizon_schema((1,))  # 或 (1, 3, 5, 10)
```

### 5.3 各线专属，不应抽象

| 文件 | 归属 | 理由 |
|------|------|------|
| `trend_schema.py`（当前版本） | 主线 | 固定 (3,5,10)，是主线 contract |
| `evaluation/trade_like_panel.py` | 主线 | 主线 trade-like 评估方法 |
| `recommendation/trend_aggregation.py` | 主线 | 3d/5d/10d 聚合排名，1d 不需要 |
| `recommendation/engine.py:generate_trend_recommendations()` | 主线 | 主线聚合推荐方法 |
| `configs/datasets/1d_independent/` | 1d 线 | 1d 实验配置 |
| `configs/experiments/1d_independent/` | 1d 线 | 1d 实验配置 |
| `scripts/run_xgboost_1d_direction_*.py` | 1d 线 | 1d 专属脚本 |
| `tests/test_xgb_1d_*.py` | 1d 线 | 1d 专属测试 |
| `tests/test_trade_like_panel.py` | 主线 | 主线专属测试 |
| `tests/test_trend_aggregation.py` | 主线 | 主线专属测试 |
| `tests/test_trend_schema.py` | 主线 | 主线专属测试 |

---

## 6. 推荐抽象优先级

### P0：确认现有公用层（零成本）

**44 个完全一致的文件已经是公用层**，不需要任何代码改动，只需在文档/规范中明确它们的公用层地位。

### P1：`compare_ic_reports.py` horizon-generic 统一

| 项目 | 说明 |
|------|------|
| 优先级 | **高** — 这是两条线都需要的评估比较工具 |
| 方向 | 采用 1d 分支的 horizon-generic 实现回合入 develop |
| 收益 | develop 也获得按 horizon 灵活比较的能力 |
| 风险 | 低 — 1d 版本是 develop 版本的超集，向后兼容 |

### P2：`trend_schema.py` 升级为参数化 horizon schema

| 项目 | 说明 |
|------|------|
| 优先级 | **中** — 是 P3 的前置条件 |
| 方向 | 保留 `MAINLINE_SCHEMA` 作为默认，增加参数化构造能力 |
| 收益 | 6 个分歧文件可以在统一 schema 下收敛 |
| 风险 | 中 — 需要仔细保持主线现有行为不变 |

### P3：模型/训练/数据集层 horizon 参数化

| 项目 | 说明 |
|------|------|
| 优先级 | **低（当前）** — 两条线当前可以独立运行 |
| 方向 | MTLTransformer/evaluate/sequence_parquet 接受 horizon list 参数 |
| 收益 | 真正的代码复用，消除重复维护 |
| 前置条件 | P2 完成 + 两条线确认统一接口 |

---

## 7. 公用层抽象技术门槛

对任何代码从"各线独立"升级为"公用层"，必须同时满足以下三个条件：

### 门槛 1：输入 Contract 一致

两条线消费相同格式的输入数据。

- 当前状态：✅ 已满足（features/ 和 data/ 完全共享）

### 门槛 2：输出 Contract 一致或可参数化

两条线的输出格式要么相同，要么通过统一参数化接口产出各自格式。

- 当前状态：⚠️ 部分满足
  - 主线输出 `pred_3d/5d/10d`，1d 线需要输出 `pred_1d`
  - 需要 horizon 参数化后才能统一

### 门槛 3：评估 Contract 一致

两条线的评估方式使用相同的指标计算逻辑和比较规则。

- 当前状态：⚠️ 部分满足
  - 基础 IC 计算一致（metrics.py）
  - 比较工具不一致（compare_ic_reports.py 分歧）
  - 1d 版本更通用，可以反向统一 develop

---

## 8. 分歧根因归因图

```
feature/model-3d-5d-10d-head 合入 develop
        │
        ├─ 引入 trend_schema.py（主线 horizon 常量中心化）
        │
        ├─ 6 个共享文件被重构为使用 trend_schema
        │   ├─ labels/multi_horizon.py
        │   ├─ dataset/sequence_parquet.py
        │   ├─ models/transformer.py
        │   ├─ training/mtl_finetune/__init__.py
        │   ├─ recommendation/__init__.py
        │   └─ recommendation/engine.py
        │
        ├─ 3 个主线专属文件新增
        │   ├─ evaluation/trade_like_panel.py
        │   ├─ recommendation/trend_aggregation.py
        │   └─ trend_schema.py
        │
        └─ 10+ scripts/configs 被重构
            └─ compare_ic_reports.py 在 1d 分支独立进化为更通用版本

feature/model-d1-research（未合入）
        │
        └─ 保持旧基底 + 独立增加 1d 实验资产
            ├─ configs/datasets/1d_independent/ (4)
            ├─ configs/experiments/1d_independent/ (4)
            ├─ scripts/run_xgboost_1d_* (4)
            └─ tests/test_xgb_1d_* (5)
```

---

## 9. 对后续合并的建议

### 1d 分支合入 develop 时

1. **无冲突区域**（44 个一致文件 + 1d 独有资产）：直接合入；
2. **6 个分歧文件**：必须决定是否让 1d 采用 trend_schema；
3. **compare_ic_reports.py**：建议采用 1d 的 horizon-generic 版本作为合并基础；
4. **1d 独有配置/脚本**：直接合入，在 `configs/` 下保持 `1d_independent/` 子目录隔离。

### execution-layer-v2 合入 develop 时

- 与 1d 面临完全相同的 6 个文件冲突（因为基底一致）；
- 建议先合 1d，再合 execution-layer（减少重复冲突解决）。

---

## 10. 与 G4（配置/版本规范）的关系

G4 已完成，参见 [config_and_artifact_naming_20260311.md](config_and_artifact_naming_20260311.md)。

### 10.1 G4 对 G3 分类的影响

| G4 定义 | 对 G3 共享层的影响 |
|---------|-------------------|
| `model_track` 区分 `mainline_3510d` / `1d_independent` | 确认两条线有独立身份，配置层面**不应强行统一** |
| `config_profile` 与文件名一致 | config parser（`scripts/config_io.py`）当前完全一致，可作为公用层 |
| 元数据三字段（model_track/config_profile/config_status） | 两条线的配置文件需补齐，但**格式完全一致**，读取逻辑可共享 |
| `_effective_config.json` 输出规范 | 输出格式统一，生成逻辑可抽象为公用层 |

### 10.2 configs/ 子目录结构确认

- `configs/*/1d_independent/` 子目录模式**符合 G4 规范**（§ 2.1 允许模型线子目录，不超过两层）
- 两条线共享 `configs/datasets/` 和 `configs/experiments/` 的顶层结构

### 10.3 对抽象优先级的修正

基于 G4 发现，调整 § 6 推荐优先级中的 P1 补充项：

- **P1 补充：** `scripts/config_io.py` 和 `_effective_config.json` 生成逻辑应纳入公用层盘点
  - `config_io.py` 当前完全一致（已确认），是事实公用层
  - 后续两条线都需要输出 G4 规范的 `_effective_config.json`，生成函数可统一
- **P2 不变：** `trend_schema.py` 参数化仍是中期目标，与 G4 的 `model_track` 区分互不冲突
- `stock_pool/__init__.py` 已从 S0 预留态推进到 S1 minimal 入口，后续不再按“~空”处理

---

## 11. 相关文档索引

| 文档 | 路径 |
|------|------|
| 治理总清单 | `docs/branch_tasks/develop_governance_backlog_20260311.md` |
| 数据契约 | `docs/data_contract.md` |
| 双窗口评估基线 | `docs/overview/dual_window_evaluation_baseline_20260311.md` |
| 股票池模组基线 | `docs/modules/stock_pool_module_baseline_20260311.md` |
| 股票池模组开发计划 | `docs/modules/stock_pool_module_development_plan_20260311.md` |
| 分支任务 - develop | `docs/branch_tasks/develop.md` |
| 分支任务 - 1d | `docs/branch_tasks/feature_model_d1_research.md` |
