---
title: "WT-T1-A2: 按批准清单删除/合并（Del-A1）"
artifact_type: "worktrack-contract"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A2"
status: "active"
node_type: "cleanup"
derived_from_milestone: true
created: "2026-07-14T18:25:00+08:00"
---

# WT-T1-A2 按批准清单删除（Del-A1 only）

## Control Signal

- approved_inventory: .servo/worktrack/WT-T1-A1-inventory.md
- approved_batches: [Del-A1]
- retained: all other tests; Arch-v1 deferred to A3; Cov-detail deferred to A4
- branch: milestone/MS-T1-001-test-suite-rewrite
- baseline_branch: develop
- worktrack_branch: milestone/MS-T1-001-test-suite-rewrite
- checkpoint_base_ref: 476da6b98e5c7a9ad84df17764a54f4a331105b7
- branch_action: use_existing_milestone_branch

## Scope

- Remove `tests/test_deployment_files.py::test_deployment_directory_structure` only
- Do NOT delete other tests; do NOT migrate directories (A3)
- Do NOT change cov fail_under (A4)

## Non-goals

- Arch-v1 directory moves
- sys.path / fixture consolidation (A3)
- R4 / src business changes
- commit/push unless programmer asks

## Acceptance

- [x] Del-A1 function removed
- [x] `pytest tests/test_deployment_files.py` still green (6 passed)
- [x] no other test file deletions

## Close

- status: completed
- execution_log: .servo/worktrack/WT-T1-A2-execution-log.md
- completed_at: 2026-07-14T18:25:00+08:00
