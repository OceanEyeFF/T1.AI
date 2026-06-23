---
title: "WT-R2-A1: 全量路径引用审计 → change-impact map"
artifact_type: "worktrack-contract"
milestone_id: "MS-R2-001"
worktrack_id: "WT-R2-A1"
status: "completed"
node_type: "audit"
created: "2026-06-23"
completed: "2026-06-23"
branch: "milestone/MS-R2-001-repo-restructure"
---

# WT-R2-A1 全量路径引用审计 → change-impact map

## Audit Findings → Cross-Worktrack ToDo

以下 3 项发现不属于 A1（审计只读），需要后续 Worktrack 执行：

### Todo 1: deployment/ 改用相对路径

**文件**: `deployment/daily-pipeline.service`
**问题**: 硬编码绝对路径 `/home/oceaneye/gitee/T1.AI`（旧环境，不匹配当前 `/home/oceaneye/github/T1.AI`）
**修复**:

- `WorkingDirectory` → 更新为当前实际路径
- `ExecStart` → `./scripts/daily_pipeline.sh`（相对 WorkingDirectory）
- `StandardOutput/Error` → `workspace/runs/pipeline.log`（相对 + 新路径）
**归属**: WT-R2-A6（路径引用全量修复）

### Todo 2: 老数据集清理 + 影响面检查

**被引用文件**: `configs/experiments/{lstm,xgb}_rolling_{baseline,fastpilot}.toml`（4 个）
**问题**: 全部引用 `data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts`
**影响面**:

- `scripts/run_multilevel_tuning.py` — DEFAULT_LSTM_CONFIG / DEFAULT_XGB_CONFIG 引用这 4 个 TOML
- `scripts/run_dim52_group_ablation.py` — `--dataset-dir` default 引用同一路径
- `scripts/run_lstm_dim16_vs_dim19_market.py` — `--dataset-dir` default 引用旧数据集
- `scripts/train_baseline_models.py` — `--dataset` default 引用 `data/datasets/sequence_v1`
- `scripts/evaluate_model.py` — docstring 示例引用旧路径
**结论**: 4 个实验 TOML + 涉及的脚本 defaults 全部清理
**归属**: WT-R2-A5（历史残留清理）

### Todo 3: 旧 checkpoint 删除后清除 defaults

**文件**:

- `scripts/daily_pipeline.py:56` — `default="models/latest_mtl.pt"` → 清为 `default=None`（生产模式需显式传入）
- `scripts/generate_daily_recommendations.py:66` — `default="models/best_mtl.pt"` → 清为 `default=None`
- `configs/model_mtl.yaml:42,43` — checkpoint 路径 → 清为 `""`
**归属**: WT-R2-A5（历史残留清理）+ WT-R2-A6（路径修复）

## Completion

- [x] T1: 扫描 scripts/ 路径引用
- [x] T2: 扫描 configs/ 路径引用
- [x] T3: 扫描 src/ 硬编码路径
- [x] T4: 扫描 deployment/ 路径引用
- [x] T5: 扫描 docs/ 交叉引用
- [x] T6: 审计 .gitignore 规则
- [x] T7: 扫描根 .md 目录引用
- [x] T8: 汇总 change-impact map → `.servo/worktrack/WT-R2-A1-change-impact-map.md`

## Deliverables

- [x] `.servo/worktrack/WT-R2-A1-change-impact-map.md` — 17 组移动操作 × ~64 受影响文件的完整矩阵
