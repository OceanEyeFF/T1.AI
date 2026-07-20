# White-box: `test_sanity.py`

| Field | Content |
|-------|---------|
| purpose | U-G6 sanity transforms destroy / reduce IC without importing ashare_lab |
| SUT | `ashare_infra.guard.sanity` |
| phase | Phase 1 / Infra A TQA |
| run | `pytest tests/unit/guard/test_sanity.py -q` |

## Cases

- Shuffle / time_reverse destroy IC; lag1 reduces; panel baseline; no lab import

## Invariants

- Guard sanity stays infra-pure

## Out of scope

- Full neutralization battery (deferred)
