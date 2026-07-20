# White-box: `test_infra_a_sim_edges.py`

| Field | Content |
|-------|---------|
| purpose | U-S2 limit-up + missing_bar edges on fixture bars |
| SUT | `PaperBroker.match_day` with Infra A bars |
| phase | Phase 1 / Infra A |
| run | `pytest tests/unit/infra/test_infra_a_sim_edges.py -q` |

## Cases

- Limit-up buy blocked; missing bar rejects order (default REJECT)

## Invariants

- Fixture-driven; no network

## Out of scope

- SKIP/RAISE policies → `test_phase1_audit_fixes.py` (M4)
