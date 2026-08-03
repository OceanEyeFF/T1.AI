---
title: "WT-R4-A4 QA Report (CS4)"
artifact_type: "worktrack-qa-report"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-28T15:17:00+08:00"
owner: "OceanEyeFF"
tip: "60cbf22"
live_pull: "none"
proposed_gate_verdict: "pass_with_residuals"
gate_status: "accepted"
---

# WT-R4-A4 QA Report — CS4 Quality Audit Handoff

## Control Signal

```yaml
artifact_type: worktrack-qa-report
milestone_id: MS-R4-001
worktrack_id: WT-R4-A4
tip: 60cbf22
generated_at: "2026-07-24T14:50:00+08:00"
gate_accepted_at: "2026-07-28T15:17:00+08:00"
live_pull: none
pool: custom_research_liquidity_quality_v1@1
registry: 61
trial: 60
trial_exclude: ["601989.SH"]
derived_m1: Return5/10/20 + RSI
proposed_gate_verdict: pass_with_residuals
gate_status: accepted  # Formal Gate 2026-07-28
ms_residual_confirmation: pending_programmer_confirmation  # do NOT mark confirmed
```

## Scope

| Item | Status |
|------|--------|
| Pool | `custom_research_liquidity_quality_v1` @ **1** |
| Registry | **61** symbols |
| Trial subset | **60** (exclude `601989.SH`; derived still present for registry) |
| Cache base | A3: pool∩cache **61/61** + `510300.SH` qfq |
| Derived M1 | Return5d/10d/20d + RSI（ATR optional; MACD/Boll/market-state deferred） |
| Live | **zero** throughout A4（no token; no full-campaign/train/Phase4/EXEC-002） |

## Cache Layer Summary（upstream A3）

- Pool ∩ cache coverage: **61/61** under `inputs/data/cache/tushare_*`
- Index anchor: `510300.SH` **qfq-only**（basic/mf N/A accepted residual）
- Soft80: 61 < soft_target 80；hard_cap 100 OK（accepted @ A3）

## Derived Coverage

| Family | Coverage vs registry | Years |
|--------|----------------------|-------|
| momentum | **61/61** | 2023–2026 |
| technical | **61/61** | 2023–2026 |

Layout: `inputs/data/derived/{family}/{ts_code}/year=YYYY/part.parquet`（A4_Q2）.

## Load API Status（T3）

- `DataLake.load_derived*` / `make_r4_datalake(..., derived_root=...)` — **filesystem-only**
- Missing parts → empty schema frame；no TuShare fetch
- Arch-v1 unit/contract/integration green（see T3 notes）

## Hygiene（T4）

| ID | Status |
|----|--------|
| AO-O1 allowlist lake-only | **done** |
| AO-O2 dataset_builder tests | **done**（23 pass with allowlist/lake unit） |
| AO-O3 toml dual-track doc | **done** |
| AO-O4 AST contract | **deferred**（optional） |

## Accepted Residuals（proposed; WT Residuals round pending）

| ID | Summary | Disposition |
|----|---------|-------------|
| soft80_61lt80 | 61 < soft_target 80 | proposed accept（A3 lock） |
| index_510300_qfq_only | ETF qfq-only | proposed accept（A3 lock） |
| trial_exclude_601989 | trial 60; registry 61 | proposed accept（A3 lock） |
| A4_F1 | stale year dirs not pruned | proposed accept（doc-only） |
| A4_F2 | family row counts may differ | proposed accept（doc-only） |
| A4_F4 | refresh ≠ rebuild derived | proposed accept（doc-only） |
| AO-O4_deferred | AST optional | proposed accept（defer） |

Optional footnotes（non-blocking）: F3 private cache reader reuse；F5 infra→lab thin dep.

## Test Evidence

Focused A4 suite（derived 27 + hygiene/dataset 23）:

```text
pytest \
  tests/unit/infra/test_r4_derived_schema.py \
  tests/contract/infra/test_r4_derived_schema_contract.py \
  tests/unit/lab/test_r4_derived_builder.py \
  tests/integration/lab/test_r4_derived_builder_integration.py \
  tests/unit/infra/test_r4_derived_load.py \
  tests/contract/infra/test_r4_derived_load_contract.py \
  tests/integration/infra/test_r4_derived_load_integration.py \
  tests/integration/dataset/test_dataset_builder.py \
  tests/contract/infra/test_no_direct_load_or_fetch.py \
  tests/unit/lab/test_dataset_builder_lake.py -q
→ 50 passed
```

Optional JSON: `workspace/r4_a4_qa/qa-summary.json`

## Explicit Non-Goals Held

- No live fetch / no token in repo
- No full-campaign / train / Phase4 / EXEC-002
- No soft80 expansion / registry reselection
- No blind merge develop
- A4_Q7: WT close ≠ MS final acceptance；MS residual confirmation **separate**（AC6）

## Refs

| Artifact | Path |
|----------|------|
| Schema | `.servo/worktrack/WT-R4-A4-derived-schema.md` |
| README | `inputs/data/derived/README.md` |
| T1–T4 notes | `.servo/worktrack/WT-R4-A4-t{1,2,3,4}-notes.md` |
| T1–T3 review | `.servo/worktrack/WT-R4-A4-t1-t3-review.md` |
| Consistency | `.servo/worktrack/WT-R4-A4-consistency-matrix.md` |
| Residuals round | `.servo/worktrack/WT-R4-A4-residuals-round.md` |
| Gate evidence（draft） | `.servo/worktrack/WT-R4-A4-gate-evidence.md` |
| MS residual register | `.servo/repo/MS-R4-001-residual-confirmation.md` |

## Next

1. **Residuals round**（`R4-A4-RESIDUALS`）— programmer confirm → then
2. **Formal Gate**（proposed `pass_with_residuals`）→ Close
