# White-box: `test_replay.py`

| Field | Content |
|-------|---------|
| purpose | U-S1 replay no-lookahead + scripted fills + volume lots |
| SUT | `ReplayEngine` / planner visibility |
| phase | Phase 1 |
| run | `pytest tests/unit/sim/test_replay.py -q` |

## Cases

- Planner sees only prev history; buy then sell script; lots→shares; first day needs prev_close

## Invariants

- No future bar peek in planner

## Out of scope

- Session scope filter (integration I2)
