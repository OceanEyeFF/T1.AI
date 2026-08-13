# White-box: `test_datalake.py`

| Field | Content |
|-------|---------|
| purpose | Lock DataLake façade routing: bars / scope / as_of / index / TuShare |
| SUT | `ashare_infra.lake.DataLake` |
| phase | Phase 1 + Phase 2 (T0 `load_index_daily`) |
| run | `pytest tests/unit/infra/test_datalake.py -q` |

## Cases

- TuShare wrap via mocked `load_or_fetch_daily_bars`
- `load_scope_bars` multi-symbol
- `as_of` truncation on bars / scope / index
- `load_index_daily` happy path
- `source=smoke` without loader → `RuntimeError`
- Unsupported source → `ValueError`
- `refresh=True` skips legacy flat short-circuit

## Invariants

- No network; fetch mocked or local CSV only
- Upper layers should only see DataLake, not adapters

## Out of scope

- Partition maintain / gap fill → `test_datalake_maintain.py`
- stock_basic meta → `test_datalake_stock_basic.py`
- Audit H1/H2 merge semantics → `test_phase1_audit_fixes.py`
