---
title: "WT-R2-A1 Change-Impact Map"
artifact_type: "audit-report"
milestone_id: "MS-R2-001"
worktrack_id: "WT-R2-A1"
created: "2026-06-23"
audit_scope: "全量路径引用扫描"
---

# WT-R2-A1 Change-Impact Map

## 目录移动计划与影响文件矩阵

### M1: `data/cache/` → `inputs/data/cache/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/daily_pipeline.py` | 181 | `Path(str(selected.get("cache_dir") or "data/cache"))` | `inputs/data/cache` |
| 2 | `scripts/build_dataset_multi_stock.py` | 126 | `cache_dir=Path("data/cache")` | `inputs/data/cache` |
| 3 | `scripts/build_sequence_dataset.py` | 288 | `--cache-dir default="data/cache"` | `inputs/data/cache` |
| 4 | `scripts/run_backtest.py` | 26 | `--cache-dir default="data/cache"` | `inputs/data/cache` |
| 5 | `scripts/load_env.sh` | 51 | `CACHE_DIR:-data/cache` | `inputs/data/cache` |
| 6 | `scripts/clean_data.sh` | 19 | `CACHE_DIR="data/cache"` | `inputs/data/cache` |
| 7 | `configs/data_source.yaml` | 9,17 | `cache_dir: "data/cache"` | `inputs/data/cache` |
| 8 | `configs/datasets/market_state_dataset_baseline.toml` | 3 | `cache_dir = "data/cache"` | `inputs/data/cache` |
| 9 | `configs/datasets/sequence_dataset_baseline.toml` | 12 | `cache_dir = "data/cache"` | `inputs/data/cache` |
| 10 | `src/ashare_lab/dataset/builder.py` | 53 | `Path("data/cache")` | `inputs/data/cache` |
| 11 | `src/ashare_lab/recommendation/validator.py` | 153,190,237,280 | `Path("data/cache")` | `inputs/data/cache` |
| 12 | `src/ashare_lab/stock_pool/low_manipulation/strategy.py` | 351 | `"data/cache"` | `inputs/data/cache` |
| 13 | `deployment/crontab.example` | 11 | `/path/to/T1.AI/data/cache` | `/path/to/T1.AI/inputs/data/cache` |

### M2: `data/datasets/` → DELETE（激进清理）

| # | 文件 | 行号 | 当前引用 | 动作 |
|---|------|------|---------|------|
| 1 | `scripts/build_dataset_multi_stock.py` | 127 | `output_dir=Path("data/datasets")` | 改为 `workspace/datasets/` 或删除 |
| 2 | `scripts/train_baseline_models.py` | 164 | `--dataset default="data/datasets/sequence_v1"` | 改为 `workspace/datasets/` |
| 3 | `scripts/build_sequence_dataset.py` | 289 | `--output-dir default="data/datasets"` | 改为 `workspace/datasets/` |
| 4 | `scripts/run_lstm_dim16_vs_dim19_market.py` | 263 | `--dataset-dir default="data/datasets/lstm_sector70_19d_mkt_20210101_20260120"` | 删除（旧产物） |
| 5 | `scripts/run_dim52_group_ablation.py` | 333,410 | `"data/datasets/lstm_quick8_52d..."` | 删除（旧产物） |
| 6 | `scripts/clean_data.sh` | 18 | `DATASETS_DIR="data/datasets"` | 删除或改 `workspace/datasets/` |
| 7 | `scripts/evaluate_model.py` | 7 | `--dataset data/datasets/dataset_65stocks_2021q3_2025q4` | 删除（旧产物） |
| 8 | `scripts/train_model.py` | 6 | `--dataset data/datasets/...` (docstring) | 更新 docstring |
| 9 | `src/ashare_lab/dataset/builder.py` | 54 | `Path("data/datasets")` | 改为 `workspace/datasets/` |
| 10 | `configs/experiments/xgb_rolling_baseline.toml` | 2 | `dataset_dir = "data/datasets/..."` | 删除（旧产物） |
| 11 | `configs/experiments/lstm_rolling_baseline.toml` | 2 | `dataset_dir = "data/datasets/..."` | 删除（旧产物） |
| 12 | `configs/experiments/xgb_rolling_fastpilot.toml` | 2 | `dataset_dir = "data/datasets/..."` | 删除（旧产物） |
| 13 | `configs/experiments/lstm_rolling_fastpilot.toml` | 2 | `dataset_dir = "data/datasets/..."` | 删除（旧产物） |
| 14 | `configs/datasets/market_state_dataset_baseline.toml` | 21 | `output_dir = "data/datasets/..."` | 改为 `workspace/datasets/` |
| 15 | `configs/datasets/sequence_dataset_baseline.toml` | 13 | `output_dir = "data/datasets/..."` | 改为 `workspace/datasets/` |
| 16 | 物理删除 | — | `data/datasets/_smoke_*` (34 个文件) | `rm -rf` |

