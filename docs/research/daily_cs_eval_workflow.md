# Daily-CS 统一评估工作流（Priority-1 固化）

## 1. 目标
- 所有比较结果必须来自同一口径：`Daily-CS IC/RankIC`。
- 比较前必须先对报告做 OOS 产物覆盖率审计。
- 无 OOS parquet 或字段不全的报告，不允许进入 strict 比较。

## 2. 训练产物要求
滚动实验脚本必须输出 OOS 逐样本预测 parquet，并把路径写入报告 JSON：

- `scripts/run_lstm_rolling_retrain_dim19_h2.py --save-oos-parquet ...`
- `scripts/run_lstm_rolling_retrain_dim19_regime.py --save-oos-parquet ...`

报告至少应包含：
- `oos_predictions_path`
- parquet 列：`date,symbol,label_5d,label_10d,pred_5d,pred_10d`
- 若评估 calibrated：还需 `pred_5d_cal,pred_10d_cal`

## 3. 覆盖率审计
先盘点报告是否满足 strict daily-CS 输入条件：

```bash
python "scripts/audit_ic_reports.py" \
  --reports \
  "output/reports/lstm_dim19_h2_rolling18m_seq20_*.json" \
  "output/reports/lstm_dim19_rolling18m_horizoncal_consensus_seq20_*.json" \
  --tag 20260304_phase1
```

产物：
- `output/reports/ic_report_oos_coverage_<tag>.json`
- `output/reports/ic_report_oos_coverage_<tag>.md`

## 4. 严格比较（必须）
审计通过后执行 strict daily-CS 比较：

```bash
python "scripts/compare_ic_reports.py" \
  --reports \
  "output/reports/xxx.json" \
  "output/reports/yyy.json" \
  --metric-source raw \
  --monthly-source raw \
  --daily-cs-mode required \
  --tag 20260304_phase1
```

产物：
- `output/reports/ic_monthly_comparison_<tag>.json`
- `output/reports/ic_monthly_comparison_<tag>.md`

## 5. 失败处理
- 报错 `missing oos parquet path`：回到训练脚本补跑并带 `--save-oos-parquet`。
- 报错列缺失：检查 parquet 写出列是否完整，修复后重跑审计。
- 报错公共月份为空：统一 OOS 时间区间后再比较。

## 6. 门禁阈值
- `mean(IC_5_10) >= 0.05`
- `mean(RankIC_5_10) >= 0.08`
- `月胜率 >= 60%`
- `最差月 >= -0.10`
- `连续负月 <= 2`
