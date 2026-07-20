# White-box: `test_listing.py`

| Field | Content |
|-------|---------|
| purpose | Lock `apply_listing_filter` / `missing_bar_action` policy branches |
| SUT | `ashare_infra.guard.listing` |
| phase | Phase 1 |
| run | `pytest tests/unit/guard/test_listing.py -q` |

## Cases

- Tradable → True for all policies
- EXCLUDE_DAY → False; FILL_NAN → True; RAISE → ValueError
- `missing_bar_action` passthrough

## Invariants

- Does not mutate scope; pure helper

## Out of scope

- Broker consumption of MissingBarPolicy → audit M4 / sim tests
