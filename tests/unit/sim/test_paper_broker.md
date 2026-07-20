# White-box: `test_paper_broker.py`

| Field | Content |
|-------|---------|
| purpose | Mark-to-market + same-day sell ordering with prior lots |
| SUT | `PaperBroker` |
| phase | Phase 1 |
| run | `pytest tests/unit/sim/test_paper_broker.py -q` |

## Cases

- MTM includes cash + positions; sell-before-buy same day when prior lot exists

## Invariants

- Deterministic cash/position book

## Out of scope

- Missing-bar policies → audit M4
