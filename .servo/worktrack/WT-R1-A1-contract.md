---
title: "WT-R1-A1: 从 develop 提取 LSTM/XGB 源码并审计差异"
artifact_type: "worktrack-contract"
milestone_id: "MS-R1-001"
worktrack_id: "WT-R1-A1"
status: "active"
node_type: "audit"
created: "2026-06-23"
---

# WT-R1-A1 从 develop 提取 LSTM/XGB 源码并审计差异

## Task Goal

从 `develop` 分支提取 LSTM（3 份 MtlLSTM 副本）和 XGBoost 源码，
分析 3 份 LSTM 副本之间的差异，确认可收敛范围，
为 R1-A4（LSTM 统一实现）和 R1-A5（XGBoost 封装）提供输入。

## Scope

### In Scope

- 从 develop 分支提取以下文件内容：
  - `scripts/run_lstm_rolling_retrain_dim19_regime.py` — MtlLSTM 定义（line ~396）
  - `scripts/run_lstm_dim16_vs_dim19_market.py` — MtlLSTM 定义（line ~70）
  - `scripts/run_lstm_walkforward_sign_calibration.py` — MtlLSTM 定义（line ~61）
  - `scripts/run_xgboost_rolling_retrain_regime.py` — xgb.XGBRegressor 调用模式
  - `scripts/auto_tune_xgb.py` — Optuna 超参搜索包装
- 审计 3 份 MtlLSTM 差异（架构、超参、forward、训练逻辑）
- 产出结构化差异矩阵
- 确认可收敛范围

### Out Of Scope

- 不修改任何文件
- 不创建新代码
- 不运行训练

## Completion Criteria

- [ ] 3 份 MtlLSTM 源码已提取并记录
- [ ] XGBoost 脚本调用模式已记录
- [ ] 差异矩阵已产出
- [ ] 可收敛范围已确认
