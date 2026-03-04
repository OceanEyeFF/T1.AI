# dim52（no_hist_hl）资金流动量组单特征消融（2026-03-04）

## 1. 目标
在 `moneyflow_momentum` 9 维内做二级消融（逐特征删除），判断哪些特征可优先裁剪、哪些应保留。

## 2. 实验设置
- 基线：`output/reports/lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json`
- 额外对照：`drop_moneyflow_momentum` 整组删除结果
- 训练配置：与 dim52 基线一致（window24 / seq20 / l1 / w=0.1,0.45,0.45）
- 评估：`daily-CS` raw 与 calibrated
- 自动化脚本：`scripts/run_dim52_group_ablation.py --group-set mfm_single`

## 3. 单特征结果（核心）

### 3.1 raw（daily-CS）
来源：`output/reports/ic_monthly_comparison_dim52_mfm_single_ablation_raw_20260304_mfm_single.json`

| 方案 | mean(IC_5_10) | mean(RankIC_5_10) |
|---|---:|---:|
| baseline dim52 | -0.0089 | 0.0344 |
| drop mf_activity_ratio_20d | 0.0179 | 0.0312 |
| drop mf_large_amount_ratio_ma5 | -0.0158 | -0.0191 |
| drop mf_large_amount_ratio_mom5 | -0.0207 | -0.0014 |
| drop mf_net_amount_ratio_ma5 | -0.0208 | -0.0116 |
| drop mf_retail_amount_ratio_ma5 | -0.0229 | -0.0105 |
| drop mf_net_amount_ratio_mom5 | -0.0284 | -0.0129 |
| drop mf_buy_pressure_amount_ma5 | -0.0388 | -0.0218 |
| drop mf_net_amount_ratio_ma10 | -0.0470 | -0.0237 |
| drop mf_net_amount_ratio_mom10 | -0.0496 | -0.0021 |

### 3.2 calibrated（daily-CS）
来源：`output/reports/ic_monthly_comparison_dim52_mfm_single_ablation_cal_20260304_mfm_single.json`

| 方案 | mean(IC_5_10) | mean(RankIC_5_10) |
|---|---:|---:|
| baseline dim52 | 0.0575 | 0.0761 |
| drop mf_activity_ratio_20d | 0.0364 | -0.0087 |
| drop mf_large_amount_ratio_ma5 | 0.0331 | -0.0325 |
| drop mf_retail_amount_ratio_ma5 | 0.0304 | -0.0235 |
| drop mf_net_amount_ratio_ma5 | 0.0278 | -0.0184 |
| drop mf_net_amount_ratio_mom5 | 0.0220 | -0.0283 |
| drop mf_large_amount_ratio_mom5 | 0.0177 | -0.0248 |
| drop mf_buy_pressure_amount_ma5 | 0.0138 | -0.0298 |
| drop mf_net_amount_ratio_ma10 | -0.0014 | -0.0451 |
| drop mf_net_amount_ratio_mom10 | -0.0242 | -0.0546 |
| drop moneyflow_momentum（整组） | 0.0078 | 0.0127 |

## 4. 结论（客观）
1. 若以 `calibrated` 为主口径，9 个单特征删除全部劣于 baseline。
2. 最小伤害候选（仅相对较小，不代表可无损删除）：
   - `mf_activity_ratio_20d`
   - `mf_large_amount_ratio_ma5`
   - `mf_retail_amount_ratio_ma5`
3. 高价值特征（删除后恶化最明显）：
   - `mf_net_amount_ratio_mom10`
   - `mf_net_amount_ratio_ma10`
   - `mf_buy_pressure_amount_ma5`
4. 现阶段不建议直接删 `moneyflow_momentum` 整组；若必须精简，建议从 `mf_activity_ratio_20d` 单点试删，再做重新调权验证。

## 5. 关键产物
- 覆盖审计：`output/reports/ic_report_oos_coverage_dim52_mfm_single_ablation_20260304_mfm_single_coverage.json`
- 对比 raw：`output/reports/ic_monthly_comparison_dim52_mfm_single_ablation_raw_20260304_mfm_single.json`
- 对比 cal：`output/reports/ic_monthly_comparison_dim52_mfm_single_ablation_cal_20260304_mfm_single.json`
- 单特征报告：`output/reports/lstm_dim52_ablation_mfm_single_drop_*.json`
