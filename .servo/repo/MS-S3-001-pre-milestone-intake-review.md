---
title: "Pre-Milestone Intake Review — MS-S3-001"
artifact_type: "pre-milestone-intake-review"
proposed_milestone_id: "MS-S3-001"
created: "2026-06-22T14:00:00+08:00"
owner: "OceanEyeFF"
status: "pending-programmer-review"
---

# MS-S3-001 Pre-Milestone Intake Review

> 低控盘股票池预测稳定性验证

## 1. 一句话目的

**验证一个假说**：被操纵概率低的股票，XGBoost 的预测更稳定。

## 2. 背景

MS-S2-001 产出了 4 个可对比的股票池：

| 池子 | 股票数 | 性质 |
|---|---|---|
| custom_quick8_v1 | 8 | 历史基线 |
| custom_liquid_large_proxy_v1 | 5 | 纯大盘锚点 |
| custom_low_control_proxy_candidate_v1 | 3 | 低换手候选（research-only） |
| custom_low_manipulation_v1 | 14 | 综合低控盘评分 |

四个池子代表了从"不控任何东西"到"用多维度筛过低控盘"的梯度。如果假说成立，越靠右的池子预测越稳定。

## 3. 要做什么（极简版）

```
同一套 XGBoost + 同特征 + 同训练方式
在 4 个池子上各跑一遍
比较：
  - 谁的 IC 更稳（ICIR 更高）
  - 谁的 IC 在不同月份别差太多（条件 IC 方差更小）
  - 谁的信号别天天变（排名自相关更高）
```

**不做**：换模型、调参数、优化特征、回测策略收益。

## 4. 技术决策

| 项目 | 决策 | 理由 |
|---|---|---|
| 模型 | XGBoost only | 不考虑 LSTM |
| 预测目标 | pred_3d / pred_5d / pred_10d | 沿用 MS-S1 三头定义 |
| 数据窗口 | 2023-01 ~ 2026-03 | 约 3 年日线，与 MS-S2 缓存对齐 |
| Label 定义 | **改为 t+1 open → t+h+1 open** | 对齐实盘 T+1 执行（三个 SubAgent 的共识） |
| 训练方式 | 扩展窗口 rolling retrain | 避免单次 OOS 切分的偶然性 |
| 特征 | 沿用现有 XGBoost pipeline 的特征集 | 本轮不涉及特征工程 |

## 5. 验收标准

核心判决：**至少一个低控盘池（low_manipulation 或 low_control_candidate）在以下两个指标上显著优于 quick8 基线：**

| 指标 | 含义 | 判定方式 |
|---|---|---|
| ICIR | IC 的稳定性（均值/标准差） | low_manipulation 的 ICIR > quick8 的 ICIR |
| IC 衰减半衰期 | 预测能力能持续多久 | low_manipulation 的半衰期 > quick8 的半衰期 |

如果两个指标都不显著，假说不成立——诚实接受，不强行解释。

## 6. Out of Scope

- 不做策略回测、不算 Net Sharpe
- 不调模型参数
- 不优化特征
- 不晋级信号
- 不碰 LSTM

## 7. 前置依赖

- MS-S2-001 ✅ 已完成（产出股票池）
- MS-S1-001 ✅ 已完成（XGBoost pipeline 可用）

## 8. 风险

| 风险 | 缓解 |
|---|---|
| 池子太小（3/5/8/14 只），统计结论不稳定 | 用 bootstrap 置信区间代替裸均值 |
| Label 改为 open→open 后 IC 可能大幅下降 | 接受——这暴露的是 MS-S1 时期的系统性高估 |
| 假说被证伪 | 同样是有价值的结论，不比"证实"差 |

---

## 决策请求

1. **是否立项 MS-S3-001？**
2. **验收标准够不够？** 要不要加第三个指标（如排名自相关）？
3. **Label 改用 open→open，同意吗？** 这意味着要重新生成 label，但这是三个 SubAgent 的共识方向。