### M3: `data/recommendations/` → `outputs/predictions/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `src/ashare_lab/pipeline/orchestrator/core.py` | 46,47 | `Path("data/recommendations")`, `Path("data/recommendations/validation")` | `outputs/predictions`, `outputs/reports` |
| 2 | `src/ashare_lab/pipeline/orchestrator/core.py` | 74,75 | `Path("data/recommendations")`, `Path("data/recommendations/validation")` | `outputs/predictions`, `outputs/reports` |
| 3 | `configs/pipeline.yaml` | 4,5 | `recommendation_dir: "data/recommendations"`, `report_dir: "data/recommendations/validation"` | `outputs/predictions`, `outputs/reports` |

### M4: `data/recommendations.db` → `workspace/recommendations.db`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `src/ashare_lab/pipeline/orchestrator/core.py` | 48,76 | `Path("data/recommendations.db")` | `outputs/recommendations.db` |
| 2 | `src/ashare_lab/recommendation/history.py` | 228 | `"data/recommendations.db"` | `outputs/recommendations.db` |
| 3 | `configs/pipeline.yaml` | 6 | `db_path: "data/recommendations.db"` | `outputs/recommendations.db` |

### M5: `configs/pipeline.yaml` → `inputs/configs/pipeline.toml`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/daily_pipeline.py` | 54 | `--config default="configs/pipeline.yaml"` | `inputs/configs/pipeline.toml` |
| 2 | `scripts/daily_pipeline.sh` | 34 | `--config configs/pipeline.yaml` | `inputs/configs/pipeline.toml` |

### M6: `configs/data_source.yaml` → `inputs/configs/data_source.toml`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/daily_pipeline.py` | 55 | `--data-source-config default="configs/data_source.yaml"` | `inputs/configs/data_source.toml` |

### M7: `configs/model_mtl.yaml` → `inputs/configs/profiles/model_mtl.toml`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/daily_pipeline.py` | 57 | `--model-config default="configs/model_mtl.yaml"` | `inputs/configs/profiles/model_mtl.toml` |
| 2 | `configs/model_mtl.yaml` | 42 | `warm_start_checkpoint: "models/latest_mtl.pt"` | 删除（激进清理） |
| 3 | `configs/model_mtl.yaml` | 43 | `save_checkpoint: "models/latest_mtl.pt"` | 删除（激进清理） |

### M8: `configs/datasets/` → `inputs/configs/profiles/`

| # | 文件 | 内容 | 动作 |
|---|------|------|------|
| 1 | `configs/datasets/market_state_dataset_baseline.toml` | 数据集构建配置 | 移动到 `inputs/configs/profiles/` |
| 2 | `configs/datasets/sequence_dataset_baseline.toml` | 数据集构建配置 | 移动到 `inputs/configs/profiles/` |

### M9: `configs/experiments/` → `inputs/configs/experiments/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/run_multilevel_tuning.py` | 34 | `DEFAULT_LSTM_CONFIG = "configs/experiments/lstm_rolling_baseline.toml"` | `inputs/configs/experiments/` |
| 2 | `scripts/run_multilevel_tuning.py` | 35 | `DEFAULT_XGB_CONFIG = "configs/experiments/xgb_rolling_baseline.toml"` | `inputs/configs/experiments/` |
| 3 | `configs/experiments/` 下 4 个文件 | — | 物理移动 | `mv configs/experiments/* inputs/configs/experiments/` |

