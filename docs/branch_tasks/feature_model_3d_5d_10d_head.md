# `feature/model-3d-5d-10d-head` 任务文档

## 分支角色

- 角色：`3d/5d/10d` 主模型收口分支
- 当前定位：历史开发分支，主要成果已同步进 `develop`

## 当前状态

- [x] 主线 schema 已统一
- [x] `pred_3d/pred_5d/pred_10d -> alpha_score` 聚合层已落地
- [x] `trade_like panel` 已落地
- [x] 目标测试已通过
- [x] 2026-03-11 已同步进 `develop`

## 当前必须做

- [ ] 不再把新的长期开发继续堆在本分支
- [ ] 如需继续推进主模型 baseline，一律转到 `develop`
- [ ] 将本分支保留为历史参考点，用于回溯：
  - schema 收口
  - 聚合层引入
  - trade-like panel 引入

## 明确不做

- [ ] 不再把本分支当作当前主工作分支
- [ ] 不在本分支继续追加与 `develop` 重复的功能演化

## 退出条件

- [ ] 本分支状态明确标记为”已同步/待归档”
- [ ] 后续主模型工作全部转到 `develop`

## G3 公用层盘点确认

已在 [shared_layer_inventory](../overview/shared_layer_inventory_20260311.md) 中确认本分支的贡献：

- 贡献 3 个主线专属文件：`trend_schema.py`、`trade_like_panel.py`、`trend_aggregation.py`
- 贡献 trend_schema 重构（影响 6 个共享文件的 import/常量引用）
- 其余 44 个 src/ 文件为未修改的公用层基底

## G4 配置合规说明

已同步到 develop 的配置文件中，以下需补齐元数据字段（参见 [config_and_artifact_naming](../overview/config_and_artifact_naming_20260311.md) § 7.1）：

- `experiments/lstm_rolling_fastpilot.toml` — 缺 `model_track`/`config_profile`/`config_status`
- `experiments/xgb_rolling_baseline.toml` — 同上
- `experiments/xgb_rolling_fastpilot.toml` — 同上

仅 `experiments/lstm_rolling_baseline.toml` 已合规。补齐工作在 develop 上执行即可。

## 归档说明

- 本分支已于 2026-03-11 同步进 `develop`
- 可参照 [merge_audit_checklist](../overview/merge_audit_checklist_20260311.md) § 代码分支合入 Checklist 回顾确认（无需重新执行）
- 合并时已通过的检查项可作为后续分支的参考标准
