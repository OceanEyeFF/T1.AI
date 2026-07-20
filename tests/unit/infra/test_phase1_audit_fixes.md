# White-box: `test_phase1_audit_fixes.py`

| Field | Content |
|-------|---------|
| purpose | Regression lock for Phase 1 audit findings H1/H2/M1–M5/L1/L3/L4 |
| SUT | `tushare_source` / `odp_source` / `guard.temporal` / `guard.metrics` / `sim.broker` / `sim.fill_model` / `DataLake.with_stock_basic_meta` / `DataScope` |
| phase | Phase 1 harden (post-audit) |
| run | `pytest tests/unit/infra/test_phase1_audit_fixes.py -q` |

## Cases

- H1 refresh sub-range preserves cache; H2 qfq refetch full span
- M1 empty fetch; M2 unsorted `as_of`; M3 ts_code lifecycle; M4 missing_bar policies; M5 degenerate IC → NaN
- L1 participation cap; L3 readonly meta; L4 scope override; ODP legacy nested cache

## Invariants

- No network; each case maps to a named audit ID
- Do not weaken assertions when changing cache semantics

## Out of scope

- Consumer cutover (Phase 2) → validator / builder / convention tests
