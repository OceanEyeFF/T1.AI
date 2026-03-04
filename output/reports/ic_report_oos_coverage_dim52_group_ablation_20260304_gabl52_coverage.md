# IC 报告 OOS 覆盖率审计

- 报告总数: 7
- 有 OOS parquet 路径: 7
- strict daily-CS(raw) 就绪: 7
- strict daily-CS(calibrated) 就绪: 7

| 报告 | OOS 路径 | raw列 | cal列 | 样本行数 | 月份数 | 问题 |
|---|---|---|---|---:|---:|---|
| lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json | YES | YES | YES | 864 | 6 | OK |
| lstm_dim52_ablation_drop_price_tech_core_auto_window24_l1_20260304_gabl52.json | YES | YES | YES | 864 | 6 | OK |
| lstm_dim52_ablation_drop_turnover_volume_micro_auto_window24_l1_20260304_gabl52.json | YES | YES | YES | 864 | 6 | OK |
| lstm_dim52_ablation_drop_valuation_size_auto_window24_l1_20260304_gabl52.json | YES | YES | YES | 864 | 6 | OK |
| lstm_dim52_ablation_drop_moneyflow_structure_auto_window24_l1_20260304_gabl52.json | YES | YES | YES | 864 | 6 | OK |
| lstm_dim52_ablation_drop_moneyflow_momentum_auto_window24_l1_20260304_gabl52.json | YES | YES | YES | 864 | 6 | OK |
| lstm_dim52_ablation_drop_market_state_auto_window24_l1_20260304_gabl52.json | YES | YES | YES | 864 | 6 | OK |
