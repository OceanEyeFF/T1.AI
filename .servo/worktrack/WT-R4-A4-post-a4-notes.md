---
title: "WT-R4-A4 post-A4 notes"
artifact_type: "worktrack-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-08-03"
owner: "OceanEyeFF"
status: "post_a4_package"
---

# WT-R4-A4 post-A4 notes

Small package after A4 Gate/Close (`pass_with_residuals`). Tip after commit: **TBD** (parent commits). Gate close writeback tip already stamped in closeout as `e0b683d`.

## AO-O4-A (static scan)

- Expanded `tests/contract/infra/test_no_direct_load_or_fetch.py` to full-tree static AST scan of `src/ashare_lab/**/*.py` and `scripts/**/*.py`.
- Allow only `load_or_fetch*` imports from modules starting with `ashare_infra.lake`.
- Deferred allowlist: `scripts/build_sequence_dataset_market_state.py` only (intentional imports asserted).
- Tier A = static `Import` / `ImportFrom` only; **no** getattr/importlib dynamic bypass detection.
- AO-O4 dynamic AST remains deferred.

## F1 fix (derived rebuild)

- Keep year overwrite for written years (`part.parquet` replace, atomic tmp+replace).
- After write, **prune** derived `year=*` under `{family}/{ts_code}` to the qfq cache year set.
- Optional `rebuild="incremental"`: date-union merge with **new wins**, then write + prune.
- Default `rebuild="full"`: write computed frames (year overwrite) + prune — **not** bare date-union alone.
- Helpers in `r4_derived_io.py`: `list_r4_qfq_cache_years`, `list_r4_derived_years`, `prune_r4_derived_years`, `merge_r4_derived_by_date`.

## Residuals

- `A4_F1` → `fixed_post_a4` in MS residual confirmation register.
- F2 / F4 remain doc-only.
- MS residual confirmation still `pending_programmer_confirmation` (not auto-confirmed).

## Out of scope

- No DB migration, no ban-all AkShare, no dynamic AST scan, no MS residual auto-confirm.
