# 数据实验 Brief（2026-03-04）

## 结论
- 当前最优基线：`dim52_no_hist_hl`。
- 该基线在 `calibrated daily-CS` 下：
  - `mean(IC_5_10)=0.0575`
  - `mean(RankIC_5_10)=0.0761`
  - 月胜率 `66.7%`，最差月 `-0.0341`，连续负月 `1`
- 门禁状态：仅 `RankIC_5_10` 略低于 `0.08`（其余核心稳定性项已达标）。

## 关键实验判断
1. 历史高低价 4 维是负贡献主因，移除后显著改善。
2. 日频 `volume_volatility_10d` 为负贡献，不应并入默认基线。
3. 日频 ETF 1阶+2阶（ret/ma/mom/slope）在当前实现下未超过 `dim52`。
4. QFQ 复权显著优于 nonqfq，后续实验应统一 QFQ。

## 后续动作
1. 锁定 `dim52_no_hist_hl` 作为后续唯一调参基线。
2. 在该基线上做 `RankIC` 定向优化（rank-aware / ic-rank-aware 小网格）。
3. ETF 因子转向 5min 聚合表达后再复测。
