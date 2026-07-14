---
title: "WT-R3-A1 Cleanup Inventory"
artifact_type: "worktrack-inventory"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A1"
updated: "2026-07-14T12:55:00+08:00"
owner: "OceanEyeFF"
status: "approved_batch_a_and_b"
approval:
  approved_by: "OceanEyeFF"
  approved_at: "2026-07-14T12:55:00+08:00"
  approved_batches: ["A", "B"]
  approval_message: "Batch A + Batch B 的内容都可以删"
  retained: ["Batch C / 强制保留项"]
---

# WT-R3-A1 Cleanup Inventory

> 只读 inventory。本文件中的「建议删」**不等于已批准删除**。  
> A2 仅可删除本清单中经 programmer 明确批准的项。  
> 受保护路径默认不可删：`src/`、`.servo/goal-charter.md`、`inputs/pools/`（含 low_manipulation 正式池）、`inputs/configs/profiles/`、`inputs/data/cache/tushare*`。

## Control Signal

- inventory_status: approved_batch_a_and_b
- deletes_executed: true
- delete_execution_log: .servo/worktrack/WT-R3-A2-execution-log.md
- approved_by: OceanEyeFF
- approved_at: 2026-07-14T12:55:00+08:00
- approved_batches: [A, B]
- retained_batches: [C]
- pytest_after_delete: 395 passed / 2 failed（仍为 F1/F2；multilevel dry-run 已修复）
- recommend_next: Init WT-R3-A3 修 F1/F2；可选 commit 本轮删除

## Summary Counts

| 桶 | 条目数（约） | 说明 |
|----|-------------:|------|
| 建议删 | 见下表 | P3 默认 + 无/弱引用 |
| 保留 | 见下表 | 受保护、现行入口、或仍有测试/脚本依赖 |
| 待定 | 见下表 | 有引用但仍过时，需你拍板 |
| R3 可修测 | 2 | 路径/注册表债务，不依赖数据湖 |
| Defer R4 | 0（本轮定性） | 两个 fail 均不需要重建数据湖 |

---

## 1. docs/archive/（P3：过时材料默认建议删）

| ID | 路径 | 默认桶 | 引用摘要 | 建议 |
|----|------|--------|----------|------|
| D-A0 | `docs/archive/README.md` | 建议删 | 仅目录索引；`docs/WORK_RULES.md` 提到 archive 作为归档去处 | **待定**：可留空壳 README 或随整目录删 |
| D-A1 | `docs/archive/data_sources.md` | 建议删 | 无活跃 docs 硬链（除 archive README） | 建议删 |
| D-A2 | `docs/archive/model_line_boundaries_1d_vs_3510d_20260309.md` | 建议删 | 已被 architecture/research 现行文档替代 | 建议删 |
| D-A3 | `docs/archive/news_sources.md` | 建议删 | 无活跃引用 | 建议删 |
| D-A4 | `docs/archive/production_scheduler.md` | **待定** | `tests/test_deployment_files.py` **硬依赖存在性** | **待定**：删前必须改/退役该测试（A3） |
| D-A5 | `docs/archive/stock_pool_module_baseline_20260311.md` | 建议删 | 旧基线；现行见 guides/reference | 建议删 |
| D-A6 | `docs/archive/stock_pool_module_development_plan_20260311.md` | 建议删 | 旧计划 | 建议删 |
| D-A7 | `docs/archive/stock_pool_registry_baseline_20260311.md` | 建议删 | 旧基线 | 建议删 |
| D-A8 | `docs/archive/system_io_and_architecture_spec.md` | 建议删 | 已被 `docs/architecture/*` 替代 | 建议删 |

---

## 2. docs/research/（P3：过时计划/PDF 默认建议删；现行口径可留）

