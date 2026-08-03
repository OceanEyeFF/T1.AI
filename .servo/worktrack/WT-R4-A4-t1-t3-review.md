---
title: "WT-R4-A4 T1–T3 Review"
artifact_type: "worktrack-review-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
scope: "T1–T3 (A4-D1/D2/D3)"
updated: "2026-07-24T11:25:00+08:00"
owner: "OceanEyeFF"
review_verdict: "pass_with_residuals"
checkpoint_ref: "afba1f0"
code_fix_required: false
---

# WT-R4-A4 T1–T3 Review

## Control Signal

```yaml
verdict: pass_with_residuals
checkpoint: afba1f0
scope: R4-A4-T1 + T2 + T3
code_fix: none  # F1/F2/F4 documented only
next: R4-A4-T4 (AO-O hygiene; do not absorb F1 prune unless re-opened)
```

## Verdict

- **pass_with_residuals** against tip `afba1f0` (derived schema + cache-only builder + DataLake load API).
- Programmer lock: 「T1–T3 review：pass_with_residuals；F1/F2/F4 文档化，不修代码」
- No additional code commit required for these findings.

## Accepted Residuals (document-only)

| ID | Severity | Behavior (accepted) | Doc disposition |
|----|----------|---------------------|-----------------|
| **F1** | P2 | Rebuild overwrites same-year `part.parquet` only; does **not** prune stale `year=*` dirs under `derived/{family}/{ts_code}` | QA (T5) + README: rebuild semantics; for strict cache parity, delete symbol family dir before full rebuild |
| **F2** | P2 | `momentum` / `technical` row counts may differ (independent warm-up `dropna`) | QA + README: consumers read per-family; join on `date` explicitly |
| **F4** | P2 | `DataLake.refresh` does **not** rebuild derived; `load_derived*` is filesystem-only | README / load API: refresh bars via builder `build_r4_derived_*`, not load |

### Optional low tech-debt (non-blocking)

| ID | Note |
|----|------|
| **F3** | `read_r4_qfq_cache` uses private `_read_cached_partitions` — acceptable internal reuse for A4 |
| **F5** | `DataLake.load_derived` → `ashare_lab.symbols.symbol_to_ts_code` — thin infra→lab dep; Gate may footnote |

## Explicit Non-Actions

- Do **not** implement F1 prune / wipe-on-rebuild in T4 unless programmer re-opens.
- Do **not** force equal-length join of momentum+technical in builder.
- Do **not** make `DataLake.refresh` rebuild derived.
- AO-O1/O2 remain **T4 AC** (separate from F1/F2/F4).

## Doc Anchors

- README known limits: `inputs/data/derived/README.md`
- T5 will expand in `.servo/worktrack/WT-R4-A4-qa-report.md` (§ Accepted residuals — derived T1–T3)
- Gate evidence will cite this file + QA table

## Template (for T5 QA paste)

> **Derived rebuild (F1):** incremental build overwrites `year=YYYY/part.parquet` only; stale year directories are not pruned. For strict cache parity, delete symbol family dir before full rebuild.
>
> **Family alignment (F2):** `momentum` and `technical` row counts may differ after warm-up; consumers must join explicitly, not assume identical calendars.
>
> **Load vs refresh (F4):** `load_derived*` is filesystem-only; `DataLake.refresh` does not rebuild derived; use cache-only builder.

## Residuals Round（强制后续关卡）

- Programmer 追加要求：**最后一定要过一轮 Residuals**（`R4-A4-RESIDUALS`）。
- 本文件登记的 F1/F2/F4 **不算**已完成 Residuals round；仅作为候选清单输入。
- T5 之后、**R4-A4-GATE 之前**必须再跑一轮：accept / fix / waive+理由，并写入可引用产物。
- 跳过 Residuals round → **Gate 无效**。

## Milestone Final Acceptance Hook

F1/F2/F4（及 A3 soft80 / 510300 / 601989 等）必须进入 `.servo/repo/MS-R4-001-residual-confirmation.md`。  
MS-R4-001 **final acceptance** 前须与使用者完成 Residual Confirmation Round（完整记录 / 清楚理解 / 接受条件+再阻塞条件）；见 milestone AC6。
