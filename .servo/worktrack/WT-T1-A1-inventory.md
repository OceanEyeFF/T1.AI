---
title: "WT-T1-A1 Test Suite Inventory"
artifact_type: "worktrack-inventory"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A1"
updated: "2026-07-14T18:25:00+08:00"
owner: "OceanEyeFF"
status: "approved_del_a1_arch_v1"
approval:
  approved_by: "OceanEyeFF"
  approved_at: "2026-07-14T18:24:00+08:00"
  approved_batches: ["Del-A1", "Arch-v1"]
  deferred_batches: ["Cov-detail"]
  approval_message: >
    1 主要 Del-A1；2 采纳 Arch-v1；3 cov 详细数值等 A4 实测后再定。
---

# WT-T1-A1 Test Suite Inventory

> 只读 inventory / 架构草案。本文件中的「建议删」**不等于已批准删除**。  
> A2 仅可删除/合并本清单中经 programmer 明确批准的项。  
> A3 负责按批准的目标架构搬迁；A4 落地 markers / CI / cov 门禁。  
> 决策锁定：D1=T-heavy · D2=T1→R4 · D3=Del-yes · D4=Acc-balanced。

## Control Signal

- inventory_status: approved_del_a1_arch_v1
- approved_by: OceanEyeFF
- approved_at: 2026-07-14T18:24:00+08:00
- approved_batches: [Del-A1, Arch-v1]
- deferred: Cov-detail → A4 after baseline measurement
- deletes_executed: true
- delete_execution_log: .servo/worktrack/WT-T1-A2-execution-log.md
- pytest_del_a1: tests/test_deployment_files.py → 6 passed
- recommend_next: Init WT-T1-A3（Arch-v1 搬迁）；Cov 细节留待 A4

## Summary Counts

| 桶 | 条目 | 说明 |
|----|-----:|------|
| 建议迁（migrate） | 45 文件全部 | T-heavy 下整面迁入分层目录 |
| 建议删/合并（Del） | 见 Batch Del-A | 主要为冗余存在性测例/重复断言，非整文件铲除 |
| 保留语义 | 几乎全部契约 | 迁走但不丢断言意图 |
| 待定 | 见 Batch Hold | env 名、cov 90 是否可执行等 |
| Defer R4 | 0 | 现有测均可用 mock/tmp；无需数据湖 |

---

## 1. Surface Map（T1-A1-T1）

### 1.1 全局事实

| 项 | 观察 |
|----|------|
| 布局 | 单目录 `tests/test_*.py`；**无** `conftest.py`、无子包 |
| 规模 | 45 文件；约 654 `test_*`；约 9756 LOC |
| 最大文件 | `test_recommendation_validator.py` (684) / `test_dataset_builder.py` (528) / `test_models.py` (486) |
| 脚本耦合 | ≥15 文件 `sys.path` 注入后 `import scripts.*` |
| 配置缺口 | 无 `[tool.pytest.ini_options]` / markers；`pytest-cov` 已依赖 |
| 已有 cov | `pyproject.toml` `[tool.coverage.report] fail_under = 90`（仅在启用 `--cov` 时生效） |
| fast 回归入口 | `scripts/run_develop_min_regression.sh`（5 个文件子集，无 cov） |
| 环境契约 | `scripts/env_guard.py` 默认 `py311-private`；`test_env_guard.py` 仍测 `ashare-lab` 字符串 |

### 1.2 域分组（建议迁移目标域）

| 域 | 文件数 | 代表文件 |
|----|------:|----------|
| features | 4 | `test_features_*.py` |
| dataset_labels | 6 | `test_dataset_builder.py`, `test_labels.py`, `test_sequence_builder.py`, … |
| evaluation | 7 | `test_evaluation*.py`, `test_sanity_checks.py`, `test_compare_ic_reports.py`, … |
| models_training | 6 | `test_models.py`, `test_incremental_training.py`, `test_multilevel_tuning.py`, … |
| recommendation | 7 | `test_recommendation_*.py`, `test_trend_*.py`, … |
| data_pipeline | 6 | `test_tushare_source.py`, `test_odp_source.py`, `test_pipeline.py`, … |
| stock_pool | 1 | `test_stock_pool_registry.py` |
| backtest_strategy | 4 | `test_backtest_metrics.py`, `test_strategy_*.py`, `test_engine_rules.py` |
| ops_deploy | 4 | `test_deployment_files.py`, `test_daily_pipeline_prod.py`, `test_env_guard.py`, `test_monitoring.py` |

### 1.3 质量信号（启发式）

| 信号 | 观察 | 含义 |
|------|------|------|
| 无共享 fixtures | 0 conftest | A3 必须先落 `tests/conftest.py` + factories |
| 存在性断言密集 | `test_deployment_files.py`（7+ exists）、部分 daily_pipeline | 适合 contract 层；可合并冗余 |
| `data/datasets/mock` 字面量 | `test_multilevel_tuning.py` | 测试桩路径，非 live 依赖；**迁时改 tmp stub**（已有 dry-run stub 模式） |
| GPU/CUDA 分支 | `test_models.py` | 建议 `@pytest.mark.gpu` / 可选 skip |
| 大集成烟测 | dataset_builder / incremental_training / models train loop | 建议 `@pytest.mark.integration` 或 `slow` |

