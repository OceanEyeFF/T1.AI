---
title: "MS-ENV-000 Conda 环境可用性验证"
artifact_type: "milestone"
milestone_id: "MS-ENV-000"
status: "completed"
milestone_kind: "goal-driven"
priority: 0
created: "2026-06-11T11:34:36+08:00"
created_by: "programmer-confirmed-harness"
updated: "2026-06-11T16:40:59+08:00"
updated_by: "harness-skill"
---

# MS-ENV-000 Conda 环境可用性验证

> 这是 `MS-S0-001` 之前的前置 Milestone，用来确认压缩过的 conda 环境是否仍能支撑本项目。它最初只授权验证与报告；后续经程序员一次性批准，已完成 `py311-private` 依赖修复和环境合同迁移。它不授权进一步安装、升级、删除环境、提交或推送。

## Control Signal

- milestone_id: MS-ENV-000
- title: Conda 环境可用性验证
- status: completed
- milestone_kind: goal-driven
- priority: 0
- purpose: 验证当前机器上的 conda 环境是否仍能支持 T1.AI 的基本开发、导入、测试和后续研究工作；最终确认 `py311-private` 是当前 canonical conda 环境。
- completion_threshold_pct: 100
- depends_on_milestones: none
- activation_decision: active because the programmer requested a prerequisite milestone before starting prediction credibility work.
- scope_boundary_note: 做环境可用性检查、命令证据记录、一次性批准的 `py311-private` 依赖修复/环境合同迁移，以及 go/no-go 判断；不执行环境重建、进一步包安装/依赖升级、业务代码实现、提交或推送。
- next_required_route: RepoScope.Refresh -> activate `MS-S0-001` -> pre-milestone intake for `WT-A2-001`.

## Purpose

在推进 `MS-S0-001` 前，先确认 conda 环境压缩后是否仍保留项目运行所需的核心能力。若环境不可用，本 Milestone 需要明确阻断原因和最小修复建议；若环境可用，后续才能安全进入主线预测可信评估。本轮最终以 `py311-private` 作为可用环境合同。

## Scope

### In Scope

- 检查 conda 是否可用，并识别候选环境；最终确认 `py311-private` 可用。
- 验证项目要求的 Python 版本满足 `pyproject.toml` 中 `>=3.10`。
- 验证核心依赖的 import smoke：`pandas`、`numpy`、`pyarrow`、`torch`、`sklearn`、`xgboost`、`akshare`、`tushare`、`yaml`、`pytest`。
- 验证项目包导入入口：`ashare_lab` 以及若干轻量核心模块。
- 验证最小测试入口是否可运行，优先使用不依赖外部数据源和大模型训练的快速测试子集。
- 记录 CUDA 可见性，但 CUDA 不作为本 Milestone 的硬通过条件，除非后续 Worktrack 明确要求 GPU。
- 输出环境可用性报告和 go / blocked / repair-needed 判断。

### Out Of Scope

- `conda env create`、`conda env remove`、进一步 `pip install`、依赖升级、环境修复或 CUDA 重装。
- 访问生产数据源、调用外部付费 API、消耗 TuShare 分钟权限。
- 修改业务代码、训练模型、运行长耗时实验。
- Git commit、git push、release、tag 或版本动作。

## Worktrack List

| order | worktrack_id | title | node_type | status | role |
|---:|---|---|---|---|---|
| 1 | WT-ENV-001 | Conda 环境盘点与最小 smoke 验证 | test/config | completed | 验证环境是否能支撑项目基本开发 |

## Completion Signals

- conda_runtime_identified: 能记录 `conda` 命令可用性、当前 shell Python、候选环境路径和最终 `py311-private` 环境状态。
- python_version_supported: 候选运行环境的 Python 满足项目 `>=3.10` 要求。
- core_dependency_imports_passed: 核心依赖 import smoke 通过，或逐项记录缺失/损坏原因。
- package_import_smoke_passed: `ashare_lab` 和轻量核心模块可导入。
- minimal_test_entry_verified: 至少一个快速、无外部数据依赖的测试入口可运行，或明确说明阻断原因。
- environment_report_written: 产出环境验证报告，包含命令、解释器路径、版本、失败项和下一步建议。
- downstream_gate_decision_recorded: 明确 `MS-S0-001` 是否可以继续，或必须先追加环境修复 worktrack。

## Acceptance Criteria

