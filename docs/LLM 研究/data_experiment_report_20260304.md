# 数据实验阶段报告（截至 2026-03-04）

## 1. 范围与目标
- 范围：`quick8` 数据集（`2023-01-01` 至 `2026-01-20`），rolling 训练与 OOS 评估。
- OOS 统一月份：`2025-08` 至 `2026-01`（6 个月）。
- 目标：提升短线 `5d/10d` 横截面预测稳定性与可交易性。

## 2. 统一评估口径与门禁
- 主口径：`Daily-CS`（逐日横截面算 IC/RankIC，再时间聚合）。
- 核心指标：
  - `mean(IC_5_10)`
  - `mean(RankIC_5_10)`
  - 月胜率、最差月、连续负月
- 门禁：
  - `mean(IC_5_10) >= 0.05`
  - `mean(RankIC_5_10) >= 0.08`
  - 月胜率 `>= 60%`
  - 最差月 `>= -0.10`
  - 连续负月 `<= 2`

## 3. 实验脉络与结果

### 3.1 维度扩展（19 -> 26 -> 58）
来源：
- `ic_monthly_comparison_dim19_vs_dim26_auto_window24_l1_20260304.json`
- `ic_monthly_comparison_dim26_vs_dim58_auto_window24_l1_20260304.json`

`raw`（daily-CS）：
- `dim19`: IC_5_10=-0.0004, RankIC_5_10=-0.0452
- `dim26`: IC_5_10=0.0508, RankIC_5_10=-0.0237
- `dim58`: IC_5_10=0.0210, RankIC_5_10=0.0226

结论：
- 从 19 到 26，`IC_5_10` 提升明显。
- 从 26 到 58，`IC_5_10` 回落，`RankIC_5_10`略改善但仍偏弱。

### 3.2 复权验证（dim44 nonqfq vs qfq）
来源：
- `ic_monthly_comparison_dim44_nonqfq_vs_qfq_window24_l1_20260304.json`
- `ic_monthly_comparison_dim44_nonqfq_vs_qfq_window24_l1_cal_20260304.json`

`calibrated`（daily-CS）：
- `dim44_nonqfq`: IC_5_10=-0.0545, RankIC_5_10=-0.0973
- `dim44_qfq`: IC_5_10=0.0410, RankIC_5_10=0.0351

结论：
- QFQ 复权显著优于 nonqfq，是后续实验前提。

### 3.3 新增 12 维（历史高低价 + 资金流 MA/MOM）与消融
来源：
- `ic_monthly_comparison_dim58_vs_dim56_histflow_raw_20260304.json`
- `ic_monthly_comparison_ablation_new12_raw_20260304.json`
- `ic_monthly_comparison_ablation_new12_cal_20260304.json`

关键对比（daily-CS）：
- `dim58` -> `dim56(hist+flow)`：
  - `raw IC_5_10`: `0.0210 -> -0.1231`（显著恶化）
- `dim56` 消融：
  - 去历史高低价 4 维（`dim52_no_hist_hl`）后恢复最明显。
  - 去资金流 MA/MOM 8 维（`dim48_no_mf_momma`）对 `10d RankIC`改善更明显，但整体不如 `dim52`稳。

`dim52_no_hist_hl`（calibrated, daily-CS）：
- `IC_5_10=0.0575`
- `RankIC_5_10=0.0761`
- 月胜率=0.667，最差月=-0.0341，连续负月=1

结论：
- 历史高低价 4 维与当前短线目标存在频率/语义错配，是主要负贡献源。
- 当前最优主线来自 `dim52_no_hist_hl`。

### 3.4 交易量波动（日频）尝试
来源：
- `ic_monthly_comparison_dim52_vs_dim53_volvol_raw_20260304.json`
- `ic_monthly_comparison_dim52_vs_dim53_volvol_cal_20260304.json`

对比：`dim52` vs `dim53(+volume_volatility_10d)`
- `raw IC_5_10`: `-0.0089 -> -0.0792`
- `cal IC_5_10`: `0.0575 -> -0.0370`

结论：
- 当前定义的日频 `volume_volatility_10d` 为负贡献，未纳入基线。

### 3.5 板块 ETF 1阶+2阶（日频）尝试
新增因子：
- 1阶：`etf_ret_1d`, `etf_ret_1d_ma5`, `etf_ret_1d_ma10`
- 2阶：`etf_mom_5d`, `etf_slope_10d`

来源：
- `lstm_dim58_nohist_etf_auto_window24_l1_20260304.json`
- `ic_monthly_comparison_dim52_vs_dim58_nohist_etf_raw_20260304.json`
- `ic_monthly_comparison_dim52_vs_dim58_nohist_etf_cal_20260304.json`

对比：`dim52` vs `dim58_nohist_etf`
- `raw IC_5_10`: `-0.0089 -> -0.0372`
- `raw RankIC_5_10`: `0.0344 -> -0.0432`
- `cal IC_5_10`: `0.0575 -> 0.0358`
- `cal RankIC_5_10`: `0.0761 -> 0.0529`

结论：
- 当前日频 ETF 1阶+2阶设计尚未带来净增益。

## 4. 当前结论（客观）
- 目前最稳妥基线：`dim52_no_hist_hl`（不含历史高低价 4 维，不含日频 volume_volatility，不含日频ETF因子）。
- `dim52_no_hist_hl` 已接近门禁，仅差 `RankIC_5_10` 小幅不足（`0.0761` vs 门槛 `0.08`）。
- 当前阶段不建议将日频 `volume_volatility_10d` 和日频 ETF 因子直接并入默认基线。

## 5. 建议下一步（按优先级）
1. 固定 `dim52_no_hist_hl` 为后续调参与损失函数实验基线。
2. 在 `dim52` 上做 `RankIC` 定向优化（rank-aware / ic-rank-aware 小网格），目标补齐 `0.08` 门槛缺口。
3. 板块预期因子转向更高频表达（ETF 5min 聚合到日频的尾盘动量/日内波动）再复测。

## 6. 关键产物清单
- 核心最佳模型报告：
  - `output/reports/lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json`
- 关键对比报告：
  - `output/reports/ic_monthly_comparison_ablation_new12_cal_20260304.json`
  - `output/reports/ic_monthly_comparison_dim52_vs_dim53_volvol_cal_20260304.json`
  - `output/reports/ic_monthly_comparison_dim52_vs_dim58_nohist_etf_cal_20260304.json`
- 数据集：
  - `data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts`
  - `data/datasets/lstm_quick8_58d_nohist_etf_20230101_20260120_ts`
