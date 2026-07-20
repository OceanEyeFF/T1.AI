# White-box: `test_fetch_gate.py`

| Field | Content |
|-------|---------|
| purpose | U-G2/G3/G4 DataScope + FetchGate permissions / freeze / lifecycle merge |
| SUT | `FetchGate`, `DataScope`, `merge_symbol_lifecycle` |
| phase | Phase 1 |
| run | `pytest tests/unit/guard/test_fetch_gate.py -q` |

## Cases

- Role add / auto_maintain cannot add / remove rejected / fork shrink / sim_start freeze
- Override lifecycle requires evidence; merge priority
- Inverted window rejected

## Invariants

- Symbols immutable after freeze; role matrix enforced

## Out of scope

- Listing filter helper → `test_listing.py`