- 不依赖猜测判断环境是否可用；每个结论必须有命令输出或明确的失败证据。
- 允许记录 CUDA 不可用，但只要 CPU 路径能支撑当前短期开发和测试，CUDA 不阻断本 Milestone。
- 如果 canonical 环境不存在或核心依赖缺失，不得静默进入 `MS-S0-001`；本轮该风险已通过一次性批准的 `py311-private` 修复解除。
- 如果测试失败来自已知仓库测试问题而非环境问题，报告必须区分“环境不可用”和“代码/测试基线失败”。
- 不安装、不升级、不删除任何环境，除非后续得到明确程序员审批。

## Progress Counter

- total: 1
- completed: 1
- blocked: 0
- deferred: 0
- completion_pct: 100

## Milestone Review Gate

- milestone_review_gate_status: effective_pass
- milestone_review_count: 1
- latest_review_checkpoint: WT-ENV-001-intake-2026-06-11T12:14:55+08:00
- effective_review_pass: true
- review_invalidated_by: none
- milestone_review_gate_ready: true
- conservative_runtime_backfill: not_applicable_for_new_artifact
- next_required_review: none before `WT-ENV-001` validation execution.

## Aggregated Evidence

- [pyproject.toml#project]
- [README.md#快速开始]
- [docs/interfaces/setup.md]
- [.servo/control-state.md#User-Defined-Servo-Controls]
- [.servo/repo/snapshot-status.md#Known-Issues-And-Risks]
- [.servo/worktrack/intake-review.md#Milestone-Review-Gate-Handoff]
- [.servo/worktrack/contract.md#Verification-Requirements]
- [.servo/worktrack/environment-validation-report.md#Verdict]
- [.servo/worktrack/gate-evidence.md#Per-Surface-Verdicts]
- [.servo/milestone/MS-ENV-000-composite-acceptance.md#Summary]

## Release Version Consideration

- release_version_consideration: no release or version bump is implied by environment validation.

## Developer Decision Boundary

- programmer_confirmed_milestone_brief: true
- confirmation_source: conversation on 2026-06-11, request to add a prerequisite milestone for conda environment validation.
- final_acceptance_required: fulfilled
- final_acceptance_received: true
- final_acceptance_received_at: 2026-06-11T16:40:59+08:00
- worktrack_init_allowed_now: true
- worktrack_init_blocker: none
- package_install_or_env_repair_allowed_now: completed under one-shot programmer approval for `py311-private` repair and environment-contract migration
- source_code_mutation_allowed_now: false
- git_branch_commit_push_allowed_now: false

## Activation Rules

- activation_rule: prerequisite_before_MS-S0-001
- activation_context: `MS-S0-001` is planned until `MS-ENV-000` completes or is explicitly bypassed by programmer decision.
- branch_strategy: one development branch per confirmed milestone is the configured policy; `milestone/MS-ENV-000-conda-env-validation` was created from `develop` at `b1c1f82bb87ae2ce32223ad2edb69ca501296c5b`.

## Initialization Result

- init_action: created
- backlog_updated: true
- control_state_updated: true
- override_source: programmer
- milestone_brief_confirmed: true
- pre_milestone_intake_required: false for milestone artifact creation, true before Worktrack Init.
- pre_milestone_intake_status: N/A for artifact creation.
- complex_project_entry_gate: not_applicable for validation-only prerequisite milestone.
- milestone_reevaluation_required: true
- milestone_reevaluation_reason: new active prerequisite milestone with zero closed worktracks.
- can_proceed: true for RepoScope.Observe and intake review only.
- proceed_blockers:
  - final milestone acceptance remains programmer-owned.

## WT-ENV-001 Result

- worktrack_status: completed
- gate_verdict: pass
- result_kind: go-for-cpu-development
- decisive_result: `py311-private` imports core dependencies and project modules, passes env guard and ruff availability checks, and passes the minimal pytest subset.
- report_ref: .servo/worktrack/environment-validation-report.md
- gate_evidence_ref: .servo/worktrack/gate-evidence.md
- downstream_decision: `MS-S0-001` may proceed on the CPU lane.
- residual_risk: local GPU is visible but current PyTorch wheel does not support GTX 1080 Ti `sm_61`; CPU development/testing passes and the programmer accepted using CPU first.

## Final Acceptance

- accepted_by: OceanEyeFF
- accepted_at: 2026-06-11T16:40:59+08:00
- acceptance_verdict: accepted_with_residual_gpu_risk
- composite_acceptance_report: .servo/milestone/MS-ENV-000-composite-acceptance.md
- final_state: completed
