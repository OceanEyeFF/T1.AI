# White-box: `test_execution.py`

| Field | Content |
|-------|---------|
| purpose | U-G8 ReturnConvention + `period_return` parity helpers |
| SUT | `ashare_infra.guard.execution` |
| phase | Phase 1 |
| run | `pytest tests/unit/guard/test_execution.py -q` |

## Cases

- Convention literals; close_to_close / next_open_to_open on fixtures
- Missing anchor / empty bars / date-column index / zero start price → NaN

## Invariants

- Defaults match validator IC convention (`close_to_close`)

## Out of scope

- End-to-end recommendation validate → `test_recommendation_validator.py`