| ID | 路径 | 默认桶 | 引用摘要 | 建议 |
|----|------|--------|----------|------|
| D-R0 | `docs/research/README.md` | 保留 | 研究入口索引 | **保留** |
| D-R1 | `docs/research/research_checklist.md` | 保留 | README 推荐阅读 #1 | **保留** |
| D-R2 | `docs/research/mainline_3510d_evaluation_gate_protocol.md` | 保留 | README + 评估门禁现行 | **保留** |
| D-R3 | `docs/research/daily_cs_eval_workflow.md` | 保留 | README；引用 rolling 脚本名 | **保留** |
| D-R4 | `docs/research/low_manipulation_screening.md` | 保留 | 与现行 low_manipulation 池相关 | **保留** |
| D-R5 | `docs/research/future_roadmap_suggestions.md` | 待定 | README 列出；偏路线笔记 | **待定** |
| D-R6 | `docs/research/1d_independent_model_execution_strategy_20260309.md` | 建议删 | 202603 计划；1d 仍 blocked | 建议删 |
| D-R7 | `docs/research/1d_independent_model_research_plan.md` | 建议删 | 同上 | 建议删 |
| D-R8 | `docs/research/mainline_3510d_development_retrospective_20260310.md` | 建议删 | 历史复盘 | 建议删 |
| D-R9 | `docs/research/mainline_3510d_model_development_plan_20260310.md` | 建议删 | 历史计划 | 建议删 |
| D-R10 | `docs/research/multilevel_tuning_plan_20260307.md` | 待定 | 被 multilevel/auto_tune 文档与脚本引用叙述 | **待定** |
| D-R11 | `docs/research/数据窗口结构的区别.md` | 建议删 | 202603 笔记；README 仍链 | 建议删（或改 README 后退役） |
| D-R12 | `docs/research/多头输出和数据切分.md` | 建议删 | 同上 | 建议删 |
| D-R13 | `docs/research/警惕伪信号.md` | 建议删 | 同上 | 建议删 |
| D-R14 | `docs/research/选股池方法论.md` | 待定 | 长文方法论；guides 已有维护指南 | **待定** |
| D-R15 | `docs/research/高频与日频模型分析.md` | 建议删 | 历史分析 | 建议删 |
| D-R16 | `docs/research/A股短中线多头预测的 IC 提升与评估体系可执行研究计划.pdf` | 建议删 | ~678KB PDF；无代码引用 | **建议删** |
| D-R17 | `docs/research/A股短中线预测IC提升方案：诊断与可执行研究计划.pdf` | 建议删 | ~404KB PDF；无代码引用 | **建议删** |

---

## 3. workspace/checkpoints/（P3：未引用旧权重默认建议删）

| ID | 路径 | 大小 | 默认桶 | 引用摘要 | 建议 |
|----|------|------:|--------|----------|------|
| C-1 | `workspace/checkpoints/best_mtl.pt` | ~10MB | 建议删 | gitignored；训练代码写的是目录惯例名，**无现行入口硬依赖此文件存在**；`model_mtl.toml` 仍写 `models/latest_mtl.pt`（旧路径，属配置债务） | **建议删** |
| C-2 | `workspace/checkpoints/latest_mtl.pt` | ~10MB | 建议删 | 同上（与 best 同尺寸，2026-03 AkShare 时代残留） | **建议删** |
| C-3 | `workspace/checkpoints/rolling_dim19/` | 空目录 | 建议删 | 无文件 | **建议删**（空壳） |

注：`workspace/checkpoints/` **目录本身保留**（gitignore + 训练默认 save_dir）。

---

## 4. Cache / 散落 CSV

| ID | 路径 | 默认桶 | 引用摘要 | 建议 |
|----|------|--------|----------|------|
| K-1 | `inputs/data/cache/akshare/` | 建议删 | 探针/旧源；R4 以 TuShare 为主 | 建议删 |
| K-2 | `inputs/data/cache/akshare_probe/` | 建议删 | 探针 | 建议删 |
| K-3 | `inputs/data/cache/akshare_probe2/` | 建议删 | 探针 | 建议删 |
| K-4 | `inputs/data/cache/akshare_probe3/` | 建议删 | 探针 | 建议删 |
| K-5 | `inputs/data/cache/tushare*`（含 qfq/moneyflow/daily_basic/fund/probe） | **保留** | 受保护；MS-R4 输入 | **保留** |
| K-6 | `inputs/data/cache/odp/` | 待定 | 特征脚本可能引用 ODP | **待定** |
| K-7 | `inputs/data/cache/*.csv`（根下 9 个日K CSV） | 建议删 | 旧散落样本；非 tushare 分区结构 | **建议删** |

