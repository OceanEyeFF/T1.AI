---
title: "Repo Snapshot / Status"
artifact_type: "repo-snapshot-status"
generated_from: "servo-set-harness-goal-skill/assets/repo/snapshot-status.md"
updated: "2026-06-12T10:01:18+08:00"
owner: "OceanEyeFF"
---

# Repo Snapshot / Status

> 这是 `.servo/repo/snapshot-status.md` 的运行状态，用来记录当前 repo 的慢变量观测面。

## Metadata

- repo: T1.AI
- baseline_branch: develop
- updated: 2026-06-12T10:01:18+08:00
- status: next-three-head-credibility-milestone-planned

## Mainline Status

- baseline_branch: develop
- last_verified_checkpoint: b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- checkpoint_ref: HEAD
- checkpoint_type: git_commit
- working_tree_state:
  - uncommitted_servo_install: yes
  - uncommitted_gitignore_update: yes
  - environment_contract_changes: yes
  - business_code_changes: yes, focused A2 strict protocol gate in `scripts/compare_ic_reports.py` and tests.
  - research_docs_changes: yes, A2 evaluation gate protocol and Daily-CS workflow updates.
  - servo_control_changes: yes, `WT-A2-001`, `WT-A3-001`, `WT-B0-001`, and `WT-C0-001` initialized, verified, and closed.
- worktree_state:
  - active_worktree_count: 1
  - active_worktree_path: /home/oceaneye/github/T1.AI
  - removed_worktrees:
    - /home/oceaneye/github/T1.AI-exec
    - /home/oceaneye/github/T1.AI-model-d1

## Architecture And Module Map

- package: `ashare-lab`
- python_requires: `>=3.10`
- source_root: `src/ashare_lab`
- major_modules:
  - `data`: akshare, tushare, index, and ODP source adapters.
  - `dataset`: tabular and sequence dataset builders.
  - `features`: momentum, price slope, technical, and volume features.
  - `labels`: excess return and multi-horizon labels.
  - `models`: transformer and related model components.
  - `training`: trainer and MTL finetune paths.
  - `evaluation`: metrics, sanity checks, trade-like panels.
  - `recommendation`: engine, validator, history, trend aggregation.
  - `backtest`: book and engine.
  - `pipeline`: orchestrator and monitoring.
  - `stock_pool`: registry and stock pool typing.
- scripts_root: `scripts`
- config_roots:
  - `configs`
  - `configs/datasets`
  - `configs/experiments`
  - `configs/stock_pools`
- docs_roots:
  - `README.md`
  - `NEXT_STEPS.md`
  - `ROADMAP.md`
  - `docs/README.md`
  - `docs/modules`
  - `docs/overview`
  - `docs/research`
  - `docs/interfaces`

## Active Branches And Purpose

- local:
  - `milestone/MS-S0-001-prediction-credibility`: current checked-out branch; completed prediction credibility milestone changes are still uncommitted pending programmer approval.
  - `milestone/MS-ENV-000-conda-env-validation`: previous milestone branch retained locally.
  - `develop`: intended single-worktree programmer review branch.
  - `feature/model-3d-5d-10d-head`: local branch retained; not currently checked out.
- remote_refs_observed:
  - `origin/develop`
  - `origin/feature/execution-layer-v2`
  - `origin/feature/model-d1-research`
  - `origin/feature/model-3d-5d-10d-head`
  - `origin/codex/read-research_checklist.md-for-new-branch`
- consolidation_state:
  - previous local worktrees for execution-layer and d1 research were removed.
  - previous local branches `feature/execution-layer-v2` and `feature/model-d1-research` were deleted locally after confirming no unpushed commits.

## Governance Status

- current_route_documents:
  - `README.md`: project purpose and current development lines.
  - `NEXT_STEPS.md`: current execution priority and staged work.
  - `ROADMAP.md`: long-term route.
  - `docs/overview/three_track_development_plan_20260609.md`: current three-track development plan.
  - `docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md`: mainline vs 1d boundary.
  - `docs/modules/system_io_and_architecture_spec.md`: system I/O and pipeline-first architecture.
