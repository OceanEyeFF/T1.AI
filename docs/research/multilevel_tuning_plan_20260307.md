# 多级别模型微调方案（LSTM / XGBoost，2026-03-07，2026-03-08 修订）

## 1. 目标

- 在现有 `weekly rolling retrain + walk-forward` 口径下，系统性扫描关键超参数。
- 保持同窗比较与 `daily-cs-mode=required`，避免评估口径漂移。
- 自动化产出：训练报告、OOS parquet、覆盖率审计、IC 对比结果。

---

## 2. 当前基线快照（来自现有报告）

### 2.1 输入参数（两模型共用）

- 数据集：`data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts`
- 特征模式：`auto`
- 特征数：`53`
- 序列长度：`seq_len=20`
- 窗口：`train/valid/calibration = 104/8/12 weeks`
- 标签口径：`close_to_close`（当前报告）

### 2.2 LSTM 基线

- 结构：`hidden_size=64, num_layers=2, dropout=0.3`
- 训练：`lr=5e-5, optimizer=adamw, weight_decay=1e-5`
- 调度：`cosine_warm_restart`
- 损失：`loss_type=ic_aware, loss_alpha=0.176, weights=(0.1, 0.45, 0.45)`

### 2.3 XGBoost 基线

- 核心：`n_estimators=400, max_depth=6, learning_rate=0.03`
- 采样：`subsample=0.8, colsample_bytree=0.8`
- 正则：`min_child_weight=1, gamma=0, reg_alpha=0, reg_lambda=1`

---

## 3. 多级别微调设计

### L1（低风险单因子）

- LSTM：`lr / dropout / loss_alpha / loss_weights / sign_threshold`
- XGB：`n_estimators / max_depth / learning_rate / subsample / colsample_bytree`
- 目标：快速识别方向性敏感参数。

### L2（中等强度结构与稳健性）

- LSTM：`hidden_size / num_layers / train_window_weeks / calibration_weeks / lr_scheduler / weight_decay`
- XGB：`min_child_weight / gamma / reg_alpha / reg_lambda / early_stopping_rounds / train_window_weeks`
- 目标：提升跨月份稳定性（最差月、连续负月、ICIR）。

### L3（重点交互组合）

- LSTM：窗口与学习率联调、高容量正则化组合、头权重策略组合。
- XGB：深浅树与学习率联调、正则化组合、采样鲁棒组合。
- 目标：在有限组合内验证非线性交互增益。

---

## 4. 自动执行方式

统一入口脚本：`scripts/run_multilevel_tuning.py`

### 4.-1 运行环境前置（必选）

- 训练与调参脚本已接入环境守卫：必须在 `py311-private` conda 环境运行。
- 推荐统一调用方式：`conda run -n py311-private python ...`。

### 4.0 配置文件固化（推荐）

- LSTM 固化配置：`configs/experiments/lstm_rolling_baseline.toml`
- XGBoost 固化配置：`configs/experiments/xgb_rolling_baseline.toml`
- 数据集构建固化配置（市场状态版）：`configs/datasets/market_state_dataset_baseline.toml`
- 数据集构建固化配置（通用版）：`configs/datasets/sequence_dataset_baseline.toml`
- 训练脚本已支持 `--config-file <json/toml>`，CLI 参数仅做覆盖。
- 每次运行会自动写出 `*_effective_config.json`（可追溯实际生效参数）。
- `run_multilevel_tuning.py` 默认即使用上述配置文件，不依赖历史 `output/reports/*.json`。

### 4.1 查看当前参数与输入特征

```bash
conda run -n py311-private python "scripts/run_multilevel_tuning.py" --model both --level all --show-current
```

### 4.2 仅生成执行计划（不训练）

```bash
conda run -n py311-private python "scripts/run_multilevel_tuning.py" --model both --level all
```

### 4.3 实际执行（示例）