---

## 5. Experiment TOML（旧 dataset_dir）

| ID | 路径 | 默认桶 | 引用摘要 | 建议 |
|----|------|--------|----------|------|
| E-0 | `inputs/configs/experiments/README.md` | 保留 | 目录说明 | **保留** |
| E-1 | `inputs/configs/experiments/lstm_rolling_baseline.toml` | 待定 | `dataset_dir=data/datasets/lstm_quick8_...`（路径已不存在）；被 `run_multilevel_tuning` / rolling 脚本消费 | **待定**：建议删 **或** A3 改路径后保留骨架 |
| E-2 | `inputs/configs/experiments/lstm_rolling_fastpilot.toml` | 待定 | 同上 | **待定** |
| E-3 | `inputs/configs/experiments/xgb_rolling_baseline.toml` | 待定 | 同上 | **待定** |
| E-4 | `inputs/configs/experiments/xgb_rolling_fastpilot.toml` | 待定 | 同上 | **待定** |

相关 profile（**受保护目录** `inputs/configs/profiles/` — 默认不删，仅记账）：

- `sequence_dataset_baseline.toml` / `market_state_dataset_baseline.toml` 仍含 `output_dir = "data/datasets/..."` → **A3 路径修复**，非删除。

---

## 6. scripts/（P3：无引用 one-off → 建议删；有测试/入口 → 保留或待定）

### 6.1 建议保留（现行入口 / 测试 / pyproject）

| ID | 脚本 | 理由 |
|----|------|------|
| S-keep | `daily_pipeline.py/.sh`, `env_guard.py`, `load_env.sh`, `config_io.py`, `runtime_metadata.py` | 生产/日更链路 |
| S-keep | `build_sequence_dataset.py`, `build_sequence_dataset_market_state.py`, `build_dataset*.py` | 数据集构建入口；测试引用 |
| S-keep | `train_model.py`, `train_mtl.py`, `train_baseline_models.py`, `evaluate_model.py`, `evaluate_recommendation.py`, `generate_daily_recommendations.py`, `validate_recommendations.py`, `run_backtest.py`, `run_sanity_checks.py`, `compare_ic_reports.py`, `audit_ic_reports.py` | 主链路 / 评估 |
| S-keep | `run_lstm_rolling_retrain_dim19_regime.py`, `run_xgboost_rolling_retrain_regime.py`, `run_multilevel_tuning.py`, `auto_tune_xgb.py` | 被多测试 import；调参链路 |
| S-keep | `score_low_manipulation.py` | 与现行池构造相关 |
| S-keep | `setup_conda_env.sh`, `run_develop_min_regression.sh` | 环境/回归 |

### 6.2 建议删 / 待定（历史实验 one-off）

| ID | 路径 | 默认桶 | 引用摘要 | 建议 |
|----|------|--------|----------|------|
| S-1 | `scripts/run_dim52_group_ablation.py` | 建议删 | 默认旧 `data/datasets/...`；无测试硬依赖 | **建议删** |
| S-2 | `scripts/run_lstm_dim16_vs_dim19_market.py` | 建议删 | 旧对比实验；默认旧 dataset | **建议删** |
| S-3 | `scripts/run_lstm_walkforward_sign_calibration.py` | 待定 | 默认旧 dataset；可能仍有研究价值 | **待定** |
| S-4 | `scripts/run_lstm_rolling_retrain_dim19_h2.py` | 待定 | `daily_cs_eval_workflow.md` 提及 | **待定** |
| S-5 | `scripts/clean_data.sh` | 建议删 | 仍指向 `data/datasets` 旧布局 | **建议删** |
| S-6 | `scripts/build_universe.py` | 待定 | pyproject 列出；旧选股宇宙；与 R0 方法论可能冲突 | **待定** |
| S-7 | `scripts/select_industry_stocks.py` | 待定 | pyproject 列出；依赖 build_universe | **待定** |

