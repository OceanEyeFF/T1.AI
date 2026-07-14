---
title: "Repo Snapshot / Status"
artifact_type: "repo-snapshot-status"
generated_from: "servo-set-harness-goal-skill/assets/repo/snapshot-status.md"
updated: "2026-07-14T10:50:00+08:00"
owner: "OceanEyeFF"
---

# Repo Snapshot / Status

> 这是 `.servo/repo/snapshot-status.md` 的运行状态，用来记录当前 repo 的慢变量观测面。

## Metadata

- repo: T1.AI
- baseline_branch: develop
- updated: 2026-07-14T10:50:00+08:00
- status: idle (MS-R2-001 completed and accepted; no active milestone; MS-R3-001 / MS-R4-001 planned)

## Mainline Status

- baseline_branch: develop
- last_verified_checkpoint: 1f7eab1ccc9a065c6eff330b4b2c588e5fbb24cc
- checkpoint_ref: HEAD
- checkpoint_type: git_commit
- working_tree_state:
  - clean: yes
  - tracked_branch: develop...origin/develop (in sync)
  - last_commit_subject: chore: clean up stale recommendation outputs, add .logs/ to gitignore
  - layout: inputs/ + workspace/ + outputs/ three-zone model present at repo root (MS-R2-001 delivered)
  - top_level_dirs_observed: deployment, docs, inputs, outputs, scripts, src, tests, workspace (+ root docs/config files)
- worktree_state:
  - active_worktree_count: 1
  - active_worktree_path: /home/oceaneye/github/T1.AI
  - policy: single-worktree / develop as programmer review branch

## Architecture And Module Map

- package: `ashare-lab`
- python_requires: `>=3.10`
- source_root: `src/ashare_lab`
- major_modules:
  - `data`: akshare, tushare, index, and ODP source adapters.
  - `dataset`: tabular and sequence dataset builders.
  - `features`: momentum, price slope, technical, and volume features.
  - `labels`: excess return and multi-horizon labels.
  - `models`: ModelABC + registry; LSTM / XGBoost / Transformer paths (MS-R1-001).
  - `training`: trainer and MTL finetune paths.
  - `evaluation`: metrics, sanity checks, trade-like panels.
  - `recommendation`: engine, validator, history, trend aggregation.
  - `backtest`: book and engine.
  - `pipeline`: orchestrator and monitoring.
  - `stock_pools`: strategy ABC + low_manipulation strategy (MS-R0-001).
- zone_layout (MS-R2-001):
  - `inputs/`: data, configs, pools
  - `workspace/`: checkpoints, runs, registry
  - `outputs/`: predictions, reports, signals
- scripts_root: `scripts`
- docs_roots:
  - `README.md`
  - `NEXT_STEPS.md`
  - `ROADMAP.md`
  - `docs/WORK_RULES.md`
  - `docs/architecture`
  - `docs/reference`
  - `docs/guides`
  - `docs/research`
  - `docs/archive`

## Active Branches And Purpose

- local:
  - `develop`: current checkout; programmer review / servo baseline branch; HEAD `1f7eab1`; synced with `origin/develop`.
- remote_refs_observed:
  - `origin/develop`
- consolidation_state:
  - MS-R2 milestone branch work is recorded in history; current observed checkout is `develop` only.
  - No active milestone development branch required while `active_milestone: none`.

## Governance Status

- current_route_documents:
  - `README.md`: project purpose and current development lines.
  - `NEXT_STEPS.md`: current execution priority and staged work.
  - `ROADMAP.md`: long-term route.
  - `docs/WORK_RULES.md`: global work rules after MS-R2 docs rebuild.
- installed_servo:
  - control artifacts under `.servo/` are versionable project state.
  - skill backends historically under `.agents/skills` / `.claude/skills` (may be gitignored depending on later policy commits).
- approval_state:
  - persistent Servo work habit variables are configured.
  - Completed/accepted milestones include MS-ENV-000, MS-S0-001, MS-S1-001, MS-S2-001, MS-R0-001, MS-R1-001, MS-R2-001.
  - No model is promoted; `alpha_score` remains candidate research signal.
  - Pipeline planned: MS-R3-001 (deep cleanup) then MS-R4-001 (TuShare data lake).
- three_track_status:
  - `3d/5d/10d`: main alpha candidate line; credibility gates still block promotion.
  - `1d`: modeling remains blocked until live provider permission and fixed-pool fixed-window minute replay are proven.
  - decision_model: I/O draft exists; implementation remains future-scoped.

## Known Issues And Risks

- Control plane was stale after MS-R2 acceptance until 2026-07-14 refresh (this snapshot).
- MS-R2 left 2 pytest failures tied to old dataset paths; deferred to MS-R3-001 / MS-R4-001.
- Mainline `3d/5d/10d` prediction credibility remains insufficient for decision-ready `alpha_score`.
- `1d` ultra-fast prediction cannot be judged from day-K-only data.
- External data source behavior depends on provider availability, credentials, caching, and replay discipline.
- Generated caches, model checkpoints, logs, and reports must remain artifacts, not source truth.
- Commit / push / destructive cleanup / dependency changes / final milestone acceptance remain programmer-gated.

## Milestone Pipeline Snapshot

- active_count: 0
- planned_count: 2
- completed_count: 7
- active_milestone: none
- planned:
  - MS-R3-001: 旧文件深度清理 (depends on MS-R2-001; intake pending)
  - MS-R4-001: TuShare 数据湖构建 (depends on MS-R3-001; intake draft exists)
- latest_completed: MS-R2-001 (repo three-zone restructure; accepted 2026-06-23)

## Notes

- Snapshot records observed facts, not approval for future work.
- Next safe route is RepoScope.Decide (`repo-whats-next`) or pre-milestone intake for `MS-R3-001` when requested; no commit/push without programmer approval.
- Control-plane refresh report: `.servo/repo/refresh-report-control-plane-2026-07-14.md`
