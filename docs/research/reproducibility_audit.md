# 联调复现性审计（数据 → 数据集 → 模型 → 评估，2026-09-02）

审计目标：回答"从落盘数据到评估结论的整条链路是否可以良好复现"。

## 链路全景

```
数据湖 (inputs/data/cache, gitignored)
  → 数据集构建 (build_sequence_dataset --config-file profile)
  → 模型训练 (run_lstm/xgboost_rolling_retrain_* --dataset-dir ... --seed 42)
  → OOS parquet + 报告 JSON
  → 评估链 (audit_ic_reports → compare_ic_reports → compare_trade_like_panels → run_sanity_checks → audit_lag_horizon_analysis)
```

## ✅ 已验证可复现

| 环节 | 验证方式 | 结果 |
|---|---|---|
| 数据集构建 | 两次重建（23:43 vs 15:13）metadata 对比 | split/label_statistics/feature_config/dataset_id **完全一致** |
| seed 控制 | 代码审计 | LSTM `_set_seed(seed+i)`（random/np/torch/cuda 全设）；XGB `random_state=month_seed+h`；构建无随机源 |
| 同 seed 重跑 | sanity x2（seed 42, h10）去时间戳比对 | **逐字段一致**（shuffle IC 0.00617 两次相同）|
| 评估链 | audit/compare/panel 纯确定性读取报告 | 确定性（无随机源）|
| 环境前提 | `ensure_required_conda_env("py311-private")` + `.env` token | 脚本侧强制校验 |

## ⚠️ 缺口（已修复/待处理）

| # | 缺口 | 状态 |
|---|---|---|
| G1 | LSTM 无 cudnn deterministic——CUDA 下重训 OOS 有微小非确定性 | ✅ 已修复（`torch.backends.cudnn.deterministic=True` + benchmark=False，代价轻微速度损失）|
| G2 | 无端到端一键入口——命令链靠文档手工拼接 | 待办：`scripts/repro_full_chain.sh`（dry-run 语义可验证）或暂以 §6b 命令链为准 |
| G3 | nohup 重定向 stdout 缓冲掩盖进度 | 已记录：用 `python -u`（4.3v2 期间发现）|
| G4 | 产物对比需忽略时间戳（generated_at/created_at） | 规范：复现比对一律 strip 时间戳字段 |
| G5 | 数据湖本身是运行时产物（gitignored）——新机器需重新落盘 | 步骤化：1.3/1.4 拉取命令链已文档化（NEXT_STEPS），暂无自动化重拉脚本 |

## 结论

**数据 → 数据集 → 模型 → 评估的中段（数据集构建、训练、评估）确定性已达标**；
首段（数据湖落盘）与末段（一键执行）的自动化程度是主要改进空间。当前用
NEXT_STEPS §1.3/1.4 拉取命令 + §6b 评估命令链可人工完整复现全流程，但
"复制粘贴命令链"仍是手工步骤——建议 G2 落地 `repro_full_chain.sh` 后视为
"良好复现"闭环。
