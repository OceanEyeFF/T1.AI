---
title: "Repo Analysis"
artifact_type: "repo-analysis"
generated_from: "servo-set-harness-goal-skill/assets/repo/analysis.md"
updated: "2026-06-11T16:40:59+08:00"
owner: "OceanEyeFF"
---

# Repo Analysis

> 这是 `.servo/repo/analysis.md` 的运行状态，用来记录 RepoScope 的阶段性分析与优先级判断。它是决策支撑 artifact，不是 goal truth，也不是 worktrack queue。

## Metadata

- repo: T1.AI
- baseline_branch: develop
- baseline_ref: b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- updated: 2026-06-11T16:40:59+08:00
- analysis_status: refreshed-after-MS-ENV-000-acceptance

## Facts

- The repo is a Python A-share low-frequency research and execution framework.
- The project documents now define three development lines:
  - `3d/5d/10d` short-term prediction
  - `1d` ultra-fast prediction with intraday/minute data as prerequisite
  - decision model
- The current worktree is `/home/oceaneye/github/T1.AI` on `milestone/MS-ENV-000-conda-env-validation` after accepted environment milestone closeout.
- Multi-worktree local development has been consolidated back to a single worktree.
- Servo framework was installed through `npx servo-installer@next`; observed installer version is `0.6.1-rc.2`.
- Installed Servo backends:
  - `.agents/skills`
  - `.claude/skills`
- Current uncommitted business-logic changes: none observed.
- Current uncommitted environment/control changes: Servo bootstrap/control artifacts and `py311-private` environment-contract updates.

- facts: TODO(facts)
## Inferences

- `MS-ENV-000` is completed and accepted; `py311-private` supports CPU development/testing for the repo.
- The active Servo-managed milestone is now `MS-S0-001`, focused on `3d/5d/10d` prediction credibility and optimization discipline.
- Decision-model work should remain at I/O draft level until the mainline `alpha_score` passes a credible prediction gate.
- Because the programmer works solo and requested a single worktree, branch/worktree proliferation should be treated as governance debt unless explicitly requested.
- `.servo` control artifacts are currently intended to be visible in project state; `.serena/` and `.logs/` remain local-only.

- inferences: TODO(inferences)
## Unknowns

- Whether the three development lines should use physical Git branches now, or remain logical planning tracks on the current branch.
- Whether local GPU support should become a separate Worktrack later; current decision is CPU-first.

- unknowns: TODO(unknowns)
## Main Contradiction

- current_main_contradiction: The project needs decision-ready `3d/5d/10d` signals, but current prediction credibility, false-signal controls, and optimization evaluation discipline are not yet sufficient.
- main_aspect: prediction credibility before decision-model reliance.

## Priority Judgment

- current_highest_priority: Prepare `WT-A2-001` intake/review gate under active milestone `MS-S0-001`, then establish the mainline evaluation and anti-false-signal framework.
- long_term_highest_priority: Keep the A-share pipeline reproducible, auditable, line-separated, and capable of turning predictions into explainable decisions.
- do_not_do_now:
  - do not merge `1d` into default mainline scoring
  - do not use day-K-only `1d` results as the final ultra-fast prediction verdict
  - do not prioritize complex decision-model implementation before `alpha_score` passes credibility gates
  - do not expand model complexity to mask execution-layer gaps
  - do not reopen multiple local worktrees without explicit need
  - do not treat generated reports/checkpoints/logs as source truth
  - do not commit/push/branch-mutate without explicit programmer instruction

## Routing Projection

- recommended_repo_action: observe active milestone `MS-S0-001`, then prepare the `WT-A2-001` intake/review gate.
- recommended_next_route: RepoScope.Observe -> milestone-status-skill -> PreMilestoneIntake for `WT-A2-001`.
- suggested_node_type: research/test
- continuation_ready: partial
- continuation_blockers:
  - milestone review gate is not ready for Worktrack Init
  - active milestone development branch for `MS-S0-001` has not been created or checked out yet

## Writeback Eligibility

- writeback_eligibility:
  - `.servo` bootstrap writeback: complete
  - three-track planning writeback: complete
  - revised milestone recommendation: complete
  - formal milestone artifact and backlog: complete for `MS-ENV-000` and `MS-S0-001`
  - milestone activation: complete for `MS-S0-001`
  - `MS-S0-001` prerequisite dependency: satisfied by accepted `MS-ENV-000`
  - worktrack creation: blocked until milestone review gate and worktrack intake are ready for `WT-A2-001`
  - source code mutation: allowed only after an approved worktrack or direct user request

## Notes

- This analysis intentionally avoids deriving unapproved worktracks from existing branch names.
- The first Servo-controlled work should be small enough to validate the harness loop without creating multiple worktrees or collapsing the three tracks back into one.
