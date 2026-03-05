# 稳定性复验报告（2026-03-05）

## 1. 复验目标
对已选最优参数点做跨随机种子稳定性检查，确认是否具备可复现性：

- 配置：`dim52_no_hist_hl + seq20 + w(0.1/0.45/0.45) + ic_aware(alpha=0.176)`
- 种子：`42`（基线）、`7`、`99`

## 2. 固定实验配置
- 脚本：`scripts/run_lstm_rolling_retrain_dim19_regime.py`
- 数据集：`data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts`
- `feature_mode=auto`
- `train_window_months=24`
- `valid_window_months=2`
- `calibration_months=3`
- `sign_threshold=0.02`
- 评估口径：strict `daily-CS`（`compare_ic_reports.py --daily-cs-mode required`）

## 3. 新增产物
- 复验训练产物（seed99）：
  - `output/reports/lstm_dim52_no_hist_hl_auto_window24_seq20_w010_045_045_icaware_a0176_seed099_20260305.json`
  - `output/reports/lstm_dim52_no_hist_hl_auto_window24_seq20_w010_045_045_icaware_a0176_seed099_20260305_oos.parquet`
- OOS 覆盖率审计：
  - `output/reports/ic_report_oos_coverage_20260305_microgrid_seed_stability.json`
  - `output/reports/ic_report_oos_coverage_20260305_microgrid_seed_stability.md`
- 严格比较结果：
  - `output/reports/ic_monthly_comparison_20260305_microgrid_seed_stability_cal.json`
  - `output/reports/ic_monthly_comparison_20260305_microgrid_seed_stability_cal.md`
  - `output/reports/ic_monthly_comparison_20260305_microgrid_seed_stability_raw.json`
  - `output/reports/ic_monthly_comparison_20260305_microgrid_seed_stability_raw.md`

## 4. 核心结果（calibrated, strict daily-CS）

| seed | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 | 门禁 |
|---|---:|---:|---:|---:|---:|---|
| 42 | 0.1025 | 0.1023 | 66.7% | -0.0948 | 1 | PASS |
| 7 | 0.0401 | 0.0281 | 66.7% | -0.2451 | 1 | FAIL |
| 99 | -0.0641 | -0.0337 | 33.3% | -0.1724 | 2 | FAIL |

补充（raw, strict daily-CS）：`seed42/7/99` 全部未过门禁。

## 5. 结论
- 当前最优点对随机种子高度敏感，跨 seed 稳定性不足。
- `seed42` 可作为单次最佳记录保留，但不应视作已验证的稳健最优参数。

## 6. 下一步建议
1. 先做小规模稳健性优先微调：固定其余参数，仅在 `loss_alpha` 邻域（如 `0.176/0.180/0.184`）上做 `3-seed` 快速筛选，门禁改为“按 seed 均值 + 最差 seed 同时约束”。
2. 若仍不稳，降低校准翻转敏感度（提高 `sign_threshold` 或收紧翻转规则），避免个别 seed 在单月出现过度反转。
3. 若目标是可交付信号，可引入 seed 集成（多 seed 平均预测）作为工程兜底口径，再与单 seed 结果并行评估。