### M10: `configs/stock_pools/` → `inputs/pools/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `configs/stock_pools/custom_low_manipulation_v1.toml` | 7,8 | `"configs/stock_pools/..."` | `inputs/pools/low_manipulation/...` |
| 2 | `scripts/build_sequence_dataset.py` | 280 | `--stock-pool-registry-dir default="configs/stock_pools"` | `inputs/pools` |
| 3 | `scripts/build_sequence_dataset.py` | 281 | `--stock-pool-export-dir default="output/stock_pools"` | `workspace/stock_pools` |

### M11: `models/*.pt` → DELETE（激进清理，基于 AkShare）

| # | 文件 | 行号 | 当前引用 | 动作 |
|---|------|------|---------|------|
| 1 | `scripts/daily_pipeline.py` | 56 | `--model default="models/latest_mtl.pt"` | 清除 default，或改为 `workspace/checkpoints/` |
| 2 | `scripts/generate_daily_recommendations.py` | 66 | `--model default="models/best_mtl.pt"` | 清除 default，或改为 `workspace/checkpoints/` |
| 3 | `scripts/run_lstm_dim16_vs_dim19_market.py` | 244 | `ckpt = Path(f"models/best_lstm_sector70_{name}.pt")` | 改为 `workspace/checkpoints/` |
| 4 | `configs/model_mtl.yaml` | 42,43 | checkpoint 路径指向 `models/` | 改为 `workspace/checkpoints/` |
| 5 | `.gitignore` | — | `*.pt *.pth *.ckpt`（已全局排除） | 确认 `workspace/checkpoints/` 被 gitignore 覆盖 |

### M12: `output/recommendations/` → `outputs/predictions/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/generate_daily_recommendations.py` | 8-12,17,67 | `output/recommendations` | `outputs/predictions` |
| 2 | `.gitignore` | — | `output/recommendations/` | `outputs/predictions/` |

### M13: `output/reports/` → `outputs/reports/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `scripts/runtime_metadata.py` | 188 | `"output/reports"` | `outputs/reports` |
| 2 | `scripts/run_multilevel_tuning.py` | 796 | `--output-dir default="output/reports"` | `outputs/reports` |
| 3 | `scripts/run_dim52_group_ablation.py` | 337,346 | `"output/reports/..."` | `outputs/reports/...` |
| 4 | `scripts/run_lstm_dim16_vs_dim19_market.py` | 273 | `--report default="output/reports/..."` | `outputs/reports/...` |
| 5 | `.gitignore` | — | `output/reports/` | `outputs/reports/` |

### M14: `logs/` → `workspace/runs/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `src/ashare_lab/pipeline/orchestrator/core.py` | 49,77 | `Path("logs/pipeline_runs.jsonl")` | `workspace/runs/pipeline_runs.jsonl` |
| 2 | `configs/pipeline.yaml` | 7 | `run_meta_path: "logs/pipeline_runs.jsonl"` | `workspace/runs/pipeline_runs.jsonl` |
| 3 | `configs/pipeline.yaml` | 19 | `file: "logs/pipeline.log"` | `workspace/runs/pipeline.log` |
| 4 | `scripts/daily_pipeline.sh` | 29,35,40 | `logs/pipeline.log` | `workspace/runs/pipeline.log` |
| 5 | `deployment/crontab.example` | 8 | `logs/cron.log` | `workspace/runs/cron.log` |
| 6 | `deployment/daily-pipeline.service` | 11,12 | `logs/pipeline.log` | `workspace/runs/pipeline.log` |
| 7 | `.gitignore` | — | `logs/*.log logs/*.csv` | `workspace/runs/*.log workspace/runs/*.csv` |

### M15: `runs/checkpoints/` → `workspace/checkpoints/`

| # | 文件 | 行号 | 当前引用 | 修改为 |
|---|------|------|---------|--------|
| 1 | `src/ashare_lab/training/trainer.py` | 46 | `save_dir: Path = Path("runs/checkpoints")` | `workspace/checkpoints` |
| 2 | `scripts/train_model.py` | 95 | `default="runs/checkpoints"` | `workspace/checkpoints` |
| 3 | `scripts/evaluate_model.py` | 6 | `--checkpoint runs/transformer_12layers/best_model.pt` (docstring) | 更新 docstring |
| 4 | `scripts/run_sanity_checks.py` | 8-10 | `runs/<exp>/...` (docstring) | 更新 docstring |
| 5 | `.gitignore` | — | `runs/` | 改为 `workspace/checkpoints/` |

