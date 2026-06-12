---
title: "Repo Goal / Charter"
artifact_type: "goal-charter"
generated_from: "servo-set-harness-goal-skill/assets/goal-charter.md"
updated: "2026-06-11"
owner: "OceanEyeFF"
---

# Repo Goal / Charter

> 这是 `.servo/goal-charter.md` 的运行状态，用来记录当前 repo 的长期目标和方向。

## Metadata

- repo: T1.AI
- owner: OceanEyeFF
- updated: 2026-06-11
- status: active-existing-code-adoption

## Project Vision

- Build a reproducible, auditable, and iteratively improvable A-share low-frequency research and execution framework.
- Keep the system pipeline-first: data ingestion, feature construction, signal modeling, portfolio decision, execution diagnostics, and reporting remain separable and explainable.
- Prioritize a correct research/execution contract over adding model complexity.

## Core Product Goals

- Maintain three explicit development lines: `3d/5d/10d` short-term prediction, `1d` ultra-fast prediction, and the decision model.
- Make the default main alpha line `3d/5d/10d`, with `pred_3d/pred_5d/pred_10d` aggregated into `alpha_score` for ranking/recommendation.
- Keep `1d` as an independent ultra-fast prediction line until intraday/minute data feasibility is proven and the line earns a separate go/no-go decision.
- Convert model scores into auditable trading decisions under strict A-share constraints through a dedicated decision model.
- Preserve realistic A-share constraints: long-only, T+1, limit-up/limit-down blocks, failed fills, transaction costs, minimum fees, and low-turnover discipline.
- Make every default experiment comparable through stable data windows, metrics, reports, and execution-layer assumptions.

## Technical Direction

- Python package managed by `pyproject.toml`, source under `src/ashare_lab`, scripts under `scripts`, tests under `tests`.
- Pipeline-first architecture: data sources, dataset builders, features, labels, models, recommendation, backtest, monitoring, and reporting stay as explicit modules.
- Default validation path uses pytest/ruff-style project tooling and focused regression scripts rather than ad hoc notebook-only evidence.
- Generated data, caches, model checkpoints, logs, recommendations, and reports are treated as artifacts rather than source truth.
- Servo controls work planning and evidence flow; it must not replace explicit programmer approval for business goals, destructive operations, git publishing, or production actions.

## Engineering Node Map

> 本 Goal 涉及的工程节点类型规划，供 `init-worktrack-skill` 在拆分 worktrack 时参考。
> 不是 worktrack 拆分本身，而是定义"这个 Goal 下会产生哪些类型的工程节点"及其约束。

### Node Type Registry

可复用的节点类型定义（全局参考）：

| type | merge_required | baseline_form | gate_criteria | if_interrupted_strategy | 说明 |
|------|---------------|---------------|---------------|-------------------------|------|
| `feature` | yes | commit-on-feature-branch-or-confirmed-current-branch | implementation + validation + policy | checkpoint-or-recover | 新功能开发 |
| `refactor` | yes | commit-on-refactor-branch-or-confirmed-current-branch | validation + policy | checkpoint-or-rollback | 重构，不改变外部行为 |
| `research` | no | report-or-experiment-artifact | review-only + reproducibility note | preserve-report-and-stop | 调研/探针，产出可能不可合并 |
| `bugfix` | yes | commit-on-bugfix-branch-or-confirmed-current-branch | implementation + regression validation + policy | checkpoint-or-rollback | 缺陷修复 |
| `docs` | yes | commit-on-docs-branch-or-confirmed-current-branch | review + consistency policy | checkpoint-or-recover | 文档更新 |
| `config` | yes | commit-on-config-branch-or-confirmed-current-branch | validation + rollback path + policy | checkpoint-or-rollback | 配置/部署变更 |
| `test` | yes | commit-on-test-branch-or-confirmed-current-branch | validation + coverage relevance + policy | checkpoint-or-recover | 专项测试 |

### This Goal's Node Types

- type: feature
  - expected_count: ongoing
  - merge_required: yes
  - baseline_form: commit-on-feature-branch-or-confirmed-current-branch
  - gate_criteria: implementation + focused tests + execution/reporting evidence + policy review
  - if_interrupted_strategy: checkpoint-or-recover
