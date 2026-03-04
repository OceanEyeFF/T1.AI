# dim52（no_hist_hl）按大类逐组消融实验（2026-03-04）

## 1. 实验目标
- 对当前最佳基线 `dim52_no_hist_hl` 的 52 维特征做“按大类逐组删除”消融。
- 统一使用 rolling + daily-CS 口径，观察各大类对 `IC_5_10 / RankIC_5_10` 与月度稳定性的边际贡献。

## 2. 统一配置
- 基线报告：`output/reports/lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json`
- OOS 月份：`2025-08` ~ `2026-01`（6 个月）
- 训练配置：
  - `train_window_months=24`
  - `seq_len=20`
  - `loss_type=l1`
  - `loss_weights=(0.1, 0.45, 0.45)`
  - 其余参数与基线保持一致
- 自动化脚本：`scripts/run_dim52_group_ablation.py`

## 3. 分组定义（覆盖 52 维）
1. `price_tech_core`（14）
2. `turnover_volume_micro`（6）
3. `valuation_size`（7）
4. `moneyflow_structure`（13）
5. `moneyflow_momentum`（9）
6. `market_state`（3）

## 4. 结果总表（Daily-CS）

### 4.1 raw 口径
来源：`output/reports/ic_monthly_comparison_dim52_group_ablation_raw_20260304_gabl52.json`

| 方案 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 |
|---|---:|---:|---:|---:|---:|
| baseline dim52 | -0.0089 | 0.0344 | 50.0% | -0.4008 | 1 |
| drop price_tech_core | -0.0219 | -0.0568 | 66.7% | -0.4433 | 2 |
| drop turnover_volume_micro | -0.1428 | -0.1076 | 16.7% | -0.3620 | 5 |
| drop valuation_size | -0.0442 | -0.0091 | 50.0% | -0.3697 | 3 |
| drop moneyflow_structure | -0.0203 | -0.0213 | 50.0% | -0.2465 | 2 |
| drop moneyflow_momentum | -0.0293 | 0.0261 | 50.0% | -0.1248 | 3 |
| drop market_state | -0.1236 | -0.0714 | 16.7% | -0.3588 | 5 |

### 4.2 calibrated 口径
来源：`output/reports/ic_monthly_comparison_dim52_group_ablation_cal_20260304_gabl52.json`

| 方案 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 |
|---|---:|---:|---:|---:|---:|
| baseline dim52 | 0.0575 | 0.0761 | 66.7% | -0.0341 | 1 |
| drop price_tech_core | -0.0352 | -0.0581 | 50.0% | -0.4433 | 2 |
| drop turnover_volume_micro | -0.0512 | -0.0514 | 16.7% | -0.0990 | 5 |
| drop valuation_size | -0.0550 | -0.0281 | 33.3% | -0.3697 | 2 |
| drop moneyflow_structure | -0.0429 | -0.0444 | 50.0% | -0.2465 | 2 |
| drop moneyflow_momentum | 0.0078 | 0.0127 | 50.0% | -0.0806 | 2 |
| drop market_state | -0.0328 | -0.0099 | 33.3% | -0.1179 | 4 |

## 5. 相对基线的降幅（calibrated）
- baseline（dim52）对照：`IC_5_10=0.0575`，`RankIC_5_10=0.0761`
- 删除各大类后的变化（`delta = ablation - baseline`）：

| 删除组 | ΔIC_5_10 | ΔRankIC_5_10 |
|---|---:|---:|
| drop valuation_size | -0.1125 | -0.1042 |
| drop turnover_volume_micro | -0.1087 | -0.1274 |
| drop moneyflow_structure | -0.1004 | -0.1205 |
| drop price_tech_core | -0.0927 | -0.1341 |
| drop market_state | -0.0902 | -0.0860 |
| drop moneyflow_momentum | -0.0497 | -0.0634 |

## 6. 结论
1. 6 个大类全部为正贡献，删除任一组都使结果退化（raw/cal 一致）。
2. 对当前基线最关键的几组（综合看 IC/RankIC 降幅与稳定性）是：
   - `turnover_volume_micro`
   - `valuation_size`
   - `moneyflow_structure`
   - `price_tech_core`
3. `moneyflow_momentum` 相对“次关键”，但删除后仍显著劣化，暂不建议删减。
4. 在当前 52 维基线上，更合理的下一步是“组内精修”而不是“大类整组裁剪”：
   - 先在 `moneyflow_momentum` 内做细粒度单特征/小子组裁剪；
   - 其余 5 大类保持完整，优先做损失函数与权重优化。

## 7. 关键产物
- 覆盖审计：`output/reports/ic_report_oos_coverage_dim52_group_ablation_20260304_gabl52_coverage.json`
- 对比结果（raw）：`output/reports/ic_monthly_comparison_dim52_group_ablation_raw_20260304_gabl52.json`
- 对比结果（cal）：`output/reports/ic_monthly_comparison_dim52_group_ablation_cal_20260304_gabl52.json`
- 各组模型报告：`output/reports/lstm_dim52_ablation_drop_*_20260304_gabl52.json`