### M16: `experiments/` → DISSOLVE

| # | 文件 | 当前引用 | 动作 |
|---|------|---------|------|
| 1 | `experiments/XGBoost_pool_comparison/experiment_design.md` | 唯一文件 | 移动到 `docs/research/` |
| 2 | 物理删除 | `experiments/` 目录 | `rm -rf experiments/` |

### M17: `scripts/__pycache__/` → gitignore 排除

| # | 文件 | 动作 |
|---|------|------|
| 1 | `scripts/__pycache__/` | `git rm -r --cached scripts/__pycache__/` |

---

## Deployment 路径引用（额外）

| # | 文件 | 行号 | 当前引用 |
|---|------|------|---------|
| 1 | `deployment/daily-pipeline.service` | 10 | `ExecStart=/home/oceaneye/gitee/T1.AI/scripts/daily_pipeline.sh` |
| 2 | `deployment/daily-pipeline.service` | 11 | `StandardOutput=.../logs/pipeline.log` |
| 3 | `deployment/daily-pipeline.service` | 12 | `StandardError=.../logs/pipeline.log` |

注意：`deployment/` 路径包含绝对路径 `/home/oceaneye/gitee/T1.AI`（旧路径），需更新为实际部署路径。

---

## `.gitignore` 规则更新汇总

| 当前规则 | 修改为 |
|---------|--------|
| `data/cache/` | `inputs/data/cache/` |
| `data/datasets/` | 删除（目录不再存在） |
| `runs/` | `workspace/checkpoints/` |
| `logs/*.log` | `workspace/runs/*.log` |
| `logs/*.csv` | `workspace/runs/*.csv` |
| `output/recommendations/` | `outputs/predictions/` |
| `output/reports/` | `outputs/reports/` |
| `.logs/` | 删除（不再使用） |
| `*.pt *.pth *.ckpt` | 保留（全局排除） |
| 新增 | `scripts/__pycache__/` |

---

## 文件影响统计

| 类别 | 受影响文件数 |
|------|------------|
| `scripts/*.py` | 14 |
| `scripts/*.sh` | 3 |
| `configs/*.yaml` | 2 |
| `configs/*.toml` | 8 |
| `src/ashare_lab/**/*.py` | 6 |
| `deployment/*` | 2 |
| `.gitignore` | 1 |
| 根 `.md` | 3 (README, CLAUDE, ROADMAP) |
| `docs/**/*.md` | ~25（交叉引用路径不变，内容提及需检查） |
| **合计** | **~64 文件** |

---

## 风险标注

| 风险 | 严重度 | 说明 |
|------|--------|------|
| `daily_pipeline.py` 路径断裂 | HIGH | 生产脚本，4 个硬编码路径，修复后需 dry-run 验证 |
| `deployment/` systemd 路径 | HIGH | 绝对路径引用旧 `/home/oceaneye/gitee/` 路径 |
| `configs/experiments/` 引用 `data/datasets/` | MEDIUM | 4 个实验配置引用旧的 `quick8` 数据集路径，激进清理后配置本身也需删除 |
| `models/*.pt` 删除后引用悬空 | MEDIUM | `daily_pipeline.py` 和 `generate_daily_recommendations.py` 的 default 参数指向旧 checkpoint |
| `docs/` 交叉引用 | LOW | ~25 个文档内部链接使用相对路径，目录移动后相对路径不变（文档在 `docs/` 内移动才需要更新） |
| `CLAUDE.md` 架构图 | LOW | 79-85 行有 `src/ashare_lab/` 目录树，重组后需更新 |

---

## 审计结论

**change-impact map 已就绪**，共识别 17 组目录移动/删除操作，影响 ~64 个文件。

**WT-R2-A1 完成。** 可交接到 WT-R2-A2（inputs/ 区落成）。
