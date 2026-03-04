# 微调收敛报告（2026-03-05）

## 1. 目标
在保持 `mean(IC_5_10)` 与 `mean(RankIC_5_10)` 高位的前提下，修复门禁短板：
- 最差月从 `-0.1132` 拉回到 `>= -0.10`

## 2. 固定配置
- 数据集：`data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts`
- 模型：`run_lstm_rolling_retrain_dim19_regime.py`（`feature-mode=auto`）
- 核心参数：
  - `seq_len=20`
  - `train_window_months=24`
  - `valid_window_months=2`
  - `w3/w5/w10=0.1/0.45/0.45`
  - `loss_type=ic_aware`
  - `calibration_months=3`
  - `sign_threshold=0.02`

## 3. 微网格结果
最后一轮窄区间微调：`loss_alpha in {0.168, 0.170, 0.172, 0.176}`。

最佳结果为 `loss_alpha=0.176`：
- `mean(IC_5_10)=0.102493`
- `mean(RankIC_5_10)=0.102293`
- 月胜率 `=0.666667`
- 最差月 `=-0.094770`
- 连续负月 `=1`
- 门禁结果：`PASS`

## 4. 最终保留记录
- 最佳模型报告：
  - `output/reports/lstm_dim52_no_hist_hl_auto_window24_seq20_w010_045_045_icaware_a0176_20260305.json`
- 最佳模型 OOS 逐样本预测：
  - `output/reports/lstm_dim52_no_hist_hl_auto_window24_seq20_w010_045_045_icaware_a0176_20260305_oos.parquet`
- 本轮汇总对比：
  - `output/reports/ic_monthly_comparison_20260305_microgrid_last_round_cal.json`
  - `output/reports/ic_monthly_comparison_20260305_microgrid_last_round_cal.md`

## 5. 增量归档
除第 4 节保留记录外，其余本轮测试产物已归档到：
- `output/reports/reports_increment_20260305_microgrid.tar.gz`
