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
- updated: 2026-07-14T17:24:00+08:00
- status: active (MS-T1-001 test suite rewrite; MS-R3-001 completed/accepted; MS-R4-001 planned behind T1)

## Mainline Status

- baseline_branch: develop
- last_verified_checkpoint: 296318baeb27d4271986e51852ba4ade0abe0f02
- checkpoint_ref: HEAD
- checkpoint_type: git_commit
- working_tree_state:
  - clean: pending (close+init writeback may be uncommitted)
  - tracked_branch: develop / milestone/MS-T1-001-test-suite-rewrite
  - last_commit_subject: merge: 合入 origin/develop 并行清理与 MS-R3-001
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
  - Completed/accepted milestones include MS-ENV-000, MS-S0-001, MS-S1-001, MS-S2-001, MS-R0-001, MS-R1-001, MS-R2-001, MS-R3-001.
  - No model is promoted; `alpha_score` remains candidate research signal.
  - Pipeline: MS-T1-001 active (test suite rewrite); MS-R4-001 planned behind T1.
- three_track_status:
  - `3d/5d/10d`: main alpha candidate line; credibility gates still block promotion.
  - `1d`: modeling remains blocked until live provider permission and fixed-pool fixed-window minute replay are proven.
  - decision_model: I/O draft exists; implementation remains future-scoped.

## Known Issues And Risks

- MS-R2 path failures were fixed in MS-R3-001 (pytest 397/397).
- Mainline `3d/5d/10d` prediction credibility remains insufficient for decision-ready `alpha_score`.
- `1d` ultra-fast prediction cannot be judged from day-K-only data.
- External data source behavior depends on provider availability, credentials, caching, and replay discipline.
- Generated caches, model checkpoints, logs, and reports must remain artifacts, not source truth.
- Commit / push / destructive cleanup / dependency changes / final milestone acceptance remain programmer-gated.
- T-heavy test rewrite (MS-T1-001) carries short-term false-green risk; mitigated by phased migration + approval-gated deletes.

## Milestone Pipeline Snapshot

- active_count: 1
- planned_count: 1
- completed_count: 8
- active_milestone: MS-T1-001
- planned:
  - MS-R4-001: TuShare 数据湖构建 (depends on MS-T1-001; intake draft exists)
- latest_completed: MS-R3-001 (deep cleanup; accepted 2026-07-14; merge develop@296318b)

## Notes

- Snapshot records observed facts, not approval for future work.
- Next safe route: Init WT-T1-A1 (readonly inventory) on programmer request; no commit/push without programmer approval.
- Control-plane refresh report: `.servo/repo/refresh-report-control-plane-2026-07-14.md`