# 简验结论报告（2026-03-05）

## 1. 目的
对“当前参数点稳定性不足”做快速复核，验证两件事：

1. 换 seed 后表现是否显著波动；
2. 换股票池后表现是否显著变化。

## 2. 参数与口径
- 脚本：`scripts/run_lstm_rolling_retrain_dim19_regime.py`
- 核心参数：`seq20 + window24 + w(0.1/0.45/0.45) + ic_aware(alpha=0.176) + calibration_months=3 + sign_threshold=0.02`
- 评估：strict `daily-CS`（`--daily-cs-mode required`）
- 统一月份：`2025-08` 到 `2026-01`

## 3. 验证结果

### 3.1 同参数，换 seed（quick8 已验证）
- `seed42`（最佳记录）`mean(IC_5_10)=0.1025`，门禁 PASS
- `seed7`：`0.0401`，门禁 FAIL
- `seed99`：`-0.0641`，门禁 FAIL

对应文件：
- `output/reports/ic_monthly_comparison_20260305_microgrid_seed_stability_cal.md`

### 3.2 同参数，换池（quick8 -> pool2 ETF）
固定 `seed42` 对比：

- quick8：`mean(IC_5_10)=0.1025`，门禁 PASS
- pool2 ETF：`mean(IC_5_10)=0.0694`，门禁 FAIL（`月胜率 33.3%`, `最差月 -0.1818`）

对应文件：
- `output/reports/ic_monthly_comparison_20260305_pool_switch_simple_cal.md`

### 3.3 同池（pool2 ETF）再换 seed
- `seed42`：`mean(IC_5_10)=0.0694`（cal）
- `seed99`：`mean(IC_5_10)=-0.1528`（cal）

两者均 FAIL，且差异明显。

对应文件：
- `output/reports/ic_monthly_comparison_20260305_pool2_seed_simple_cal.md`
- `output/reports/ic_monthly_comparison_20260305_pool2_seed_simple_raw.md`

## 4. 结论
- “当前参数点对 seed 和样本池都敏感，稳定性不足”这一结论成立。
- 当前仓库可用的“换池”数据主要是 `pool2 ETF`（2 只标的），可作为快速旁证；若要形成更强外推结论，需要补充真正多股票池（如 30+ 或 70 只）的同口径复验。
