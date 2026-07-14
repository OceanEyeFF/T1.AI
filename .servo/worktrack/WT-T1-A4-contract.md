---
title: "WT-T1-A4: markers + CI 分层 + cov 门禁 + 文档 + R4 交接"
artifact_type: "worktrack-contract"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A4"
status: "active"
node_type: "test"
derived_from_milestone: true
created: "2026-07-14T18:55:00+08:00"
---

# WT-T1-A4 markers / cov / docs / R4 handoff

## Control Signal

- branch: milestone/MS-T1-001-test-suite-rewrite
- baseline_branch: develop
- worktrack_branch: milestone/MS-T1-001-test-suite-rewrite
- checkpoint_base_ref: a682ace7c6fbb7a2c292470b807621cfc0dfcb09
- branch_action: use_existing_milestone_branch
- inventory_ref: .servo/worktrack/WT-T1-A1-inventory.md
- acceptance_signal_policy: Acc-balanced
- goal: >
  落地 path-based markers 与 fast/full 入口；实测 cov baseline 并提出 fail_under；
  写测试约定文档与 MS-R4 延后交接；不把 cov 当唯一成功标准。

## Scope

- Auto-apply `unit` / `integration` / `contract` markers by Arch-v1 path
- Mark obvious `gpu` / `slow` tests where cheap
- Fast/full scripts (update min regression to marker/path based fast)
- Measure coverage baseline; propose/update `fail_under` per Acc-balanced
- Docs: short test layout / how to run guide
- R4 deferred handoff artifact（T1 precedes R4）

## Non-goals

- MS-R4 datalake work
- Further test architecture moves
- Inflating coverage with low-value tests

## Acceptance

- [x] markers applied (auto and/or explicit)
- [x] fast + full entrypoints documented/runnable
- [x] cov baseline recorded; fail_under set to 76 (Acc-balanced)
- [x] R4 handoff doc exists
- [x] full pytest still green (396 passed)

## Close

- status: completed
- closeout_ref: .servo/worktrack/WT-T1-A4-closeout.md
- completed_at: 2026-07-14T18:58:00+08:00
