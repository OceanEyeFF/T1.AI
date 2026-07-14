---
title: "Repo Analysis"
artifact_type: "repo-analysis"
generated_from: "servo-set-harness-goal-skill/assets/repo/analysis.md"
updated: "2026-07-14T10:50:00+08:00"
owner: "OceanEyeFF"
---

# Repo Analysis

> 这是 `.servo/repo/analysis.md` 的运行状态，用来记录 RepoScope 的阶段性分析与优先级判断。它是决策支撑 artifact，不是 goal truth，也不是 worktrack queue。

## Metadata

- repo: T1.AI
- baseline_branch: develop
- baseline_ref: 1f7eab1ccc9a065c6eff330b4b2c588e5fbb24cc
- updated: 2026-07-14T10:50:00+08:00
- analysis_status: refreshed-after-control-plane-realignment-2026-07-14
- analysis_stale: false

## Facts

- The repo is a Python A-share low-frequency research and execution framework (`ashare-lab`).
- Three development lines remain in charter: `3d/5d/10d`, independent `1d`, and decision model.
- Current checkout is `/home/oceaneye/github/T1.AI` on `develop` @ `1f7eab1`, clean and synced with `origin/develop`.
- Repo root now follows MS-R2 three-zone layout: `inputs/` → `workspace/` → `outputs/`, with `src/` as code core.
- Completed/accepted Servo milestones include MS-ENV-000, MS-S0-001, MS-S1-001, MS-S2-001, MS-R0-001, MS-R1-001, MS-R2-001.
- Live milestone backlog has `active_count: 0` and planned `MS-R3-001` then `MS-R4-001`.
- No active worktrack; continuous milestone autonomy is inactive while `active_milestone: none`.
- Persistent approval gates remain: commit, push, destructive cleanup, dependency changes, production/external side effects, final milestone acceptance.

## Inferences

- Immediate repo-level work is governance/pipeline routing, not coding under an active milestone.
- Highest near-term pipeline candidate is `MS-R3-001` (deep cleanup of archived/stale artifacts), which unblocks `MS-R4-001` (TuShare data lake).
- Residual MS-R2 pytest path failures are better treated as cleanup/data-contract follow-through under R3/R4 than as reopen of R2.
- Research credibility of mainline `3d/5d/10d` remains a standing product gap, but it is not the current control-plane idle-state blocker; the idle blocker is missing confirmed active milestone + intake.
- Decision-model implementation should stay deferred until mainline signals pass credibility gates.

## Unknowns

- Exact scope and aggressiveness of MS-R3-001 deletion set (docs/archive, old TOML, old scripts, checkpoints) pending pre-milestone intake.
- Whether MS-R4-001 should start from a narrow lake bootstrap or a broader provider-cutover once R3 completes.
- Whether residual 2 failing tests should be explicit MS-R3 acceptance criteria or deferred to MS-R4 data rebuild.

## Main Contradiction

- current_main_contradiction: Product still needs decision-ready `3d/5d/10d` signals, but the current control plane is correctly idle on infrastructure/cleanup pipeline work (R3→R4) after restructuring; research promotion and infra cleanup must not be collapsed into one milestone.
- main_aspect: pipeline sequencing vs research credibility backlog.

## Priority Judgment

- current_highest_priority: Keep control plane truthful, then decide whether to run pre-milestone intake for `MS-R3-001`.
- long_term_highest_priority: Keep the A-share pipeline reproducible, auditable, line-separated, and capable of turning predictions into explainable decisions.
- do_not_do_now:
  - do not invent an active milestone or Worktrack Init without intake + programmer confirmation
  - do not merge `1d` into default mainline scoring
  - do not promote `alpha_score` / prediction heads
  - do not treat generated reports/checkpoints/logs as source truth
  - do not commit/push/branch-mutate without explicit programmer instruction
  - do not reopen MS-R2 as active; it is completed/accepted

## Routing Projection

- recommended_repo_action: RepoScope.Decide — `repo-whats-next` or start `MS-R3-001` pre-milestone intake when programmer requests progression
- recommended_next_route: RepoScope.Decide -> (optional) pre-milestone-intake for MS-R3-001
- suggested_node_type: cleanup / docs / config (for MS-R3 candidate)
- continuation_ready: yes for Decide/Intake; no for Worktrack Init
- continuation_blockers:
  - no confirmed active milestone
  - MS-R3-001 pre-milestone intake not yet written

## Writeback Eligibility

- writeback_eligibility:
  - control-state realignment: complete (2026-07-14)
  - snapshot-status refresh: complete (2026-07-14)
  - analysis refresh: complete (this file)
  - milestone backlog/history: already consistent with idle + planned R3/R4
  - git commit of control-plane refresh: deferred until programmer approval
  - source code mutation: blocked until approved worktrack or direct user request
  - milestone activation / Worktrack Init: blocked until intake + confirmation

## Notes

- This analysis replaces the stale 2026-06-11 MS-ENV/MS-S0 routing projection.
- Refresh evidence: git HEAD `1f7eab1`, milestone-history § MS-R2-001, milestone-backlog planned R3/R4, programmer request to update control plane on 2026-07-14.
- Refresh report: `.servo/repo/refresh-report-control-plane-2026-07-14.md`
