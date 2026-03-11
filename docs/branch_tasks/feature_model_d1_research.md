# `feature/model-d1-research` 任务文档

## 分支角色

- 角色：`1d` 独立研究分支
- 当前定位：研究资产包，不是默认主线候选

## 当前状态

- [x] `1d` 实验协议已形成
- [x] `1d` 审计结论已形成
- [x] `1d` 训练/网格/稳定性脚本已形成
- [x] 目标测试已通过
- [ ] 尚未对齐 2026-03-11 之后的 `develop`

## 当前必须做

- [ ] 先对齐当前 `develop`
  - 须通过 [merge_audit_checklist](../overview/merge_audit_checklist_20260311.md) § 研究结论吸收 Checklist
  - 须填写研究结论分支自查表
- [ ] 人工解决已知冲突：
  - `docs/README.md`（入口文档，按 G2 集中制由 develop 统一处理）
  - `docs/research/README.md`（同上）
  - `scripts/run_xgboost_rolling_retrain_regime.py`
  - 6 个 src/ 文件（均因 trend_schema.py 引入，须决定是否采用 trend_schema）：
    - `labels/multi_horizon.py`
    - `dataset/sequence_parquet.py`
    - `models/transformer.py`
    - `training/mtl_finetune/__init__.py`
    - `recommendation/__init__.py`
    - `recommendation/engine.py`
  - 10 个 scripts/ 文件分歧（主要为 trend_schema 引用差异）
  - 3 个 tests/ 文件分歧
- [ ] 保留 `1d` 为独立研究线，不回写为默认主线
- [ ] 将 `1d` 股票池使用方式对齐到统一 registry，后续除 `csi300` 外优先走 `stock_pool` 模组
- [ ] 等待股票池模组至少完成 `S1-S2` 后，再扩展多股票池实验矩阵
- [ ] 把 `1d` 评估对齐到双窗口协议：
  - `fixed_20230101_20250701`
  - `latest_rolling`
- [ ] 按 G4 配置规范补齐实验配置元数据字段（参见 [config_and_artifact_naming](../overview/config_and_artifact_naming_20260311.md) § 7.2）：
  - 所有 `configs/experiments/1d_independent/*.toml` 须补齐 `model_track = "1d_independent"`、`config_profile`、`config_status`
  - `configs/experiments/xgb_rolling_d1_close_candidate.toml` 同上
  - 报告输出路径建议迁移到 `output/reports/1d_independent/`
- [ ] 重新定义 `1d` 任务族，逐步从单一 direction 扩展到区间/事件概率型任务
- [ ] 跑通既有目标测试集，确认对齐后未回归
- [ ] 整理最终吸收清单：
  - 协议文档
  - 审计结论
  - 比较脚本增强（`compare_ic_reports.py` 的 horizon-generic 改造建议反向采纳到 develop）
  - 可进入 `develop` 的研究工具
  - 须逐项通过研究结论 checklist（协议卡片化、Registry 对齐、门禁可复用、不回写主线）
  - 1d 独有资产可直接合入：`configs/*/1d_independent/`, `scripts/run_xgboost_1d_*`, `tests/test_xgb_1d_*`
- [ ] 合入时须确认 G3 公用层盘点结论（参见 [shared_layer_inventory](../overview/shared_layer_inventory_20260311.md)）：
  - 44 个 src/ 文件为公用层，合入不受影响
  - 6 个 src/ 文件因 trend_schema 分歧，须决定合并策略
  - `compare_ic_reports.py` 1d 版本更通用，建议以 1d 为基础合并

## 明确不做

- [ ] 不把 `1d` 结果描述成新的默认主模型线
- [ ] 不为追求“统一”而覆盖主线 `3d/5d/10d` 默认配置
- [ ] 不通过修改时间窗或口径制造比较优势

## 退出条件

- [ ] `1d` 研究协议和工具可被 `develop` 吸收
- [ ] 主线默认口径保持稳定
- [ ] 冲突文件已完成可解释的人工整合
