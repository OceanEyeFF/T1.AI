# White-box: `test_dataset_builder_lake.py`

| Field | Content |
|-------|---------|
| purpose | Phase 2 T2: DatasetBuilder loads only via DataLake + symbol resolve |
| SUT | `DatasetBuilder._lake` / `_resolve_lake_symbol` / `_load_stock_data` / `_load_benchmark_data` |
| phase | Phase 2 |
| run | `pytest tests/unit/lab/test_dataset_builder_lake.py -q` |

## Cases

- Constructor holds DataLake
- Resolve: tushare→ts_code, odp→yfinance
- Spy: `_load_stock_data` → `load_daily_bars`; benchmark → `load_index_daily`

## Invariants

- No direct `load_or_fetch_*` in builder body (also contract-scanned)

## Out of scope

- Full feature/label/split build → `tests/integration/dataset/test_dataset_builder.py`
