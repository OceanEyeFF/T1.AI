---
title: "WT-R3-A2: 按批准清单分批删除"
artifact_type: "worktrack-contract"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A2"
status: "active"
node_type: "cleanup"
derived_from_milestone: true
created: "2026-07-14T12:55:00+08:00"
---

# WT-R3-A2 按批准清单分批删除

## Control Signal

- approved_inventory: .servo/worktrack/WT-R3-A1-inventory.md
- approved_batches: [A, B]
- retained: Batch C + protected paths
- branch: milestone/MS-R3-001-deep-cleanup
- baseline_branch: develop
- checkpoint_base_ref: 6511d8c1f033d60c6eee43847b4682bcbcdbc262

## Scope

- Delete all Batch A + Batch B paths from WT-R3-A1-inventory.md
- Minimal coupling fixes required by those deletes (test asserting archive doc; research README links; pyproject omit for deleted scripts; daily_cs_eval refs)
- Do NOT delete Batch C / protected paths
- Do NOT fix F1/F2 path bugs here (A3) unless blocking

## Non-goals

- TuShare cache / low_manipulation pool / profiles / src
- F1/F2 full path remediation (A3)
- commit/push unless programmer asks
