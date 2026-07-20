# White-box: `test_infra_a_scope.py`

| Field | Content |
|-------|---------|
| purpose | U-G1 tradable matrix against Infra A fixture meta |
| SUT | `DataScope.is_tradable` + fixture listing bounds |
| phase | Phase 1 / Infra A |
| run | `pytest tests/unit/infra/test_infra_a_scope.py -q` |

## Cases

- Manifest tradable matrix; late-list excluded; missing-bar fixture day

## Invariants

- Uses `tests/fixtures/infra_a/` only

## Out of scope

- FetchGate role permissions → `test_fetch_gate.py`
