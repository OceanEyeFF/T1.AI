---
title: "WT-B0-001 1d Intraday Data Feasibility Report"
artifact_type: "worktrack-evidence"
worktrack_id: "WT-B0-001"
milestone_id: "MS-S0-001"
updated: "2026-06-11T21:01:55+08:00"
owner: "OceanEyeFF"
---

# WT-B0-001 1d Intraday Data Feasibility Report

## Control Signal

- worktrack_result: pass for read-only B0 feasibility scope
- data_gate_result: blocked for `1d` modeling until live permission and replay proof exist
- primary_candidate: TuShare `stk_mins`
- smoke_candidate: AkShare minute APIs
- repo_ready_for_minute_replay: no
- provider_calls_executed: no
- credential_accessed: no
- model_training_executed: no

## Scope

B0 answers whether the independent `1d` line has a credible intraday/minute data source path. It does not implement a loader, call a provider, train a model, or change mainline `alpha_score`.

## Repo Capability Inventory

### Current adapters

| Path | Current capability | B0 finding |
|---|---|---|
| `src/ashare_lab/data/akshare_source.py` | AkShare daily bars via `stock_zh_a_hist(period="daily")` | Daily only; no minute loader. |
| `src/ashare_lab/data/tushare_source.py` | TuShare `daily`, `daily_basic`, `moneyflow`, `adj_factor`; partitioned parquet daily cache | No `stk_mins` request/normalizer/cache. |
| `src/ashare_lab/data/odp_source.py` | Generic ODP historical loader with `interval` and parquet cache | Useful cache pattern, but not proof of A-share minute coverage. |
| `docs/interfaces/data_contract.md` | Formal Daily Bars contract | No intraday/minute schema. |
| `tests/test_odp_source.py`, `tests/test_tushare_source.py`, `tests/test_source_misc.py` | Cache and adapter behavior tests | No minute replay test. |

### Current replay readiness

- formal minute schema: missing
- dedicated A-share minute adapter: missing
- deterministic fixed-pool fixed-window minute replay test: missing
- usable cache pattern: partially available through ODP interval cache and TuShare daily partition cache
- conclusion: the repo is not ready to run `1d` intraday modeling without a later source/adapter worktrack

## Provider Matrix

| Candidate | Role | B0 verdict | Why |
|---|---|---|---|
| TuShare `stk_mins` | Primary long-history candidate | best candidate but not proven ready | Official documentation says it supports `1min/5min/15min/30min/60min`, has `trade_time/open/high/low/close/vol/amount`, can provide long history, and requires separate minute permission. Permission, cost, rate limit, and local adapter are not verified. |
| AkShare `stock_zh_a_minute` / `stock_zh_a_hist_min_em` | Recent-data smoke/prototype | smoke only | Official docs and issue evidence indicate recent-data limits, especially around 1-minute history. Useful for field samples and parser smoke, not as sole long OOS source. |
| ODP/OpenBB interval loader | Cache substrate / cross-market reference | not data-source proof | Local code supports `interval`, but A-share minute coverage and provider contract are unknown. |
| Other professional vendor/broker data | Fallback long-history candidate | backlog candidate | Could solve history/quality, but no vendor, adapter, cost, or contract is selected. |

## Required Fields And Handling

| Requirement | Current status |
|---|---|
| `time` | Not in current data contract. TuShare has `trade_time`; AkShare has `day/time` depending on endpoint. |
| `open/high/low/close` | Existing daily schema supports prices; minute schema must define adjustment policy. |
| `volume/amount` | Existing daily schema supports fields, but unit conventions differ by provider and must be normalized. |
| `1min/5min/15min` | TuShare documents support. AkShare documents support but history depth is limited. |
| fixed stock pool replay | Not proven. |
| fixed time window replay | Not proven. |
| missing rate / abnormal timestamps | Requires live sample or existing minute cache; not available in repo now. |
| opening auction / lunch break | Must be part of later replay validator. TuShare samples include 09:30 bars, but treatment must be explicit. |
| halt / limit-up / limit-down | Must be joined from daily/trading-state data or provider-specific metadata later. |
| cache strategy | Candidate: partition by `provider/source/freq/symbol/year` with manifest and replay checksum. |

## Gate Conclusion

B0 itself passes: it produced the required feasibility report and machine-readable matrix without external side effects.

The `1d` data gate does not pass yet. No source is locally proven to support fixed stock pool plus fixed historical time-window minute replay. Therefore:

- `1d` modeling remains blocked.
- day-K-only `1d` experiments may remain as negative control only.
- next valid step before B1/B2 is a separately approved live source smoke or source-selection worktrack.
- TuShare `stk_mins` is the first candidate to test if minute permission is available.

## Recommended Next Source Work

1. Ask the programmer whether TuShare minute permission is available and whether a live smoke is approved.
2. If approved, run a tiny deterministic smoke only: 2 to 3 liquid symbols, 1 to 2 trading days, `1min/5min/15min`, no model training.
3. Define an intraday data contract before building B1 labels/features.
4. Implement replay cache only after a source passes permission/history/field checks.

## Evidence Sources

- Local repo files:
  - `src/ashare_lab/data/akshare_source.py`
  - `src/ashare_lab/data/tushare_source.py`
  - `src/ashare_lab/data/odp_source.py`
  - `docs/interfaces/data_contract.md`
  - `docs/overview/three_track_development_plan_20260609.md`
  - `docs/research/1d_independent_model_research_plan.md`
  - `docs/research/1d_independent_model_execution_strategy_20260309.md`
- Public provider docs:
  - TuShare `stk_mins`: https://tushare.pro/wctapi/documents/370.md
  - AkShare stock docs: https://akshare.akfamily.xyz/data/stock/stock.html
  - AkShare issue #5971: https://github.com/akfamily/akshare/issues/5971
- SubAgent explorer:
  - `019eb6c0-add4-7a50-8fb7-f1e83db7713b`
