# White-box: `test_datalake_maintain.py`

| Field | Content |
|-------|---------|
| purpose | U-L2 incremental maintain: date-range planning + second-round gap-only fetch |
| SUT | `tushare_source._date_ranges_to_fetch` + `DataLake.load_daily_bars` (raw adjust) |
| phase | Phase 1 / Infra A TQA |
| run | `pytest tests/unit/infra/test_datalake_maintain.py -q` |

## Cases

- Empty cache → full range
- Tail / head+tail extend
- Two-round fetch: second call only requests gap (`adjust=raw`)

## Invariants

- No network; mocked TuShare fetch
- qfq full-span refetch is covered in audit suite, not here

## Out of scope

- H2 qfq incremental → `test_phase1_audit_fixes.py`
