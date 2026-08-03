---
title: "WT-R4-A3 Consistency Matrix (T5)"
artifact_type: "doc-consistency-check"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
updated: "2026-07-23T13:08:00+08:00"
owner: "OceanEyeFF"
verdict: "consistent_with_residuals"
---

# WT-R4-A3 T5 — Deliverable Consistency Matrix

| Claim | Code / config | Tests / evidence | Docs | Verdict |
|-------|---------------|------------------|------|---------|
| Caps 180/80000 enforce at fetch | `tushare_rate_limit` + `tushare_source` | unit+caps contract | A1 approved; T1 notes | ok |
| Freq-wall pause; resume retries same job | `tushare_batch` | unit batch + B1 | T2/T3 addon | ok |
| estimated_calls qfq=2 → daily+adj | `expand_job_api_calls` | unit + R1 integration | T3 AO-B3 | ok |
| No tight-loop on 2002 | `_retry_with_backoff` | freq-wall unit | T3 AO-B4 | ok |
| Live single path | `make_r4_refresh_executor` | R1 integration; T3 live manifests | T3 notes | ok |
| 510300 qfq filled | cache `tushare_qfq/510300.SH` | schema contract | T3 live verify | ok |
| 510300 basic/mf N/A | empty OK | schema accepted-empty | T4 D6 | residual_ok |
| Staleness 6/7 refreshed | cache date_max 2026-07-22 | live-verify | T3 notes | ok |
| 601989 upstream exhausted | registry kept; trial exclude | unit+contract | T4 D5 | residual_ok |
| Soft80 accepted residual | `R4_SOFT80_STATUS` | unit+contract | T4 D1 | residual_ok |
| Pool v1@1 / 61 unchanged | registry + constants | schema | T4 D4 | ok |
| Zero live on T4 | policy | no new live manifests | T4 notes | ok |
| AO-O* deferred | — | — | A3_Q3 / T4 D7 → A4 | residual_ok |
| No token / no full-campaign / no train / no EXEC | policy held | n/a | contract | ok |
| No blind merge develop | milestone branch only | n/a | branch policy | ok |

**Inconsistencies blocking Gate:** none.  
**Evidence re-verify (2026-07-23):** focused A3 suite **50 passed**.

## Residual package (for Gate)

| ID | Residual | Disposition |
|----|----------|-------------|
| R-soft80 | 61 < soft_target 80 | **accepted** (T4); hard_cap 100 OK |
| R-510300-basic-mf | ETF stock APIs empty | **accepted** (index qfq-only) |
| R-601989 | TuShare ends 2025-08-12 | **accepted**; trial exclude default |
| R-AO-O | dataset tests / allowlist / toml | **deferred → A4** |
| R-A2-carry | market_state deferred; backtest hard-cut | track in A4 / docs |
