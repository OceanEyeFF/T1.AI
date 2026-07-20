# White-box: `test_smoke_fetch.py`

| Field | Content |
|-------|---------|
| purpose | SmokeHarness simulate download / add / set-start / freeze (no network) |
| SUT | `ashare_infra.lake.smoke.SmokeHarness` + CLI default scenario |
| phase | Phase 1 / Infra A |
| run | `pytest tests/unit/infra/test_smoke_fetch.py -q` |

## Cases

- Materialize cache; add stocks then download; shrink window; root-only set_window; sim_start freeze; report shape; CLI

## Invariants

- Injected loader only — never hit live sources
- Journal order: `add_symbols` before download (see TQA gap report)

## Out of scope

- Contract JSON schema → `tests/contract/infra/test_smoke_json_schema.py`
