# IC 统一评估比较

- 指标口径: calibrated
- 月度口径: calibrated
- daily-CS 使用: 7/7 份报告
- 公共 OOS 月份数: 6

| 报告 | 口径来源 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 | 门禁 |
|---|---|---:|---:|---:|---:|---:|---|
| lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json | daily_cs | 0.0575 | 0.0761 | 66.7% | -0.0341 | 1 | FAIL |
| lstm_dim52_ablation_drop_price_tech_core_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0352 | -0.0581 | 50.0% | -0.4433 | 2 | FAIL |
| lstm_dim52_ablation_drop_turnover_volume_micro_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0512 | -0.0514 | 16.7% | -0.0990 | 5 | FAIL |
| lstm_dim52_ablation_drop_valuation_size_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0550 | -0.0281 | 33.3% | -0.3697 | 2 | FAIL |
| lstm_dim52_ablation_drop_moneyflow_structure_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0429 | -0.0444 | 50.0% | -0.2465 | 2 | FAIL |
| lstm_dim52_ablation_drop_moneyflow_momentum_auto_window24_l1_20260304_gabl52.json | daily_cs | 0.0078 | 0.0127 | 50.0% | -0.0806 | 2 | FAIL |
| lstm_dim52_ablation_drop_market_state_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0328 | -0.0099 | 33.3% | -0.1179 | 4 | FAIL |
