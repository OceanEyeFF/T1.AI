# WT-INFRA-001-TQA Gap Report

> Worktrack: WT-INFRA-001-TQA · Infra A 白盒 / 集成 / 契约查漏补缺
> Updated: 2026-07-16

## Baseline

| Metric | Value |
|--------|-------|
| Before TQA | `bash scripts/run_tests_infra_a.sh` → **118 passed** |
| After TQA | **143 passed** (2026-07-16) |
| Smoke | `python scripts/run_infra_smoke.py --json` exit 0 |
| Journal order | `SmokeHarness.simulate_add_stocks` logs `add_symbols` **before** `gate.add_symbols` (download follows) |

## A. Already covered (baseline) — all ✅

| ID | Status | Location |
|----|--------|----------|
| U-G1 三边界 tradable 矩阵 | ✅ | `tests/unit/infra/test_infra_a_scope.py` |
| U-G2 FetchRole 权限 / frozen / append-only | ✅ | `tests/unit/guard/test_fetch_gate.py` |
| U-G3 fork_scope / remove 拒绝 | ✅ | `tests/unit/guard/test_fetch_gate.py` |
| U-G4 lifecycle merge 优先级 + override evidence | ✅ | `tests/unit/guard/test_fetch_gate.py` (`test_merge_lifecycle_priority`) |
| U-G5 IC 唯一实现 + shim parity | ✅ | `tests/unit/guard/test_metrics.py`, `tests/unit/infra/test_infra_a_metrics.py` |
| U-S2 limit_up / missing_bar | ✅ | `tests/unit/infra/test_infra_a_sim_edges.py`, `test_i2b_*` |
| I1 DataLake seeded cache | ✅ | `tests/integration/infra/test_infra_a_flow.py::test_i1_*` |
| I2 sim_start freeze + replay | ✅ | `tests/integration/infra/test_infra_a_flow.py::test_i2_*` |
| I3 session.score_ic | ✅ | `tests/integration/infra/test_infra_a_flow.py::test_i3_*` |
| C1 ashare_lab shim identity | ✅ | `test_c1_lab_shim_identity` |
| Smoke 黑盒脚本 | ✅ | `scripts/run_infra_smoke.py` + `tests/unit/infra/test_smoke_fetch.py` |

## B. TQA fill — status

| ID | Status | Location / note |
|----|--------|-----------------|
| U-G6 sanity | ✅ | `tests/unit/guard/test_sanity.py` |
| U-G7 temporal + as_of | ✅ | `tests/unit/guard/test_temporal.py` + `tests/unit/infra/test_datalake.py` (`test_datalake_*as_of*`) |
| U-G8 execution | ✅ | `tests/unit/guard/test_execution.py` + `period_return` helper |
| U-L2 maintain 增量 | ✅ | `tests/unit/infra/test_datalake_maintain.py` |
| U-L3 stock_basic→DataLake | 🟡 | deferred — see `WT-INFRA-001-tqa-todos.md` |
| U-S1 no-peek | ✅ | already in `tests/unit/sim/test_replay.py` (`test_replay_no_lookahead_*`; no new test) |
| I4 stockpool → maintain | ✅ | `test_i4_stockpool_triggers_maintain` |
| I5 sanity on infra_a panel | ✅ | `test_i5_guard_sanity_on_infra_a_panel` |
| C2 smoke JSON schema | ✅ | `tests/contract/infra/test_smoke_json_schema.py` |
| C3 sim replay smoke | ✅ | `tests/contract/infra/test_sim_replay_smoke.py` |
| C4 types/universe shim | ✅ | `test_c4_lab_universe_types_shim_identity` |

## New / modified files

### Created
- `tests/unit/guard/test_sanity.py`
- `tests/unit/guard/test_temporal.py`
- `tests/unit/guard/test_execution.py`
- `tests/unit/infra/test_datalake_maintain.py`
- `tests/contract/infra/test_smoke_json_schema.py`
- `tests/contract/infra/test_sim_replay_smoke.py`
- `.servo/worktrack/WT-INFRA-001-tqa-gap-report.md`
- `.servo/worktrack/WT-INFRA-001-tqa-todos.md`

### Modified
- `tests/unit/infra/test_datalake.py` — append as_of truncation tests
- `tests/integration/infra/test_infra_a_flow.py` — append I4 / I5 / C4
- `scripts/run_tests_infra_a.sh` — include `tests/contract/infra/`
- `docs/guides/testing_guide.md` — Infra A checklist status
- `src/ashare_infra/guard/execution.py` — added `period_return` helper for U-G8
- `src/ashare_infra/lake/smoke.py` — `simulate_add_stocks` already logs `add_symbols` before `gate.add_symbols` (download follows); verified present, no further edit needed

## Intentionally deferred

| Item | Reason |
|------|--------|
| U-L3 `DataLake.load_stock_basic` | Phase 1 DataLake has no meta API; lifecycle merge already covered via Guard/scope fixtures. Tracked in `WT-INFRA-001-tqa-todos.md`. |
| Real TuShare network IT | Out of scope for Infra A (no-network lane). |
| strategy / advanced / validator→guard | Explicitly out of WT-INFRA-001-TQA. |

## Coverage note

`pyproject.toml` coverage `source` already includes `src/ashare_infra` (and `ashare_lab`). No pyproject change in this TQA pass.
