# Repo Goal / Charter Answer Template

> 使用方式：在 Codex 对话中需要生成或重写 `goal-charter.md` 草稿时，使用本模板组织回答。它不是 `.servo/` 路径下的直接文件。

## Metadata

- repo:
- owner:
- updated:
- status:

## Project Vision

- 

## Core Product Goals

- 

## Technical Direction

- 

## Engineering Node Map

> 本 Goal 涉及的工程节点类型规划，供 `init-worktrack-skill` 在拆分 worktrack 时参考。
> 不是 worktrack 拆分本身，而是定义"这个 Goal 下会产生哪些类型的工程节点"及其约束。

### Node Type Registry

可复用的节点类型定义（全局参考）：

| type | merge_required | baseline_form | gate_criteria | if_interrupted_strategy | 说明 |
|------|---------------|---------------|---------------|-------------------------|------|
| `feature` | yes | commit-on-feature-branch | implementation + validation + policy | checkpoint-or-recover | 新功能开发 |
| `refactor` | yes | commit-on-refactor-branch | validation + policy | checkpoint-or-rollback | 重构，不改变外部行为 |
| `research` | no | annotated-tag-or-report | review-only | preserve-report-and-stop | 调研/探针，产出可能不可合并 |
| `bugfix` | yes | commit-on-bugfix-branch | implementation + validation + policy | checkpoint-or-rollback | 缺陷修复 |
| `docs` | yes | commit-on-docs-branch | review + policy | checkpoint-or-recover | 文档更新 |
| `config` | yes | commit-on-config-branch | validation + policy | checkpoint-or-rollback | 配置/部署变更 |
| `test` | yes | commit-on-test-branch | validation + policy | checkpoint-or-recover | 专项测试 |

### This Goal's Node Types

> 列出本 Goal 预期会涉及的节点类型：

- type:
  - expected_count:
  - merge_required:
  - baseline_form:
  - gate_criteria:
  - if_interrupted_strategy:

### Node Dependency Graph

> 如果有明确的节点间依赖关系：

- source_type → target_type (reason)

### Default Baseline Policy

- if_worktrack_interrupted:
- if_no_merge:

## Success Criteria

- 

## System Invariants

- 

## Notes

- 
