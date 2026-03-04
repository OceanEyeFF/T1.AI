# IC 统一评估比较

- 指标口径: raw
- 月度口径: raw
- daily-CS 使用: 11/11 份报告
- 公共 OOS 月份数: 6

| 报告 | 口径来源 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 | 门禁 |
|---|---|---:|---:|---:|---:|---:|---|
| lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json | daily_cs | -0.0089 | 0.0344 | 50.0% | -0.4008 | 1 | FAIL |
| lstm_dim52_ablation_drop_moneyflow_momentum_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0293 | 0.0261 | 50.0% | -0.1248 | 3 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0208 | -0.0116 | 50.0% | -0.2868 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_ma10_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0470 | -0.0237 | 50.0% | -0.2819 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_mom5_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0284 | -0.0129 | 50.0% | -0.2993 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_net_amount_ratio_mom10_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0496 | -0.0021 | 50.0% | -0.2797 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_large_amount_ratio_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0158 | -0.0191 | 66.7% | -0.2890 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_large_amount_ratio_mom5_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0207 | -0.0014 | 66.7% | -0.2849 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_retail_amount_ratio_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0229 | -0.0105 | 66.7% | -0.2913 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_buy_pressure_amount_ma5_auto_window24_l1_20260304_mfm_single.json | daily_cs | -0.0388 | -0.0218 | 50.0% | -0.2990 | 1 | FAIL |
| lstm_dim52_ablation_mfm_single_drop_mf_activity_ratio_20d_auto_window24_l1_20260304_mfm_single.json | daily_cs | 0.0179 | 0.0312 | 66.7% | -0.1564 | 1 | FAIL |
