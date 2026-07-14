---
title: "WT-T1-A3: Arch-v1 目录分层搬迁 + fixtures"
artifact_type: "worktrack-contract"
milestone_id: "MS-T1-001"
worktrack_id: "WT-T1-A3"
status: "active"
node_type: "refactor"
derived_from_milestone: true
created: "2026-07-14T18:38:00+08:00"
---

# WT-T1-A3 Arch-v1 分层搬迁

## Control Signal

- architecture: Arch-v1 (approved)
- inventory_ref: .servo/worktrack/WT-T1-A1-inventory.md
- branch: milestone/MS-T1-001-test-suite-rewrite
- baseline_branch: develop
- worktrack_branch: milestone/MS-T1-001-test-suite-rewrite
- checkpoint_base_ref: c8d642ca6cbd53e095401a945ece91baabbd229d
- branch_action: use_existing_milestone_branch
- goal: 按 Arch-v1 搬迁 tests/；加 conftest + pytest pythonpath；去掉重复 sys.path；行为等价全绿

## Scope

- Create `tests/{unit,integration,contract,support}/...` per Arch-v1
- `git mv` existing test files into target dirs
- Add `tests/conftest.py` + `[tool.pytest.ini_options]` (pythonpath, markers)
- Remove per-file `sys.path` hacks where safe
- Update `scripts/run_develop_min_regression.sh` paths
- Light factories stub under `tests/support/`

## Non-goals

- Cov fail_under numeric lock (A4)
- Marker-based CI wiring beyond declaring markers (A4 can refine)
- Deleting tests beyond already-approved Del-A1
- src/ business behavior changes

## Acceptance

- [x] Directory layout matches Arch-v1
- [x] Full pytest green: 396 passed (py311-private)
- [x] No remaining flat `tests/test_*.py`
- [x] min regression script paths updated

## Close

- status: completed
- closeout_ref: .servo/worktrack/WT-T1-A3-closeout.md
- completed_at: 2026-07-14T18:45:00+08:00
