# White-box: `test_metrics.py`

| Field | Content |
|-------|---------|
| purpose | Guard IC uniqueness + session.score_ic delegation |
| SUT | `ashare_infra.guard.metrics`, lab shim, `TestSession.score_ic` |
| phase | Phase 1 |
| run | `pytest tests/unit/guard/test_metrics.py -q` |

## Cases

- Daily CS IC; lab shim identity; session delegates; empty IC

## Invariants

- Single implementation in guard; shim re-exports same objects

## Out of scope

- Validator import-site lock → `test_recommendation_validator.py` (Phase 2)