---

## 2. 分类清单（T1-A1-T2）

### 2.1 文件级默认：全部 **migrate**

T-heavy 下不做「留在扁平根目录」；每个现有 `test_*.py` 都进入目标分层（见 §3）。语义默认 **保留**，路径 **迁移**。

### 2.2 Batch Del-A — 建议删/合并（函数级；需批准）

> 原则：优先**合并冗余**，避免误删契约。整文件删除本轮 **不建议**。

| ID | 目标 | 类型 | 理由 | 建议 |
|----|------|------|------|------|
| Del-A1 | `test_deployment_files.py::test_deployment_directory_structure` | 冗余 | 与同文件 crontab/service/timer exists 测重复 | **建议删**（合并进既有 exists 测即可） |
| Del-A2 | `test_deployment_files.py` 中纯 `Path.exists` 与内容关键字检查的重复路径 | 可合并 | 可收成参数化 contract 表驱动 | **建议合并**（A2/A3；非必须先删） |
| Del-A3 | 各文件重复的 `sys.path.append(repo_root)`（≥15 处） | 重复样板 | 迁后由 `conftest` / `pythonpath` / editable install 统一 | **建议删样板**（随 A3 搬迁删除重复代码，不是删测例） |

**Batch Del-A 批准问题（请回复）：**

- 是否批准 **Del-A1**（删除 `test_deployment_directory_structure`）？
- Del-A2/A3 作为搬迁期清理，是否默认授权给 A3（无需单独批）？

### 2.3 Batch Hold — 待定（不删，需拍板口径）

| ID | 项 | 说明 | 建议 |
|----|----|------|------|
| Hold-1 | `test_env_guard.py` 仍断言 `ashare-lab` | 生产 guard 默认已是 `py311-private` | **保留文件**；A3 改为测 `py311-private`（或参数化双名） |
| Hold-2 | `fail_under = 90` 现状 | 可能偏高且默认 pytest 不跑 cov | 见 §4；A4 实测后再锁 |
| Hold-3 | `run_develop_min_regression.sh` 子集 | 与未来 `fast` marker 应对齐 | A4 重写为 `-m "not slow and not integration"` 或显式 unit+contract |

### 2.4 Defer R4

| ID | 项 | 结论 |
|----|----|------|
| — | 依赖真实 TuShare 全量湖才能绿的测 | **无**。现有 source/dataset 测均 mock/tmp。 |

---

## 3. 目标架构草案 Arch-v1（T1-A1-T3）

### 3.1 目录树（推荐）

```text
tests/
  conftest.py                      # repo root path, shared tmp helpers
  support/
    factories.py                   # tiny market/frame factories
    assertions.py                  # shared report/protocol asserts（可选）
  unit/
    features/                      # test_features_*
    labels/                        # test_labels, test_one_day_hlc_label
    evaluation/                    # metrics + sanity（纯函数）
    models/                        # shape/loss 单测切片
    recommendation/                # engine/history/trend 纯逻辑
    stock_pool/
    backtest/
    data/                          # normalize/mapping 纯函数
  integration/
    dataset/                       # dataset_builder, sequence_builder, week_split
    pipeline/                      # pipeline, runtime_metadata, config_io
    training/                      # incremental, multilevel dry-run, models train loop
    sources/                       # tushare/odp/source_misc with tmp cache
  contract/
    deployment/                    # deployment_files, daily_pipeline_prod（文件/脚本契约）
    reports/                       # xgboost_report_contract, audit/compare IC CLI 契约
    cli/                           # scripts CLI smoke（stock_pool registry CLI 等）
```

### 3.2 Markers（pytest.ini / pyproject）

| marker | 含义 | 默认 fast？ |
|--------|------|-------------|
| `unit` | 无 IO / 纯逻辑 | yes |
| `integration` | tmp 文件系统 / 多模块编排 | no（full） |
| `contract` | 仓库文件/CLI/报告 schema 契约 | yes（通常快） |
| `slow` | 长训练环、大矩阵 | no |
| `gpu` | CUDA 路径 | no；无 GPU skip |

**选择器约定**

- `fast`（本地默认 / CI PR）：`unit + contract` 且 `not slow and not gpu`
- `full`（merge / nightly）：全量
- 对齐替换：`run_develop_min_regression.sh` → `pytest -q -m "unit or contract" --ignore=...`（A4 定稿）

### 3.3 Fixtures / factories 原则

- 禁止继续复制 `sys.path`；用 `pytest` `pythonpath = ["src", "."]` 或 package 安装
- 共享：假日线框、假 OOS parquet、假 stock pool registry 目录（从 `test_stock_pool_registry` / `test_dataset_builder` 抽）
- scripts 测试：优先 `runpy`/`importlib` + 明确 `PYTHONPATH`，避免每文件 hack

### 3.4 搬迁映射（摘要）

