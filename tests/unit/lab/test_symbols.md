# White-box: `test_symbols.py`

| Field | Content |
|-------|---------|
| purpose | Shared A-share symbol normalize for DataLake consumers (Phase 2) |
| SUT | `ashare_lab.symbols.symbol_to_ts_code` / `symbol_to_odp_equity_symbol` |
| phase | Phase 2 |
| run | `pytest tests/unit/lab/test_symbols.py -q` |

## Cases

- SH/SZ/BJ bare + prefixed; SH→SS for ODP; empty / invalid / B-share `9*` rejected by ts_code

## Invariants

- Centralized helpers — validator/builder must not re-implement

## Out of scope

- Universe allowlist (`is_allowed_a_share_symbol`) → integration `test_universe.py`
