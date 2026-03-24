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
- 主模型最小回归入口已固定：`scripts/run_develop_min_regression.sh`
- 2026-03-23 已按统一入口复跑通过：
- 2026-03-23 已完成主线 `experiment metadata / effective_config / reports/{model_track}` 最小代码闭环
- 2026-03-23 已完成股票池模组 `S1 minimal`：registry + `sequence/market_state` dataset builder 最小接线

```bash
./scripts/run_develop_min_regression.sh
```

## 当前必须做

- [x] 固定统一测试入口，消除裸跑 `pytest` 的导入不确定性
  - 已完成：`scripts/run_develop_min_regression.sh`
- [x] 固定 `develop` 主职责为架构基线、集成审核、分支吸收门禁，不把它继续用作细节研究主场
- [x] 固定模型输出 / 数据集 / 股票池 / 双窗口评估的统一 contract，并形成审核基线
  - 规范层已完成：[config_and_artifact_naming](../overview/config_and_artifact_naming_20260311.md)（ID 体系 + 配置状态）
  - 基线已冻结：[stock_pool_registry_baseline](../modules/stock_pool_registry_baseline_20260311.md)、[dual_window_evaluation_baseline](../overview/dual_window_evaluation_baseline_20260311.md)
  - 已完成：运行脚本输出 `_effective_config.json`、报告目录按 `model_track` 分层、dataset builder 写入 `dataset_id / stock_pool_*`
- [x] 将股票池模组开发提上近期排期，作为后续主模型与 `1d` 研究的 dependency
- [x] 推进股票池模组 `S1`：registry 与基础接口，并先完成架构审核
  - 已完成：`configs/stock_pools/` + `src/ashare_lab/stock_pool/` 最小实现；`sequence/market_state` dataset builder 已可消费 `stock_pool_id`
- [ ] 推进股票池模组 `S2`：首批池子家族支持（单板块 / 高相关板块 / 反板块），并先完成接线审核
- [ ] 审核 `LSTM` 真实主线数据上的 baseline vs candidate 对照是否闭环
- [ ] 审核 `XGBoost` 主模型 baseline 是否能与 `LSTM` 做同口径比较
- [x] 固定双窗口评估协议：`2023-01-01 ~ 2025-07-01` 基准窗口 + `latest_rolling` 近期窗口
  - 已完成：[dual_window_evaluation_baseline_20260311.md](../overview/dual_window_evaluation_baseline_20260311.md)
- [x] 固定主模型默认评估口径为 `trade_like panel`
  - 已完成：`feature/model-3d-5d-10d-head` 合并时落地，测试 `test_trade_like_panel.py` 已通过
- [ ] 从执行层分支吸收稳定设计文档，但不把方案误判为已实现
- [ ] 固化分支启动模板、入口文档规则、配置状态模板
  - 规则已定义：[doc_lifecycle_rules § 6](../overview/doc_lifecycle_rules_20260311.md)（分支任务文档模板）+ [config_and_artifact_naming § 5](../overview/config_and_artifact_naming_20260311.md)（配置状态三分类）
  - 待推进：模板文件实体化到 `docs/templates/` 或等价位置
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

## 治理期总结（2026-03-11）

**治理期起止：** 2026-03-11（同日完成 4 项核心专题）

**背景：**
- `feature/model-3d-5d-10d-head` 合并后，主模型代码基线初步稳定
- 3 条工作分支各自沉淀了大量文档/配置/命名约定，但互不兼容
- 后续无论推进哪条线，都需要先有统一治理基础

**产出资产清单：**
- ✅ **G1：Merge/Audit Checklist 基线**
  - 文档：[merge_audit_checklist_20260311.md](../overview/merge_audit_checklist_20260311.md)
  - 三类分支合入标准：代码分支、文档/方案分支、研究结论分支
  - 已通过独立验证（feature/g1-validation），发现 5 个问题并全部修正
- ✅ **G2：docs/ 目录治理与归档规则**
  - 文档：[doc_lifecycle_rules_20260311.md](../overview/doc_lifecycle_rules_20260311.md) + [doc_governance.md](../overview/doc_governance.md) 更新
  - 职责分离：命名/颗粒度（governance）vs 生命周期/权限（lifecycle）
  - 入口文档严格集中制、5 类归档触发条件、6 层维护责任矩阵
  - 归档实操：IC 改造 + G1 验证过程文件已移入 archive/
  - INVENTORY.md 重写（60+ 文件全覆盖，带状态标记）
- ✅ **G3：1d / 3d|5d|10d 公用层盘点**
  - 文档：[shared_layer_inventory_20260311.md](../overview/shared_layer_inventory_20260311.md)
  - 关键发现：44/55 个 src/ 文件完全一致（80%），已是事实公用层
  - 分歧根因单一：trend_schema.py（3d-5d-10d-head 引入的 horizon 常量中心化）
  - 1d 的 `compare_ic_reports.py` 更通用（horizon-generic），建议反向采纳
  - 抽象优先级：P0 确认现有公用层 → P1 采纳工具改进 → P2 trend_schema 参数化
- ✅ **G4：配置与实验产物命名/版本规范**
  - 文档：[config_and_artifact_naming_20260311.md](../overview/config_and_artifact_naming_20260311.md)
  - 完整 ID 体系：model_track / config_profile / dataset_id / stock_pool_id / evaluation_window_id / experiment_id
  - 配置状态三分类：baseline / candidate / frozen + 流转规则
  - 与已有基线完全对齐：stock_pool_registry ✅ + dual_window_evaluation ✅
  - 当前配置盘点：develop 3 个待补元数据、1d 分支 5 个待补元数据

**治理成果：**
- 🔒 **分支合入有标准可依** - 不再靠人工判断和临时协调
- 📚 **文档治理规则完整** - 新增/归档/权限都有明确流程
- 🔗 **公用层边界清晰** - 知道哪些该统一、哪些该平行共存
- 🏷️ **配置/ID 体系统一** - 实验可复现、可比较、可追溯

**跨分支影响统计：**
- `feature/model-d1-research`：4 个治理专题全部引用，合入路径清晰
- `feature/execution-layer-v2`：4 个治理专题全部引用，吸收标准明确
- `feature/model-3d-5d-10d-head`：已同步收口完成，当前作为历史参考分支保留

**遗留落地尾巴（属功能实现，非治理规则）：**
- 1d 分支 5 个配置补元数据（1d 对齐 develop 时）
- `reports/` 目录按 `model_track` 分层（2026-03-23 已完成 develop 主线）
- `runtime_metadata.py` / `_effective_config.json` 公用 helper（2026-03-23 已完成 develop 主线）

**详细总清单：** [develop_governance_backlog_20260311.md](develop_governance_backlog_20260311.md)

**✅ 治理期正式结束，develop 回归架构基线维护模式。**

---

## 退出条件

- [x] `develop` 的角色边界已经固定，后续研究实现默认回到功能/研究分支推进
- [ ] 主模型 `LSTM/XGB` 都具备可复现、可审核的 baseline 对照
- [ ] 股票池模组至少完成 `S1-S2`，并通过架构/接线审核后进入实验链路排期
- [x] 股票池基线和双窗口评估协议已经固定
- [x] 测试入口已标准化
- [ ] 执行层稳定设计文档已回收
- [ ] 后续新分支的启动/文档/状态模板已经固定
- [x] 跨分支 merge/audit checklist 已固定并进入使用
