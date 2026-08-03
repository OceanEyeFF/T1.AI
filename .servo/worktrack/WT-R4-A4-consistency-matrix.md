---
title: "WT-R4-A4 Consistency Matrix (T5)"
artifact_type: "doc-consistency-check"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-28T15:17:00+08:00"
owner: "OceanEyeFF"
verdict: "consistent_with_residuals"
tip: "60cbf22"
---

# WT-R4-A4 T5 — Deliverable Consistency Matrix

| Claim | Code / config | Tests / evidence | Docs | Verdict |
|-------|---------------|------------------|------|---------|
| Derived layout/schema (T1) | `R4_DERIVED_*` + year parts | schema unit+contract | derived-schema + README | ok |
| Cache-only builder Return5/10/20+RSI (T2) | `ashare_lab.derived` / `r4_derived_io` | builder unit+integration | T2 notes | ok |
| Load API filesystem-only (T3) | `DataLake.load_derived*` | load unit/contract/integration | T3 notes + README | ok |
| Arch-v1 tests | tests/{unit,integration,contract} | focused suite | contract | ok |
| AO-O1 allowlist lake-only | `test_no_direct_load_or_fetch` | contract green | T4 notes | ok |
| AO-O2 dataset_builder fixed | `test_dataset_builder` + lake unit | 23 hygiene pass | T4 notes | ok |
| AO-O3 toml dual-track doc | `data_source.toml` comments | doc-only | T4 notes | ok |
| AO-O4 deferred | — | — | T4 / residuals | residual_ok |
| Pool 61 / trial 60 | registry + trial exclude | A4_Q6 / QA | QA report | ok |
| Soft80 / 510300 / 601989 documented not reopened | A3 locks | n/a (policy) | A3 closeout + QA | residual_ok |
| F1/F2/F4 doc-only | no code fix | T1–T3 review | review + QA | residual_ok |
| Zero live / no token / no full-campaign / no blind merge | policy held | no live manifests | contract | ok |

**Inconsistencies blocking Gate:** none.  
**Evidence re-verify (2026-07-24):** focused A4 suite **50 passed** @ tip `60cbf22` (T5 packet).  
**Gate (2026-07-28):** accepted `pass_with_residuals`; Residuals round confirmed.

## Residual package (for Residuals round → Gate)

| ID | Residual | Disposition |
|----|----------|-------------|
| R-soft80 | 61 < soft_target 80 | **proposed accept**（A3） |
| R-510300-qfq | index qfq-only | **proposed accept**（A3） |
| R-601989 | trial exclude | **proposed accept**（A3） |
| R-F1/F2/F4 | derived semantics | **proposed accept**（doc-only） |
| R-AO-O4 | AST optional | **proposed defer** |

**Verdict:** `consistent_with_residuals`
