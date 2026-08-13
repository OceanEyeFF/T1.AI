# White-box: `test_recommendation_validator.py`

| Field | Content |
|-------|---------|
| purpose | Recommendation validate behavior + **Phase 2 cutover locks** |
| SUT | adapters (`Tushare`/`ODP`/`HS300`), `RecommendationValidator.validate` |
| phase | Pre-existing + Phase 2 T1 |
| run | `pytest tests/unit/recommendation/test_recommendation_validator.py -q` |

## Phase 2 cutover cases

- Each adapter holds a `DataLake` (`_lake`)
- `fetch_daily_bars` / `fetch_hs300_daily` call `DataLake.load_*` (spy)
- Same `_lake` instance reused across fetches
- `validate` IC/RankIC call `ashare_infra.guard.metrics` (monkeypatch import site)

## Broader cases (legacy)

- Symbol/schema helpers; return modes; horizons; error paths

## Invariants

- Cutover must fail if adapters bypass DataLake or IC reverts to lab import site only
- Contract scan remains complementary for `import load_or_fetch_*`

## Out of scope

- Integration dataset builder; live network adapters
