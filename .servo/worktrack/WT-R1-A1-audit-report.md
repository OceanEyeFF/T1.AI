---
title: "WT-R1-A1 Audit Report: LSTM/XGB Source Extraction & Divergence Analysis"
artifact_type: "audit-report"
worktrack_id: "WT-R1-A1"
milestone_id: "MS-R1-001"
created: "2026-06-23"
---

# WT-R1-A1 审计报告

## 1. 源码来源

所有源码从 `develop` 分支（HEAD: `1204de8`）提取。

### LSTM — 3 份内联副本

| # | 文件 | 行号 | 类名 | 用途 |
|---|---|---|---|---|
| 1 | `scripts/run_lstm_rolling_retrain_dim19_regime.py` | ~396 | `class MtlLSTM` | Rolling retrain + regime-aware 训练 |
| 2 | `scripts/run_lstm_dim16_vs_dim19_market.py` | ~70 | `class MtlLSTM` | dim16 vs dim19 market-state 对比 |
| 3 | `scripts/run_lstm_walkforward_sign_calibration.py` | ~61 | `class MtlLSTM` | Walkforward 符号校准（仅推理） |

### XGBoost — 无封装类

| # | 文件 | 核心 | 用途 |
|---|---|---|---|
| 4 | `scripts/run_xgboost_rolling_retrain_regime.py` | `XgbConfig` + `_build_xgb_regressor()` | Rolling retrain |
| 5 | `scripts/auto_tune_xgb.py` | subprocess 调用 #4 | Optuna 超参搜索 |

---

## 2. MtlLSTM 差异矩阵

| 维度 | #1 (rolling dim19) | #2 (dim16 vs dim19) | #3 (walkforward) |
|---|---|---|---|
| **head 类型** | `nn.ModuleDict`（通用 pred_cols） | 具名 `head_3d/5d/10d` | 具名 `head_3d/5d/10d` |
| **Norm** | `_build_norm()` → LayerNorm / RMSNorm | `nn.LayerNorm`（硬编码） | `nn.LayerNorm`（硬编码） |
| **loss_weights** | 可配置 tuple | 硬编码 `[1.0, 1.0, 1.0]` | N/A（仅推理） |
| **loss_type** | l1 / ic_aware / rank_aware / ic_rank_aware | 仅 l1（`compute_mtl_loss`） | N/A |
| **forward 返回** | `dict` 或 `(dict, dict)` | `dict` 或 `(dict, dict)` | `tuple[Tensor, Tensor, Tensor]` |
| **labels 处理** | 支持（训练模式） | 支持（训练模式） | 不支持（仅预测） |
| **助手函数** | `_masked_l1_loss`、`_pearson_corr`、`_pairwise_rank_logistic_loss`、`RMSNorm` | `_summarize`、`_eval_model` | `_infer_model_shape`、`ModelShape`、`_predict` |
| **额外内容** | 同一文件还定义了 `MtlTransformer` | 无 | 无 |
| **可配置参数** | input_dim, hidden_size, num_layers, dropout, pred_cols, loss_weights, loss_type, loss_alpha, ic_rank_beta, norm_type, norm_eps | input_dim, hidden_size, num_layers, dropout | input_dim, hidden_size, num_layers, dropout |

---

## 3. XGBoost 调用模式

```python
@dataclass(frozen=True)
class XgbConfig:
    n_estimators, max_depth, learning_rate, subsample, colsample_bytree,
    min_child_weight, gamma, reg_alpha, reg_lambda,
    n_jobs, early_stopping_rounds, device, random_seed

def _build_xgb_regressor(cfg, seed) -> xgb.XGBRegressor:
    return xgb.XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        device=cfg.device,
        random_state=seed,
        eval_metric="mae",
        early_stopping_rounds=...,
        **cfg_fields
    )

def _fit_predict_multihorizon(x_train, y_train, x_valid, y_valid, x_test, cfg, month_seed):
    # 3-horizon loop: 对每个 horizon 独立 fit XGBRegressor
    models = [None, None, None]  # 3 个独立模型
    for h in range(3):
        model = _build_xgb_regressor(cfg, seed)
        model.fit(x_train, y_train[:, h], eval_set=[(x_valid, y_valid[:, h])])
        test_pred[:, h] = model.predict(x_test)
```

**关键发现**：XGBoost 是 3 个独立模型（每个 horizon 一个），不是多任务模型。

---

## 4. 可收敛范围

### LSTM — 收敛为统一 `MtlLSTM`

| 特性 | 来源 | 纳入 |
|---|---|---|
| ModuleDict heads（通用） | #1 | ✅ 采纳 |
| 可配置 norm（LayerNorm / RMSNorm） | #1 | ✅ 采纳 |
| 全部 4 种 loss_type | #1 | ✅ 采纳 |
| 可配置 loss_weights | #1 | ✅ 采纳 |
| `ModelShape` + `_infer_model_shape` | #3 | ✅ 采纳（作为静态方法） |
| `forward()` 返回 `dict`（预测）/ `(dict, dict)`（训练） | #1/#2 | ✅ 统一签名 |
| 具名 heads（head_3d/5d/10d） | #2/#3 | ❌ 废弃（ModuleDict 更通用） |
| `_summarize` / `_eval_model` | #2 | ❌ 留在脚本层（评估逻辑不是模型） |
| `_predict` batch inference | #3 | ❌ 留在脚本层 |

### XGBoost — 封装为 `XGBoostModel`

| 特性 | 纳入 |
|---|---|
| `XgbConfig` dataclass | ✅ 迁移到 `models/xgboost/config.py` |
| `_build_xgb_regressor()` | ✅ 封装为 `XGBoostModel.__init__` |
| `_fit_predict_multihorizon()` | ✅ 封装为 `XGBoostModel._fit_multihorizon` |
| 3-model multi-horizon 架构 | ✅ 保持（每个 horizon 独立 XGBRegressor） |

---

## 5. 不在收敛范围内的内容

| 内容 | 原因 |
|---|---|
| LSTM #1 中的 `MtlTransformer` | 是另一个模型类，不属于 LSTM 治理 |
| 各脚本的训练循环、数据加载、评估逻辑 | 属于 pipeline 层，不在模型层治理范围 |
| `auto_tune_xgb.py` | 超参搜索脚本，通过 subprocess 调用，重构后需验证兼容性但不需要迁移 |
| 脚本级 helper 函数（`_extract_xy`, `_set_seed`, `_months_to_weeks` 等） | pipeline 层工具函数 |

---

## 6. 输出

本报告为 WT-R1-A2（ModelABC 接口设计）和 WT-R1-A4/R1-A5（LSTM/XGB 实现）提供输入约束。