- installed_servo:
  - installer_command: `npx servo-installer@next`
  - installer_version_observed: `0.6.1-rc.2`
  - deployed_backends:
    - `.agents/skills`
    - `.claude/skills`
- local_tooling:
  - `.serena/` is ignored and local-only.
  - `.logs/` is ignored and local-only.
  - `.servo/` is not ignored and is intended to carry versionable Servo control artifacts unless the programmer later changes that policy.
- approval_state:
  - persistent Servo work habit variables are configured.
  - `MS-ENV-000` is completed and accepted by the programmer.
  - `MS-S0-001` is completed and accepted by the programmer with residual risk and no model promotion.
  - `WT-A2-001` is closed with pass gate for protocol/audit-only scope.
  - `WT-A3-001` is closed with pass gate for planning/dry-run optimization queue scope.
  - `WT-B0-001` is closed with pass gate for read-only intraday data feasibility scope.
  - `WT-C0-001` is closed with pass gate for decision-model I/O draft scope.
  - `MS-S1-001` is planned with five Worktracks focused on `pred_3d` / `pred_5d` / `pred_10d` credibility and report contract, excluding `alpha_score` optimization or promotion.
  - no model is promoted; `alpha_score` remains candidate research signal until A3 and later gates.
- three_track_status:
  - `3d/5d/10d`: main alpha candidate line; A2 froze credibility protocol and A3 froze a planning/dry-run optimization queue under that protocol.
  - `1d`: B0 feasibility report completed; modeling remains blocked until live provider permission and fixed-pool fixed-window minute replay are proven.
  - decision_model: C0 I/O draft is available; implementation remains future-scoped and cannot use candidate signals as production trading inputs.

## Known Issues And Risks

- Mainline `3d/5d/10d` prediction credibility is the current main gap: evaluation methodology and optimization discipline must be strengthened before treating `alpha_score` as decision-ready.
- Planned next milestone `MS-S1-001` intentionally deprioritizes `alpha_score` and focuses on the three prediction heads directly.
- Mainline `3d/5d/10d` and independent `1d` research must remain separated to avoid metric/config/report contamination.
- `1d` ultra-fast prediction cannot be judged from day-K-only data; intraday/minute data source feasibility is a required gate.
- External data source behavior depends on provider availability, credentials, caching, and replay discipline.
- Generated caches, model checkpoints, logs, and reports must remain artifacts, not source truth.
- Servo framework is installed and control artifacts are versionable project state.
- Conda environment validation completed: `py311-private` is canonical and passes core imports, project imports, env guard, ruff availability, and minimal pytest on CPU.
- GPU training on the local GTX 1080 Ti / `sm_61` is not validated with current PyTorch wheel and is non-blocking for the CPU-first next milestone.
- `MS-S0-001` has completed all four planned Worktracks and was accepted by the programmer on 2026-06-12T01:28:03+08:00.
- A2 audit found quick8 historical reports are OOS-comparable but fail raw/calibrated strict credibility gates and sanity checks; this is evidence against promotion, not a missing-artifact failure.
- Independent random-label CLI and industry / market-cap neutralization gate remain explicit follow-up anti-cheat gaps.
- Actual model training remains deferred to explicit later execution slices; A3 only planned and dry-ran command manifests.
- B0 found no current repo-ready minute replay implementation; TuShare `stk_mins` is the primary candidate, AkShare is smoke-only, and live provider validation remains approval-gated.
- C0 produced a decision-model I/O draft with signal maturity guards; no trading logic was implemented and no signal was promoted.

## Notes

- Snapshot records observed facts, not approval for future work.
- Next safe route is programmer-requested activation of planned `MS-S1-001`; no Worktrack execution should start before activation and per-Worktrack intake.
