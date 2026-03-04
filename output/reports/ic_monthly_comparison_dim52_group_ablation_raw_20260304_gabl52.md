# IC 统一评估比较

- 指标口径: raw
- 月度口径: raw
- daily-CS 使用: 7/7 份报告
- 公共 OOS 月份数: 6

| 报告 | 口径来源 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 | 门禁 |
|---|---|---:|---:|---:|---:|---:|---|
| lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json | daily_cs | -0.0089 | 0.0344 | 50.0% | -0.4008 | 1 | FAIL |
| lstm_dim52_ablation_drop_price_tech_core_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0219 | -0.0568 | 66.7% | -0.4433 | 2 | FAIL |
| lstm_dim52_ablation_drop_turnover_volume_micro_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.1428 | -0.1076 | 16.7% | -0.3620 | 5 | FAIL |
| lstm_dim52_ablation_drop_valuation_size_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0442 | -0.0091 | 50.0% | -0.3697 | 3 | FAIL |
| lstm_dim52_ablation_drop_moneyflow_structure_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0203 | -0.0213 | 50.0% | -0.2465 | 2 | FAIL |
| lstm_dim52_ablation_drop_moneyflow_momentum_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.0293 | 0.0261 | 50.0% | -0.1248 | 3 | FAIL |
| lstm_dim52_ablation_drop_market_state_auto_window24_l1_20260304_gabl52.json | daily_cs | -0.1236 | -0.0714 | 16.7% | -0.3588 | 5 | FAIL |
