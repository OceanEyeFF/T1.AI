---
title: "WT-R4-A2 Consistency Matrix (T5)"
artifact_type: "doc-consistency-check"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
updated: "2026-07-22T10:05:00+08:00"
owner: "OceanEyeFF"
verdict: "consistent"
---

# WT-R4-A2 T5 — Deliverable Consistency Matrix

| Claim | Code / config | Tests | A1 frozen docs | Verdict |
|-------|---------------|-------|----------------|---------|
| DataLake importable on milestone | `src/ashare_infra/lake` | unit datalake | consumer_entry | ok |
| No `ashare_exec` | absent from tree/package include | n/a | out_of_scope | ok |
| Primary tushare / qfq / refresh=False | `make_r4_datalake` | test_r4_contract | lake-source | ok |
| Pool v1 / 61 | r4 constants | schema contract | inventory | ok |
| Layout `tushare_*/{ts_code}/year=/part.parquet` | adapters | schema contract | schema-draft | ok |
| Pool ∩ cache 61/61 three tables | read-only scan | schema contract | inventory | ok |
| `510300.SH` unavailable | empty parts | schema contract | inventory G2 | ok |
| soft80 unmet residual | 61 < 80 asserted | schema contract | inventory G1 | ok |
| No direct `load_or_fetch_*` on R4 surfaces | builder/validator/scripts | no-direct contract | lake-source | ok |
| cache-hit skips fetch | DataLake+adapter | integration T4 | R1 reuse | ok |
| `as_of` truncates | DataLake | integration T4 | schema API note | ok |
| Caps 180 / 80000 | `tushare_rate_limits.toml` | unit+integration | A1 approved | ok |
| Zero live / no lake fill | policy held | mocks only | out_of_scope | ok |
| No Phase4 / EXEC-002 / train | held | n/a | intake | ok |
| No blind merge develop | path-limited checkout | n/a | A2_Q1 | ok |

**Inconsistencies found:** none blocking.  
**Evidence re-verify (2026-07-22):** focused suite **40 passed**.