```bash
# 单次训练（配置文件驱动）
conda run -n py311-private python "scripts/run_lstm_rolling_retrain_dim19_regime.py" \
  --config-file "configs/experiments/lstm_rolling_baseline.toml" \
  --report "output/reports/lstm_cfg_run_20260307.json" \
  --save-oos-parquet "output/reports/lstm_cfg_run_20260307_oos.parquet"

# 数据集构建（市场状态版，配置文件驱动）
conda run -n py311-private python "scripts/build_sequence_dataset_market_state.py" \
  --config-file "configs/datasets/market_state_dataset_baseline.toml"

# 数据集构建（通用版，配置文件驱动）
conda run -n py311-private python "scripts/build_sequence_dataset.py" \
  --config-file "configs/datasets/sequence_dataset_baseline.toml"

# 单次训练（XGB，配置文件驱动）
conda run -n py311-private python "scripts/run_xgboost_rolling_retrain_regime.py" \
  --config-file "configs/experiments/xgb_rolling_baseline.toml" \
  --report "output/reports/xgb_cfg_run_20260307.json" \
  --save-oos-parquet "output/reports/xgb_cfg_run_20260307_oos.parquet"

# 只跑 LSTM 的 L1
conda run -n py311-private python "scripts/run_multilevel_tuning.py" \
  --model lstm \
  --level L1 \
  --execute

# 跑 XGB 的全部等级，并限制每级最多 16 组
conda run -n py311-private python "scripts/run_multilevel_tuning.py" \
  --model xgb \
  --level all \
  --max-runs-per-level 16 \
  --execute
```

---

## 5. 自动化产出

- `output/reports/<model>_<level>_<idx>_<name>_<tag>.json`
- `output/reports/<model>_<level>_<idx>_<name>_<tag>_oos.parquet`
- `output/reports/tuning_configs/<model>_<level>_<idx>_<name>_<tag>.json`（每个 run 的冻结配置）
- `output/reports/*_coverage.json`（audit）
- `output/reports/*_raw.json/.md` 与 `*_cal.json/.md`（compare）
- `output/reports/multilevel_tuning_manifest_<tag>.json`（全量清单）

---

## 6. 门禁建议

- 固定比较口径：`--daily-cs-mode required`
- 关注指标：`mean(IC_5_10), mean(RankIC_5_10), ICIR, 月胜率, 最差月, 连续负月`
- 若进入交易层候选，再附加成本后指标门禁。

### 6.1 1d H/L/C 头评估补充（LSTM）

- 数据集默认可开启：`include_1d_hlc_labels=true`（见 `configs/datasets/*.toml`）。
- LSTM 会自动识别额外 `label_1d_high/low/close` 头并纳入统一评估。
- 报告中重点查看：
  - `ic_1d_high / ic_1d_low / ic_1d_close`
  - `rank_ic_1d_high / rank_ic_1d_low / rank_ic_1d_close`
  - `order_violation_rate_1d_hlc`
  - `range_mae_1d_hlc`
  - `inside_rate_1d_hlc`

---

## 7. 自动调参（XGBoost / Optuna）

新增脚本：`scripts/auto_tune_xgb.py`

特点：
- 不改动现有训练主流程，逐 trial 直接调用 `run_xgboost_rolling_retrain_regime.py`
- 统一输出 trial 配置、report、OOS parquet、leaderboard 与 best params
- 可配置目标函数权重（IC / RankIC / 月胜率 / 最差月惩罚 / 连续负月惩罚）

示例：

```bash
conda run -n py311-private python "scripts/auto_tune_xgb.py" \
  --base-config-file "configs/experiments/xgb_rolling_baseline.toml" \
  --output-dir "output/reports/auto_tune_xgb_20260308" \
  --study-name "xgb_rolling_auto_tune" \
  --metric-source calibrated \
  --n-trials 40 \
  --n-jobs 1 \
  --top-k 10
```

主要产物：
- `output/reports/auto_tune_xgb_*/summary.json`
- `output/reports/auto_tune_xgb_*/leaderboard.csv`
- `output/reports/auto_tune_xgb_*/best_params.json`
- `output/reports/auto_tune_xgb_*/best_params.toml`
