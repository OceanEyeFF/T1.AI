---
title: "WT-T1-A4 → MS-R4-001 Deferred Handoff"
artifact_type: "milestone-handoff"
from_milestone: "MS-T1-001"
to_milestone: "MS-R4-001"
updated: "2026-07-14T18:56:00+08:00"
owner: "OceanEyeFF"
---

# MS-R4-001 Deferred Handoff（from MS-T1-001）

## Control Signal

- schedule_policy: T1_before_R4（D2=S1）
- r4_may_activate_after: MS-T1-001 completed/accepted
- datalake_work_in_t1: none
- defer_r4_test_items: 0

## What R4 should assume

1. **Test layout is Arch-v1** under `tests/{unit,integration,contract}/`.  
   New TuShare / datalake tests should land in:
   - `tests/integration/sources/`（source/cache adapters）
   - `tests/integration/dataset/`（builders that need lake fixtures）
   - `tests/contract/`（schema/CLI contracts）
   - avoid reintroducing a flat `tests/test_*.py` root dump

2. **Markers**: path auto-marks `unit` / `integration` / `contract`.  
   Prefer putting heavy fetch/replay tests under `integration` and optionally `@pytest.mark.slow`.

3. **Coverage**: `fail_under` is Acc-balanced（see `pyproject.toml` / `docs/guides/testing_guide.md`）.  
   Do not raise floor solely to absorb untested lake code — add focused tests or adjust floor with programmer approval.

4. **No T1 residual path fails** requiring lake rebuild（R3+T1 closed that class of debt）.

## Explicitly not done in T1

- TuShare full-market pull / lake build
- Quota-consuming live API campaigns
- Replacing AkShare as sole production source

## Entry for R4

- Re-open / refresh `.servo/repo/MS-R4-001-pre-milestone-intake-review.md` after T1 final acceptance.
- `depends_on_milestones: MS-T1-001`（live backlog）.
