# White-box: `test_datalake_stock_basic.py`

| Field | Content |
|-------|---------|
| purpose | U-L3 local stock_basic meta API + normalize hardening (Phase 1.5) |
| SUT | `DataLake.load_stock_basic` / `with_stock_basic_meta`; `lake.meta.normalize_*` |
| phase | Phase 1.5 |
| run | `pytest tests/unit/infra/test_datalake_stock_basic.py -q` |

## Cases

- CSV / parquet load; missing file raises
- Tradable parity with U-G1 after meta attach
- `fill_missing_only` vs overwrite
- Zero-pad numeric codes; blank `list_date` rejected; duplicate symbol rejected

## Invariants

- Local cache only — no live TuShare `stock_basic` pull
- Canonical path `{cache_dir}/meta/stock_basic.{csv,parquet}`

## Out of scope

- Live network meta (MS-R4)
