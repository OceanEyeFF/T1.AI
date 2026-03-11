# `develop` 任务文档

## 分支角色

- 角色：当前集成 / 架构 / 审核基线
- 工作原则：只接收已经形成代码/文档闭环的成果，不承接未定稿方案的直接落地
- 工作重心：
  - 统一跨分支的架构 contract、入口规范、评估口径与验收门禁
  - 审核功能/研究分支是否达到可吸收状态，而不是在 `develop` 上继续铺开细节研究
  - 对必须进入主线的 dependency，只推进接口、registry、版本规则和接线基线，不在 `develop` 上做大规模探索式实现

## 当前状态

- 2026-03-11 已快进同步 `feature/model-3d-5d-10d-head`
- 主模型最小回归已通过：

```bash
PYTHONPATH=src:. pytest -q \
  tests/test_trade_like_panel.py \
  tests/test_trend_aggregation.py \
  tests/test_trend_schema.py \
  tests/test_lstm_dynamic_heads.py \
  tests/test_multilevel_tuning.py
```

## 当前必须做

- [ ] 固定统一测试入口，消除裸跑 `pytest` 的导入不确定性
- [ ] 固定 `develop` 主职责为架构基线、集成审核、分支吸收门禁，不把它继续用作细节研究主场
- [ ] 固定模型输出 / 数据集 / 股票池 / 双窗口评估的统一 contract，并形成审核基线
- [ ] 将股票池模组开发提上近期排期，作为后续主模型与 `1d` 研究的 dependency
- [ ] 推进股票池模组 `S1`：registry 与基础接口，并先完成架构审核
- [ ] 推进股票池模组 `S2`：首批池子家族支持（单板块 / 高相关板块 / 反板块），并先完成接线审核
- [ ] 审核 `LSTM` 真实主线数据上的 baseline vs candidate 对照是否闭环
- [ ] 审核 `XGBoost` 主模型 baseline 是否能与 `LSTM` 做同口径比较
- [ ] 固定双窗口评估协议：`2023-01-01 ~ 2025-07-01` 基准窗口 + `latest_rolling` 近期窗口
- [ ] 固定主模型默认评估口径为 `trade_like panel`
- [ ] 从执行层分支吸收稳定设计文档，但不把方案误判为已实现
- [ ] 固化分支启动模板、入口文档规则、配置状态模板
- [x] 固定跨分支 merge/audit checklist：数据 contract、输出 contract、测试入口、文档入口、配置状态、验收产物
  - 已完成：[merge_audit_checklist_20260311.md](../overview/merge_audit_checklist_20260311.md)
  - 包含三类 checklist：代码分支、文档/方案分支、研究结论分支
  - 双重验证流程：功能分支自查 + develop 复核

## 明确不做

- [ ] 不把 `1d` 独立研究结果回写成默认主线
- [ ] 不在主模型 baseline 未稳定时，把执行层真实逻辑硬接到默认链路
- [ ] 不让入口文档承载具体实验顺序和大量细节
- [ ] 不在 `develop` 上直接承接长周期探索式调参、选股池试错和研究分支原型开发
- [ ] 不把股票池模组在 `develop` 上扩成策略研究平台，先只做 dependency 级能力

## 退出条件

- [ ] `develop` 的角色边界已经固定，后续研究实现默认回到功能/研究分支推进
- [ ] 主模型 `LSTM/XGB` 都具备可复现、可审核的 baseline 对照
- [ ] 股票池模组至少完成 `S1-S2`，并通过架构/接线审核后进入实验链路排期
- [ ] 股票池基线和双窗口评估协议已经固定
- [ ] 测试入口已标准化
- [ ] 执行层稳定设计文档已回收
- [ ] 后续新分支的启动/文档/状态模板已经固定
- [ ] 跨分支 merge/audit checklist 已固定并进入使用