- type: refactor
  - expected_count: as-needed
  - merge_required: yes
  - baseline_form: commit-on-refactor-branch-or-confirmed-current-branch
  - gate_criteria: behavior-preserving tests + import/API compatibility + policy review
  - if_interrupted_strategy: checkpoint-or-rollback
- type: research
  - expected_count: ongoing
  - merge_required: no
  - baseline_form: report-or-experiment-artifact
  - gate_criteria: reproducible config + stable window comparison + go/no-go statement
  - if_interrupted_strategy: preserve-report-and-stop
- type: docs
  - expected_count: ongoing
  - merge_required: yes
  - baseline_form: commit-on-docs-branch-or-confirmed-current-branch
  - gate_criteria: docs match code reality + no stale task tree + route consistency
  - if_interrupted_strategy: checkpoint-or-recover
- type: test
  - expected_count: as-needed
  - merge_required: yes
  - baseline_form: commit-on-test-branch-or-confirmed-current-branch
  - gate_criteria: targeted regression passes + no unrelated fixture churn
  - if_interrupted_strategy: checkpoint-or-recover
- type: config
  - expected_count: as-needed
  - merge_required: yes
  - baseline_form: commit-on-config-branch-or-confirmed-current-branch
  - gate_criteria: config contract validation + artifact naming consistency + rollback path
  - if_interrupted_strategy: checkpoint-or-rollback

### Node Dependency Graph

- docs -> feature (execution and model work must use current route boundaries)
- config -> research (experiments require stable config and artifact naming)
- feature -> test (execution-layer changes require focused regression coverage)
- research -> docs (go/no-go and line-boundary decisions must update navigation docs)
- 1d intraday data feasibility -> 1d model expansion (minute-level data must be validated before complex `1d` modeling)
- 3d/5d/10d alpha_score -> decision model (decision model can progress with mainline alpha before `1d` is mature)

### Default Baseline Policy

- if_worktrack_interrupted: preserve current diff, record handback state, and do not infer completion without evidence.
- if_no_merge: preserve report/evidence and keep the worktrack open or explicitly deferred; do not silently promote results to repo baseline.

## Success Criteria

- Default backtest/recommendation chain explains why a trade happens, does not happen, or fails to execute.
- Execution diagnostics distinguish turnover threshold, cost coverage, risk buy disablement, limit block, T+1 block, and failed fill causes.
- Mainline `3d/5d/10d` experiments are comparable under the same OOS window, metrics, and execution assumptions.
- `1d` results remain isolated from mainline default scoring unless a separate approved decision changes the charter.
- `1d` ultra-fast modeling does not proceed beyond baseline/negative-control status until minute-level data feasibility is documented.
- Decision model input/output contracts are stable enough to replay decisions from fixed prediction, position, cost, and risk inputs.
- Reports, configs, and generated artifacts can be traced to data/model/config versions and reproduce the key decision path.

## System Invariants

- Long-only A-share constraints are not optional.
- No lookahead leakage, survivorship shortcut, or cost-free execution assumption may enter default reports.
- Mainline default scoring remains `3d/5d/10d -> alpha_score`.
- `1d` is an independent research line, not a silent mainline input.
- Day-K-only `1d` results are not sufficient to prove or disprove ultra-fast `1d` viability.
- Signals are not final product; target positions, orders, risk checks, and decision reasons are the execution product.
- Servo does not auto-approve git publishing, destructive operations, production API calls, or persistent autonomy changes.

## Notes

- Current planning entry is `docs/overview/three_track_development_plan_20260609.md`.
- Current highest priority is active milestone `MS-S0-001`: establish trustworthy `3d/5d/10d` evaluation, false-signal controls, and optimization discipline before treating `alpha_score` as decision-ready.
- Environment baseline: `MS-ENV-000` completed on 2026-06-11; `py311-private` is the canonical CPU development/testing environment. Local GTX 1080 Ti GPU compatibility remains a non-blocking residual risk.
- This charter reflects user-provided project documents and current conversation context as of 2026-06-10.
