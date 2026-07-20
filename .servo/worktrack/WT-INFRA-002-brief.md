---
title: "WT-INFRA-002 Brief — Consumer cutover to DataLake / guard"
artifact_type: "worktrack-brief"
worktrack_id: "WT-INFRA-002"
phase: "Phase 2"
updated: "2026-07-19T09:10:00+08:00"
owner: "OceanEyeFF"
status: "gate_ready"
prerequisite: "WT-INFRA-001.5 merged to develop @ 64d3734"
approval:
  scope_locked: true
  locked_decisions:
    - "no live stock_basic in 1.5 (done)"
    - "002 includes light no-direct-load_or_fetch convention test + docs"
    - "do not delete ashare_lab shims"
    - "do not migrate strategy / Research / Product packages"
---

# WT-INFRA-002 — 消费方切到 DataLake / guard

> Phase 2。仅在 **WT-INFRA-001.5 合入/验收后** 开干。  
> 与 MS-R4 可并行，但本 WT **不** 承担 R4 全市场拉数 / 训练；DataLake 口径尽量跟 R4 湖合同一致。

## Goal

业务取数与 IC 入口改走 `ashare_infra` 规范面；行为等价；**shim 保留**。

## Non-goals（刻意不做）

- 删除 `ashare_lab.data` / `sim` / `backtest` / evaluation shim
- 迁 `stock_pool` / `models` / `pipeline` / `strategy` 包结构（Phase 3）
- lab 内去重（sequence_builder 双份等，Phase 4）
- 真实 TuShare 网络 IT（默认无网夹具）

## Prerequisite check

| Item | Status |
|------|--------|
| Phase 1 `ashare_infra` on develop | ✅ `c70aaad` |
| Phase 1.5 stock_basic meta + audit harden | ✅ on `cursor/infra-15-stock-basic-meta` (`32a3342`…`64d3734`) |
| 1.5 merged to `develop` / pushed | ✅ `develop@64d3734` |
| DataLake bars API | ✅ `load_daily_bars` / `load_scope_bars` / meta |
| DataLake index API | ✅ `load_index_daily` (002-T0) |

## Locked task order

| Seq | Task | Notes |
|-----|------|-------|
| T0 | `DataLake.load_index_daily` + unit test | Blocks validator / DatasetBuilder benchmark path; thin wrap of `ashare_infra.data.index_source` |
| T1 | `recommendation/validator.py` → DataLake + `ashare_infra.guard.metrics` | Highest leverage; bars + HS300 calendar + IC |
| T2 | `dataset/builder.py` → DataLake | Update monkeypatch call sites in integration tests |
| T3 | Scripts (must): `scripts/run_sim_replay.py` | Optional same-batch: `run_backtest.py`, `generate_daily_recommendations.py`, `build_sequence_dataset*.py` — prevent re-entry via scripts |
| T4 | Convention: docs + light scan test | Assert listed business modules do not directly `import load_or_fetch_*`; whitelist `ashare_infra/lake` + `ashare_infra/data` only. Keep C1/C4 shim identity tests. |
| GATE | `scripts/run_tests_infra_a.sh` + relevant fast/full subsets | Behavior parity |

## Must-change inventory (locked core)

| Touchpoint | Current | Cutover |
|------------|---------|---------|
| `src/ashare_lab/recommendation/validator.py` | `ashare_lab.data.* load_or_fetch_*`; IC via `ashare_lab.evaluation.metrics` | bars/index → `DataLake`; IC → `ashare_infra.guard.metrics` |
| `src/ashare_lab/dataset/builder.py` | multi-source `load_or_fetch_*` + index | → `DataLake` (needs T0) |
| `scripts/run_sim_replay.py` | `ashare_lab.data.akshare` | → `DataLake` |

`pipeline/` has no direct `load_or_fetch` today — not required in this WT.

## Optional same-batch scripts (防回流，非 locked must)

- `scripts/run_backtest.py`
- `scripts/generate_daily_recommendations.py`
- `scripts/build_sequence_dataset.py`
- `scripts/build_sequence_dataset_market_state.py` (also touches `daily_basic` / `moneyflow` — may need DataLake follow-up APIs or stay deferred)

## Acceptance

- [x] Core three touchpoints no longer **directly** call `load_or_fetch_*`
- [x] `validator` IC uses `ashare_infra.guard.metrics` (same object as lab shim re-export)
- [x] Light convention test green (T4)
- [x] Docs updated: upper layers only `DataLake` / `ashare_infra.guard.*`
- [x] Shim identity (C1/C4) still green; Infra A + related integration green
- [x] Shims **not** deleted; no package-boundary moves

## Gate evidence (2026-07-19)

- branch: `cursor/infra-002-consumer-cutover`
- `scripts/run_tests_infra_a.sh` → 173 passed
- focused: validator + dataset builder + datalake + convention → 50 passed
- `scripts/run_tests_fast.sh` → 383 passed

## Relation to MS-R4

- R4 = pool + reproducible lake contract
- INFRA-002 = consumer import / entry-point hygiene
- Prefer not to fold this into R4 worktrack list; keep independent brief
- If R4 A1/A2 redefine cache path constants, reuse one config site — do not hardcode a second contract

## Start gate

1. Merge / push `cursor/infra-15-stock-basic-meta` → `develop` (1.5 Gate)
2. Branch from that tip for `WT-INFRA-002` (suggested: `cursor/infra-002-consumer-cutover`)
3. Implement T0 → T4 → GATE
