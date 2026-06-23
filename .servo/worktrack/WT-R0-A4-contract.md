---
title: "WT-R0-A4 维护文档补完"
artifact_type: "worktrack-contract"
milestone_id: "MS-R0-001"
worktrack_id: "WT-R0-A4"
status: "completed"
worktrack_kind: "documentation"
node_type: "docs"
created: "2026-06-23"
completed: "2026-06-23"
---

# WT-R0-A4 维护文档补完

## Task Goal

为 `stock_pools/` 模块编写维护指南文档，规定新增选股策略的规则和约定。

## Scope

### In Scope

- 编写 `docs/modules/stock_pool_maintenance_guide.md`
- 覆盖：架构概述、新增策略检查清单、Registry 注册规则、禁止事项、测试规范、数据依赖、FAQ

### Out Of Scope

- 不修改任何代码
- 不修改 registry/toml 格式
- 不改动测试

## Completion Criteria

- [x] 文档已落于 `docs/modules/stock_pool_maintenance_guide.md`
- [x] 内容覆盖 8 个章节（架构、新增检查清单、注册规则、禁止事项、测试规范、修改指南、数据依赖、FAQ）
- [x] 策略代码模板可直接使用
- [x] Registry TOML 必填字段表完整

## Artifacts Produced

- `docs/modules/stock_pool_maintenance_guide.md` (244 lines)

## Gate Evidence

详见 `WT-R0-A4-gate-evidence.md`。

## Closeout

- 文档已产出，无需测试
- 格式校验通过（markdownlint auto-fix applied）
- 内容经审查覆盖全部预期章节
