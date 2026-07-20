# White-box: `test_temporal.py`

| Field | Content |
|-------|---------|
| purpose | U-G7 `truncate_as_of` inclusive / exclusive / empty / date column |
| SUT | `ashare_infra.guard.temporal.truncate_as_of` |
| phase | Phase 1 |
| run | `pytest tests/unit/guard/test_temporal.py -q` |

## Cases

- Inclusive / exclusive; empty; date column; missing index/col raises

## Invariants

- Unsorted index leak covered in audit M2

## Out of scope

- DataLake `as_of` wiring → `test_datalake.py`
