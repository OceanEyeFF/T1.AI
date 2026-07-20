# White-box: `test_fill_model.py`

| Field | Content |
|-------|---------|
| purpose | Daily OHLC touch fill + board blocks + broker ledger edges |
| SUT | `match_limit_daily_ohlc`, `PaperBroker` (via lab shim ≡ infra) |
| phase | Phase 1 |
| run | `pytest tests/unit/sim/test_fill_model.py -q` |

## Cases

- Touch / gap-through buy&sell; buy limit-up block; **sell limit-down block**
- Volume participation; T+1; min commission; insufficient cash; expire

## Invariants

- Board blocks return zero shares with explicit reason codes

## Out of scope

- Replay planner no-peek → `test_replay.py`
