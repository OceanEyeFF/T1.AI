# X×Y×Z 组合测试矩阵

> MS-R2-001 | 2026-06-23

## 三维独立轴

```
X: 选股池    pools/                    → 不同的股票代码集合
Y: 模型架构  src/ashare_lab/models/    → LSTM / XGBoost / Transformer（config 调参）
Z: 配置档案  inputs/configs/profiles/  → 输入维度 × 回溯窗口 × 输出 horizon
```

## 测试流程

### 1. 全量扫荡（Sweep）

X×Y×Z 两两组合，测试每种配对的效果，选出 IC 表现最好的组合。

```
实验定义：inputs/configs/experiments/sweep_001.toml
输出：outputs/reports/{experiment_id}/ic_series.json
```

### 2. 滚动验证（Rolling）

全量扫荡养蛊得到的最佳配对，每个星期一次微调，验证 IC 长期稳定性。

```
For each week W:
    Fine-tune(train_data[W-k:W]) → IC(test_data[W])
    记录到 certified.json
```

### 3. 认证注册（Certify）

通过滚动验证的配对写入 `workspace/registry/certified.json`：

```json
{
  "pair_id": "low_manipulation_xgb_10feat_3d5d10d",
  "pool": "custom_low_manipulation",
  "model": "xgboost",
  "config_profile": "10feat_3d5d10d",
  "checkpoint": "workspace/checkpoints/low_manipulation_xgb_10feat.pt",
  "ic_series": {
    "3d": {"mean": 0.045, "std": 0.02},
    "5d": {"mean": 0.038, "std": 0.025},
    "10d": {"mean": 0.031, "std": 0.028}
  },
  "certified_at": "2026-06-23"
}
```

## 实验配置文件格式

`inputs/configs/experiments/<name>.toml`:

```toml
experiment_id = "sweep_001"
description = "首次全量扫荡"

[[combinations]]
pool = "custom_low_manipulation"
model = "xgboost"
profile = "10feat_3d5d10d"

[[combinations]]
pool = "custom_low_manipulation"
model = "transformer"
profile = "10feat_3d5d10d"
```

## 配置档案格式

`inputs/configs/profiles/<name>.toml`:

```toml
profile_id = "10feat_3d5d10d"
input_dims = 10           # 输入特征维度
lookback_days = 20        # 回溯窗口（天）
output_horizons = [3, 5, 10]  # 输出头（交易日）
label_type = "forward_return"  # 标签类型
```