---

## 7. 空壳 pools（非 low_manipulation）

| ID | 路径 | 建议 |
|----|------|------|
| P-1 | `inputs/pools/momentum/`（仅 README） | **待定**（空壳策略目录；非受保护内容本体，但是 pools 树下） |
| P-2 | `inputs/pools/value/`（仅 README） | **待定** |

`inputs/pools/low_manipulation/**` → **强制保留**。

---

## 8. R2 遗留 2-fail 定性（T2）

实测：`395 passed, 2 failed`（`py311-private`）。

### F1 — `tests/test_stock_pool_registry.py::test_resolve_stock_pool_symbols_and_export_artifacts`

- **现象**: `FileNotFoundError: .../inputs/pools/inputs/pools/low_manipulation/symbols.csv`
- **根因**: `config.toml` 中 `symbols_csv = "inputs/pools/low_manipulation/symbols.csv"`（仓库相对路径），`resolve_stock_pool_symbols` 又与 `registry_root=inputs/pools` **再拼接** → 双前缀。
- **类别**: 路径/契约 bug（R2 迁移残留）
- **分流**: **R3 可处置**（A3：改 `symbols_csv` 为相对 registry 的 `low_manipulation/symbols.csv`，或改 resolve 逻辑）
- **非 R4**: 不需要数据湖

### F2 — `tests/test_stock_pool_registry.py::test_build_sequence_dataset_market_state_cli_smoke_supports_stock_pool_registry`

- **现象**: `KeyError: stock pool not found: ('custom_low_manipulation', 'v1')`
- **根因**: 脚本默认 `--stock-pool-registry-dir=configs/stock_pools`（**旧路径**，R2 后应为 `inputs/pools`）；测试未覆盖该参数。
- **类别**: 默认路径过期
- **分流**: **R3 可处置**（A3：改默认值为 `inputs/pools` + 必要时改测试）
- **非 R4**: 不需要数据湖

### T2 结论

| Fail | R3 可修 | Defer R4 |
|------|---------|----------|
| F1 | 是 | 否 |
| F2 | 是 | 否 |

→ **Defer R4 项：无**。A3 应包含这两项路径修复。

---

## 9. 明确不做（本 inventory 范围外）

- 删除 `src/**`
- 删除 TuShare 主缓存
- 删除正式池 `inputs/pools/low_manipulation/**`
- 执行任何 `git rm` / 文件系统删除（留给批准后的 A2）
- 在 A1 内修复 F1/F2 代码（留给 A3，除非你要求提前）

---

## 10. 建议批准批次（供你勾选）

### Batch A — 低争议建议删（推荐先批）

- D-A1, D-A2, D-A3, D-A5, D-A6, D-A7, D-A8
- D-R6, D-R7, D-R8, D-R9, D-R15, D-R16, D-R17
- C-1, C-2, C-3
- K-1..K-4, K-7
- S-1, S-2, S-5

### Batch B — 待你拍板

- D-A0, D-A4（测依赖）, D-R5, D-R10, D-R11..D-R14
- E-1..E-4
- S-3, S-4, S-6, S-7
- K-6, P-1, P-2

### Batch C — 强制保留

- D-R0..D-R4
- K-5（tushare*）
- `inputs/pools/low_manipulation/**`
- `inputs/configs/profiles/**`（只修路径，不删）
- 第 6.1 节保留脚本

---

## 11. A1 验收自检

- [x] inventory 含删/留/待定 + 引用摘要
- [x] 受保护路径未进入建议删（或已标强制保留）
- [x] 2-fail 定性完整，且均判 R3 可修（非 R4）
- [x] 本 worktrack 未执行删除（请 `git status` 无删文件 diff 验证）

## Handoff

- 下一步：programmer 批准 Batch A/B → Init **WT-R3-A2** 执行删除  
- 并行规划：**WT-R3-A3** 修 F1/F2 + 更新 README/测试对 archive 的依赖 + profiles 旧 `data/datasets` 路径
