# IC 提升研究清单（后续迭代基线）

## 1. 目标定义
- 主目标：提升 `5d/10d` 横截面预测的稳定性与可交易性。
- 次目标：在稳定性达标前提下提升全时段 IC。
- 约束：评估必须同时覆盖“全时段均值 + 月度分布”，禁止只看单一平均值。

## 2. 当前基线（以已跑结果为准，2026-03-07 更新）
- 推荐 LSTM 基线：`dim53(no_hist_hl) + weekly rolling retrain + seq_len=20 + 三头训练`
- 推荐树模型对照：`XGBoost(dim53, 同口径滚动切分)`
- 参考报告：
  - `output/reports/lstm_dim53_no_hist_hl_auto_window24_seq20_icaware_a0176_lr5e5_coswrt_pat20_seed042_20260305_latest.json`
  - `output/reports/lstm_dim53_no_hist_hl_auto_window24_seq20_icaware_a0176_lr5e5_coswrt_pat20_seed042_20260305_latest_oos.parquet`
  - `output/reports/abtest_xgb_baseline_dim53_20260306.json`
  - `output/reports/abtest_xgb_baseline_dim53_20260306_oos.parquet`
  - 非最佳实验归档：`output/reports/reports_nonbest_experiments_20260307.tar.gz`
- 关键事实：
  - 在当前样本下，纯 A 股基线中 XGBoost 的 `calibrated` 指标优于 LSTM。
  - 加入商品因子（国际 ODP 或国内期货）后，两类模型的 `calibrated` 指标都未超过基线。
  - 归一化历史高低价（`hist_high/low_*`）版本在 LSTM/XGBoost 下均未观察到增益。
  - 数据构建层可配置 `horizons`，但当前训练脚本仍是 `3d/5d/10d` 固定三头，`d1` 尚未进入实现态基线。

## 3. 统一评估口径（必须执行）
- 主口径：`Daily-CS IC` 与 `Daily-CS RankIC`（按日横截面计算，再做时间聚合）。
- 稳定性口径：月度 IC 分布（均值/中位数/最差月/胜率/连续负月）。
- 对比要求：不同配置必须统一 OOS 月份后再比较（避免样本口径偏差）。

## 4. 门禁草案（先作为研发准入）
- 全时段：
  - `mean(IC_5_10) >= 0.05`
  - `mean(RankIC_5_10) >= 0.08`
- 月度：
  - 月胜率（IC_5_10 > 0）`>= 60%`
  - 最差月 `>= -0.10`
  - 连续负月 `<= 2`
- 风险：
  - ICIR（或等价稳定性指标）需达标后才进入线上候选。

## 5. 实验优先级（按顺序）
1. 评估框架固化：
   - 固化 daily-cs/monthly 报表脚本与统一口径比较流程。
2. 三头权重优化：
   - 保留 3d 头，但降低其权重（例如 `0.2/0.4/0.4`）。
3. 滚动窗口对比：
   - `12/18/24` 个月窗口，目标是降低坏月与连续负月。
4. 损失函数升级：
   - IC-aware 或 rank-aware 混合损失，优先验证 `5d/10d` 指标提升是否稳定。
5. 市场状态特征扩展：
   - 指数状态、行业轮动、情绪 proxy 分阶段增量验证。
6. 校准策略重构（后置）：
   - 只在高置信条件触发，不允许默认翻向。

## 6. 防偏差检查（每轮实验都过）
- 检查时序泄漏（特征与标签对齐）。
- 检查 rolling 重训是否包含未来样本。
- 检查训练样本是否按“标签成熟日”入池，而不是只按 `sample_date < retrain_date`。
- 当前 `3d/5d/10d` 标签默认按最长 horizon `10d` 作为成熟门槛。
- 检查调参是否在测试集上过拟合。
- 检查不同 seq_len 的 OOS 月份是否同口径。
- 检查停牌/缺失处理是否引入未来筛样偏差。

## 7. 执行策略
- 路线 A（稳健优先）作为默认路线：
  - rolling + 多任务权重 + 市场状态增强 + 严格门禁。
- 路线 B（收益优先）作为探索路线：
  - 更激进损失函数/结构升级，仅在 A 达稳后推进。
