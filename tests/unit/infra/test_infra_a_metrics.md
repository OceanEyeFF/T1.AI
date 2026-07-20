# White-box: `test_infra_a_metrics.py`

| Field | Content |
|-------|---------|
| purpose | U-G5 IC on Infra A panel + lab shim identity |
| SUT | `ashare_infra.guard.metrics` vs `ashare_lab.evaluation.metrics` |
| phase | Phase 1 / Infra A |
| run | `pytest tests/unit/infra/test_infra_a_metrics.py -q` |

## Cases

- Panel shape / positive mean IC; shim identical to guard module object

## Invariants

- Guard is the single implementation; lab is re-export

## Out of scope

- Degenerate CS-IC → `test_phase1_audit_fixes.py` (M5)