| 现文件 | 目标 |
|--------|------|
| `test_features_*.py` | `unit/features/` |
| `test_labels.py`, `test_one_day_hlc_label.py` | `unit/labels/` |
| `test_evaluation_metrics.py`, `test_sanity_checks.py`, `test_trade_like_panel.py` | `unit/evaluation/` |
| `test_evaluation.py`, `test_compare_ic_reports.py`, `test_audit_ic_reports.py`, `test_xgboost_report_contract.py` | `contract/reports/` 或 `integration`+`contract` 拆分（A3 细拆） |
| `test_models.py`（shape/loss vs train loop） | `unit/models/` + `integration/training/`（建议拆文件） |
| `test_recommendation_*.py`, `test_trend_*`, `test_maturity_gate.py`, `test_validate_recommendations.py` | `unit/recommendation/` + CLI→`contract/cli/` |
| `test_tushare_source.py`, `test_odp_source.py`, `test_source_misc.py` | `integration/sources/` |
| `test_dataset_*.py`, `test_sequence_builder.py`, `test_universe.py` | `integration/dataset/` |
| `test_deployment_files.py`, `test_daily_pipeline_prod.py`, `test_env_guard.py` | `contract/deployment/` |
| `test_monitoring.py` | `unit/` 或 `integration/`（按是否触盘） |
| `test_stock_pool_registry.py` | `unit/stock_pool/` + CLI smoke→`contract/cli/` |
| `test_multilevel_tuning.py`, `test_incremental_training.py`, `test_auto_tune_xgb.py` | `integration/training/` |
| `test_backtest_metrics.py`, `test_strategy_*`, `test_engine_rules.py` | `unit/backtest/` |

### 3.5 Arch-v1 批准问题

请确认是否采纳 **Arch-v1** 作为 A3 搬迁蓝图（可在 A3 微调子路径，但不改 unit/integration/contract 三层）。

---

## 4. Cov Floor 建议（T1-A1-T4 · Acc-balanced）

### 4.1 现状

- 已配置 `fail_under = 90`，但默认 `pytest` / `run_develop_min_regression.sh` **不带** `--cov` → 门禁实际常未触发。
- 本轮 **未** 跑全量 cov（A1 只读；避免把耗时/环境差异当成真理）。

### 4.2 建议草案（待 A4 实测后锁定）

| 层级 | 建议 | 说明 |
|------|------|------|
| 报告 | 始终可 `--cov=ashare_lab --cov-report=term-missing` | 不单独作为唯一成功标准 |
| 过渡 floor（PR fast） | **暂不 fail** 或 `fail_under=60`（仅在显式 cov job） | 避免搬迁期假红 |
| 稳定 floor（full / merge） | **先实测**；若现状 ≥90 则维持 90；若 <90，锁定 **max(70, baseline-2)** | Acc-balanced：有锚但不逼注水 |
| 核心包加严（可选） | `models` / `evaluation` / `recommendation` / `stock_pool` 各自 ≥ 整体 floor | A4 用 coverage omit/include 实现 |
| omit | 保持 scripts 大入口 omit；**不要** omit `src/ashare_lab` 核心包 | |

### 4.3 Cov 批准问题

- 是否同意：**A4 先测 baseline cov → 再提交最终 `fail_under` 数值给你确认**（本 inventory 只锁流程，不锁数字）？
- 是否同意：PR `fast` 默认不强制 cov fail；`full`/merge 才强制？

---

## 5. 批准批次总表（已确认）

| 批次 | 内容 | 状态 |
|------|------|------|
| **Del-A1** | 删除 `test_deployment_directory_structure` | **已批准** → A2 执行 |
| **Del-A2/A3** | 参数化合并 / 删 sys.path 样板 | **不单批**；随 A3 搬迁处理 |
| **Arch-v1** | §3 三层目录 + markers + factories | **已采纳** → A3 蓝图 |
| **Cov-draft** | A4 实测后再锁数字；fast 不强制 cov | **流程同意**；详细数值 **留待 A4** |

保留默认：除批准项外，**不删任何测例文件**；A3 只搬迁（外加随迁样板清理）。

---

## 6. 验收（A1 self-check）

- [x] inventory：文件面 + 分类 + 理由
- [x] 目标架构草案 Arch-v1
- [x] 温和 cov floor 流程建议（数值 A4 实测）
- [x] 无删测 / 无搬迁 diff（相对 checkpoint）
- [x] 未进入 A2/A3/A4/R4 执行

## 7. 下一状态

1. Programmer 批准 Del-A / Arch-v1 / Cov-draft  
2. Init **WT-T1-A2**（仅执行已批删除/合并）  
3. 随后 Init **WT-T1-A3** 按 Arch-v1 搬迁  

## Evidence Refs

- Contract: `.servo/worktrack/WT-T1-A1-contract.md`
- Queue: `.servo/worktrack/WT-T1-A1-plan-task-queue.md`
- Milestone: `.servo/milestone/MS-T1-001.md`
- Intake: `.servo/repo/MS-T1-001-pre-milestone-intake-review.md`
- Coverage config: `pyproject.toml` `[tool.coverage.*]`
- Fast subset: `scripts/run_develop_min_regression.sh`
