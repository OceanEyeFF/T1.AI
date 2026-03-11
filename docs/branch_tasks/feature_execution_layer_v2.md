# `feature/execution-layer-v2` 任务文档

## 分支角色

- 角色：执行层设计资产分支
- 当前定位：方案与设计沉淀，不是已完成的功能分支

## 当前状态

- [x] 执行层分支计划已形成
- [x] Phase 0-3 实施方案已形成
- [x] `PortfolioManager` 算法伪代码已形成
- [x] 单一评分输入设计决策已形成
- [ ] 尚未进入真实代码实现闭环

## 当前必须做

- [ ] 盘点执行层文档，区分（须依据 [doc_lifecycle_rules](../overview/doc_lifecycle_rules_20260311.md) 中的状态定义）：
  - 稳定设计基线（`active`）
  - working memory（`stale` 或保留在分支）
  - 未来实现时需要重写的内容
- [ ] 将稳定设计文档择优吸收到 `develop`
  - 须通过 [merge_audit_checklist](../overview/merge_audit_checklist_20260311.md) § 文档/方案吸收 Checklist
  - 须填写文档/方案吸收自查表
  - 须明确区分：稳定设计基线 vs working memory vs 待重写
- [ ] 不把 `working memory` 作为长期基线文档合并
- [ ] 明确真实实现的下一阶段任务：
  - `PortfolioManager` 接线
  - 回测诊断与日志输出
  - 固定信号回放验收
- [ ] 为后续实现预先定义最小测试和验收产物
- [ ] 执行层设计文档中引用的配置/产物格式须与 G4 规范兼容（参见 [config_and_artifact_naming](../overview/config_and_artifact_naming_20260311.md)）：
  - 后续实现时，配置文件须遵守 § 2 命名规范
  - 实验产物须遵守 § 3 目录结构
  - 元数据字段须遵守 § 4 ID 体系
- [ ] 若正式开始实现，从 `develop` 新开实现分支，不继续无限堆叠在本分支
- [ ] 注意：本分支与 1d 共享同一代码基底，面临与 1d 完全相同的 6 个 src/ 文件冲突
  - 建议先合 1d 再合本分支，减少重复冲突解决
  - 详见 [shared_layer_inventory](../overview/shared_layer_inventory_20260311.md)

## 明确不做

- [ ] 不把“文档已完成”当成“执行层功能已完成”
- [ ] 不在未定义验收产物前直接进入大规模代码改造
- [ ] 不让本分支继续争夺入口文档的默认解释权

## 退出条件

- [ ] 稳定设计文档已进入 `develop`
- [ ] working memory 留在分支或另行归档
- [ ] 下一条执行层实现分支具备明确输入、测试与验收标准
