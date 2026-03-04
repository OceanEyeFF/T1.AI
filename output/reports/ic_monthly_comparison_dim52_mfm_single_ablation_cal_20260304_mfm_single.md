# IC 统一评估比较

- 指标口径: calibrated
- 月度口径: calibrated
- daily-CS 使用: 11/11 份报告
- 公共 OOS 月份数: 6

| 报告 | 口径来源 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 | 门禁 |
|---|---|---:|---:|---:|---:|---:|---|
| lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json | daily_cs | 0.0575 | 0.0761 | 66.7% | -0.0341 | 1 | FAIL |
| lstm_dim52_ablation_drop_moneyflow_momentum_auto_window24_l1_20260304_gabl52.json | daily_cs | 0.0078 | 0.0127 | 50.0% | -0.0806 | 2 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0278 | -0.0184 | 50.0% | -0.2613 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_ma10_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0014 | -0.0451 | 50.0% | -0.2684 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_mom5_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0220 | -0.0283 | 50.0% | -0.2662 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_mom10_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0242 | -0.0546 | 33.3% | -0.2783 | 2 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_large_amount_ratio_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0331 | -0.0325 | 66.7% | -0.2657 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_large_amount_ratio_mom5_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0177 | -0.0248 | 50.0% | -0.2719 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_retail_amount_ratio_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0304 | -0.0235 | 66.7% | -0.2633 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_buy_pressure_amount_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0138 | -0.0298 | 50.0% | -0.2506 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_activity_ratio_20d_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0364 | -0.0087 | 66.7% | -0.2508 | 1 | FAIL |
