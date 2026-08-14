# Mainline 3d/5d/10d Evaluation Gate Protocol

本协议固定主线 `3d/5d/10d -> alpha_score` 进入优化和决策模型评估前的可信评估门禁。它只定义评估、审计和防伪要求，不证明任何当前模型已经可用，也不要求在本协议内重新训练模型。

## 1. Scope

- 适用对象：主线 `3d/5d/10d` 预测报告、OOS 逐样本预测 parquet、`alpha_score` 交易近似面板。
- 默认主指标：Daily-CS `IC_5_10` 与 Daily-CS `RankIC_5_10`。
- 稳定性指标：月胜率、最差月、连续负月、ICIR。
- 辅助面板：`alpha_score` Top-N 等权超额收益 proxy，用于研究判断，不等同真实交易回测。
- 不适用对象：`1d` 独立研究线、真实下单、生产调度、外部数据刷新、模型重训。

## 2. Required Report Contract

每份进入 strict 比较的报告必须包含：

- `oos_predictions_path`
- `evaluation_protocol`
  - `signal_time_mode`
  - `execution_time_mode`
  - `label_mode`
  - `return_mode`

对应 OOS parquet 必须包含：

- raw: `date`, `symbol`, `label_5d`, `label_10d`, `pred_5d`, `pred_10d`
- calibrated: raw 列，加 `pred_5d_cal`, `pred_10d_cal`

协议字段缺失或协议不一致时，报告不能进入 strict 比较；这属于评估产物阻断，不是模型质量结论。

## 3. Required Commands

先做 OOS 覆盖审计：

```bash
python "scripts/audit_ic_reports.py" \
  --reports "outputs/reports/<report_a>.json" "outputs/reports/<report_b>.json" \
  --tag <tag>
```

再做 raw strict 比较：

```bash
python "scripts/compare_ic_reports.py" \
  --reports "outputs/reports/<report_a>.json" "outputs/reports/<report_b>.json" \
  --metric-source raw \
  --monthly-source raw \
  --daily-cs-mode required \
  --check-protocol \
  --tag <tag>-raw
```

如存在 calibrated 输出，再做 calibrated strict 比较：

```bash
python "scripts/compare_ic_reports.py" \
  --reports "outputs/reports/<report_a>.json" "outputs/reports/<report_b>.json" \
  --metric-source calibrated \
  --monthly-source calibrated \
  --daily-cs-mode required \
  --check-protocol \
  --tag <tag>-calibrated
```

对候选 OOS parquet 分 horizon 跑防伪检查：

```bash
python "scripts/run_sanity_checks.py" \
  --oos-parquet "outputs/reports/<candidate>_oos.parquet" \
  --horizon 5 \
  --output "outputs/reports/sanity_<candidate>_h5.json"

python "scripts/run_sanity_checks.py" \
  --oos-parquet "outputs/reports/<candidate>_oos.parquet" \
  --horizon 10 \
  --output "outputs/reports/sanity_<candidate>_h10.json"
```

## 4. Gate Thresholds

主线候选至少需要同时满足：

- `mean(IC_5_10) >= 0.05`
- `mean(RankIC_5_10) >= 0.08`
- `月胜率 >= 60%`
- `最差月 >= -0.10`
- `连续负月 <= 2`
- 若启用 ICIR 门禁，`ICIR_5_10` 必须达到本轮声明阈值。

防伪检查需要满足：

- shuffle 后 `abs(mean_ic)` 接近 0。
- time reverse 后 `abs(mean_ic)` 接近 0。
- lag-1 后 IC 有足够下降。
- 标签成熟日与交易时点必须由 `evaluation_protocol` 和训练/报告链路显式表达。

当前缺口（2026-08-14 更新）：

- random-label 实验已固化于 `scripts/run_sanity_checks.py`（`--random-label-trials` / `--random-label-threshold` / `--random-label-horizons`）。
- 中性化门禁已固化于同一脚本（`--neutralization-output` / `--neutralization-horizons`），但行业/市值分组数据源尚未落盘，运行需先提供分组映射；未提供时相关结论只能标记为未覆盖，不得视作通过。

## 5. Interpretation Rules

- `go`: OOS 覆盖完整、协议一致、raw/cal strict 比较至少一个候选通过、关键 sanity checks 通过，且 trade-like panel 没有相反风险信号。
- `no-go`: OOS 覆盖完整且协议一致，但 strict 比较或 sanity checks 明确失败；不得把该结果推广为默认可交易 `alpha_score`。
- `continue-research`: OOS/report 缺失、协议字段缺失、公共窗口不足、random-label 或中性化缺口未覆盖，或 evidence 只来自过小样例。

`alpha_score` 在 A2/A3 通过前只能是 candidate research signal。任何高 IC、较高月胜率或 calibrated 结果都必须先通过本协议，才允许作为默认决策模型评估输入。

## 6. A3 Handoff

A3 只能在本协议下组织优化候选：

- 使用同一 OOS 窗口和同一报告字段比较 LSTM、XGBoost 与轻量融合。
- 先修复产物协议和可比较性，再解释模型优劣。
- 把 random-label 和行业 / 市值中性化列为后续防伪增强项；未覆盖时保留 `continue-research`。

## 7. Baseline Ledger（基线留档，2026-08-14 3.1 复跑）

数据集：`sequence_baseline_20230101_20260813`（research_liquidity_quality_v1 60 只，11 特征 × seq_len 20，test 2026-02-09..2026-08-13）。产物目录：`outputs/reports/`（本地 artifact，不入库）。

| 指标 | 门禁 | LSTM | XGB |
|---|---:|---:|---:|
| mean(IC_5_10) | ≥ 0.05 | 0.0536 | 0.0568 |
| mean(RankIC_5_10) | ≥ 0.08 | 0.0664 | 0.0769 |
| 月胜率 | ≥ 60% | 71.4% | 71.4% |
| 最差月 | ≥ -0.10 | -0.0628 | -0.0129 |
| 连续负月 | ≤ 2 | 1 | 1 |
| shuffle | abs≈0 | pass | pass |
| time_reverse | abs≈0 | fail (h5/h10) | h5 pass / h10 fail |
| lag-1 drop | ≥ 0.01 | 0.0004 / 0.0033 | 0.0058 / 0.0021 |

**结论：continue-research**。RankIC 未达门禁（XGB 距 0.08 仅 0.0031）；time_reverse 部分未过。lag-1 阈值对 daily 滚动预测（相邻日 target 重叠 90%+）判别力弱——后续协议修订应改为 lag≥5 或重叠感知阈值。
