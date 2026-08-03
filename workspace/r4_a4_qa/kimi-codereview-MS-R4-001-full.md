# Independent Code Review — MS-R4-001 (Tushare DataLake, WT-R4-A0～A4)

## Metadata

- Repo: `/home/oceaneye/github/T1.AI`
- Branch: `milestone/MS-R4-001-tushare-datalake`
- Review range: `git diff 3807f81..HEAD` (merge-base with develop) — 20 commits, 173 files, +16072/−1284
- Tip reviewed: `60cbf22` (docs(MS-R4-001): seed WT-R4-A4 T5 QA/Gate packet)
- Uncommitted at review time: 9 modified `.servo/*` docs (A4 Gate/Close writeback) + untracked `WT-R4-A4-closeout.md`, `output/`, review logs. **No uncommitted src/tests/scripts changes** — working-tree code == HEAD.
- Reviewed at: 2026-07-28T16:21+08:00
- Reviewer: independent third-party pass (defect-first, read-only); no commits, no src/tests edits.

## Executive Summary

- No P0/P1 defects found in any of the five worktracks. Milestone verdict: **pass_with_residuals** — does **not** block Residual Confirmation.
- All AC-relevant claims verified against code/data, not docs: pool 61 ≤ 100 (CS1), tushare-primary cutover real (CS2), pool∩cache 61/61 + derived 61/61 reproducible (CS3), QA numbers re-executed (CS4), Arch-v1 layout kept + no token in repo (CS5), acceptance bound to `custom_research_liquidity_quality_v1@1` (CS6/AC2).
- Independent test run: **118 passed** across the full R4 surface (contract/infra, unit/infra, unit/lab lake+derived, integration/infra, integration/lab derived, integration/sources tushare). The A4 QA "50 passed" suite reproduces exactly (`50 passed in 1.66s`); A0 `tests/unit/stock_pool` 15 passed; A3-focused suite 34 passed.
- Secret scan: no hardcoded Tushare token / 32+ hex credential in `src`, `inputs`, `.servo`; `.env` not tracked by git.
- Residual register matches code reality for every row checked: `soft80_61lt80`, `index_510300_qfq_only`, `trial_exclude_601989` (accepted_residual, constants in `r4_contract.py`), `A4_F1/F2/F4` (doc_only, confirmed in builder/load code), `AO-O_hygiene` (closed_in_A4_T4, verified), `AO-O4_deferred` (deferred — the AST hole is concrete, see F-01).
- 6 P2 findings: two are milestone-introduced (`tushare_batch` manifest/result semantics), two are inherited adapter weaknesses inside the milestone diff (non-atomic cache writes, silent interior holes), two concern enforceability of the no-direct-import contract and the deferred `build_sequence_dataset_market_state.py` live path.
- Residual texts two minor cases *understate* current state (caps wiring landed in A3; A2's 10-failed dataset tests now 11-pass) — stale documentation, not overclaiming.
- MS final acceptance itself remains correctly gated: AC6 `pending_programmer_confirmation`, `programmer_confirmed: false`. This review supports proceeding with the Residual Confirmation round.

## Per-WT Findings

### WT-R4-A0 — registry / pool / symbols.csv — **Sound**

- `inputs/pools/research_liquidity_quality/symbols.csv:1-62` — 61 symbols, zero duplicates, all valid main-board codes; `config.toml:9` `symbols_count = 61` machine-checked against CSV by `registry.py:191-195`.
- Cap slicing `eligible[:soft][:hard]` at `strategy.py:226-228` — no off-by-one; constructor rejects soft>hard (`:158-159`); pinned by `test_hard_cap_enforced`.
- Old⊆new verified independently: low_manipulation 14/14 ⊆ new pool, +47 new. Export copies content-identical to source.
- Amount unit hotfix `/1e5` (千元→亿元) correct (`strategy.py:310-314`) and test-pinned.
- `pytest tests/unit/stock_pool/ -q` → 15 passed (matches closeout).
- Note: A0 impl landed **at** base `3807f81`; A1–A4 never touched pool artifacts (empty diff on those paths).
- P3 hygiene: ≤100 cap is not a registry-level invariant (`registry.py:72-74` only checks `symbols_count > 0`); exported CSVs are CRLF vs LF source; `output/stock_pools/` copy untracked and not gitignored — three copies of pool artifacts exist with drift risk.

### WT-R4-A1 / A2 — make_r4_datalake / r4_contract / façade / cache schema / cutover — **Sound, no P0/P1**

- Factory defaults correct (`r4_contract.py:155-174`: tushare primary, qfq, refresh=False); unit-tested.
- As-of via boolean mask (`guard/temporal.py:32-35`) — unordered indexes cannot leak post-as_of rows; integration test proves cache-hit + as_of with fetch hard-failing if touched.
- qfq/hfq full-span refetch on any gap prevents mixing adjustment bases (`tushare_source.py:367-373`) — implements contract §6 "禁止静默拼接".
- Cache schema contract passes against the real on-disk cache (61/61 pool coverage tests actually executed, not skipped); A2 evidence set re-run: 42 passed (closeout claimed 40).
- Cutover is real: `dataset/builder.py:65-71,109-116` routes tushare via `make_r4_datalake`; four validator adapters via DataLake; `ashare_lab.data.*` are `sys.modules` shims, not duplicates.
- Stale residuals (understate, not overclaim): "caps not wired" fixed in A3 (`tushare_source.py:168,177,190,203,211,219` all call `acquire_tushare_call`); A2's 10-failed `test_dataset_builder.py` now 11-passed.
- P2/P3 findings F-01, F-03, F-04, F-07, F-08 below.

### WT-R4-A3 — caps / freq-wall / resume / limited-live / fund_daily — **Sound, no P0/P1**

- 180/min: min-interval pacing `60/rpm`, sleep outside lock, re-check under lock (`tushare_rate_limit.py:66-70,141-153`) — thread-safe, no burst/off-by-one.
- 80000/day: pre-increment check `used >= daily_per_api` (`:121-127`) allows exactly 80000; Asia/Shanghai day roll tested; raises before network — cap cannot be overshot.
- Caps live *inside* `fetch_tushare_*`, so even façade-bypassing callers hit the limiter — the "single capped live path" claim holds for all in-repo paths **except** the deferred script (F-02).
- Freq-wall: immediate re-raise, no backoff sleep (`tushare_source.py:269-274`, test asserts exactly 1 attempt); batch pauses with job pending, no tight loop.
- Resume: status-filtered (`pending_jobs`), not offset-based — no resume off-by-one; checkpoint after every job; legacy failed-wall requeue tested.
- Register↔code match verified: `R4_SOFT80_STATUS="accepted_residual"`, `R4_INDEX_REQUIRED_NAMESPACES={tushare_qfq}`, `R4_TRIAL_EXCLUDE_SYMBOLS` (`r4_contract.py:43-55,59,97-108`).
- A3-focused suite re-run: 34 passed.
- P2/P3 findings F-05, F-06, F-09–F-11 below.

### WT-R4-A4 — derived build/load / AO-O hygiene / QA reproducibility — **Sound, no P0/P2**

- QA "50 passed" suite reproduces exactly (derived 27 + hygiene/dataset 23); derived coverage on disk = 61 symbols × 2 families × years 2023–2026 (486 parts; `601989.SH` missing year=2026, consistent with the accepted trial-exclude residual).
- Cache-only proven empirically: `600519.SH` rebuilt from cache → all 8 parts **byte-identical** to on-disk derived; builder reads only via pure parquet reader; tests explode on any fetch call and still pass.
- Determinism verified: sorted output, no timestamp leakage, features called directly with `shift(1)` lookahead guards (`momentum.py:84,120,132`; `technical.py:80`).
- Load API semantics correct: missing parts → empty schema frame (`lake/__init__.py:238-241`); unknown family/missing columns → clear ValueError; inclusive slicing matches `load_daily_bars`.
- AO-O fix (`15c078d`) closes what it claims: O1 allowlist narrowed to `ashare_infra.lake` only, repo-wide grep confirms zero stray `load_or_fetch_*` imports; O2 dataset tests reseeded (11 passed); O3 dual-track doc accurate.
- F1/F2/F4 doc_only residuals confirmed in code (no stale-year prune; 853 vs 844 family rows; load≠rebuild).
- P3 findings F-12, F-13 below.

## Cross-cutting

- **Architecture**: façade + contract + caps-in-fetch layering is coherent; the one structural soft spot is enforceability (AST scan scope, F-01) and the deferred raw-tushare script (F-02). Limiter is process-local by design — fine under the M1 single-process limited-live policy; must be revisited if that policy changes.
- **Security**: no tokens/credentials in `src`, `inputs`, `.servo` (pattern + 32-hex scans); `.env` untracked; no unapproved full-market campaign found in diff; A4 zero-live verified empirically.
- **Tests**: Arch-v1 layout preserved; contracts genuinely execute against real cache (not skip-masked). Independent run: 118 passed (command in §Verification). Weakness: several closeout commands are pattern-based, not exact file lists (A2 "40", A3 "50") — reproducible only approximately.
- **Docs consistency**: residual register matches code on every row checked; two A2/A3 residual texts are stale *in the safe direction* (describe problems since fixed). `qa-summary.json` tip `15c078d` vs report header `60cbf22` — both correct at their generation times (code tip vs packet tip). Uncommitted `.servo` writeback matches the declared `pending_programmer_commit` state — expected pre-close, not a discrepancy.

## Findings

No qualifying P0–P1 defects.

**P2 (milestone-introduced)**

- **[P2] F-05: Batch manifest reports `completed` despite permanently failed jobs** — `src/ashare_infra/data/tushare_batch.py:614-616` (and `resume_batch` at `:662-673`). Final state derives from `not manifest.pending_jobs()` only; a manifest with a non-wall failed job + rest done ends `state="completed"`. Per-job status survives (no data loss), but the top-level state misleads any consumer checking only `state`.
- **[P2] F-06: One bad symbol aborts the batch with a success-shaped result** — `tushare_batch.py:594-606`. A non-wall exception returns `BatchRunResult(paused=False, pause_kind=None)`, indistinguishable from success without inspecting `manifest.state`; remaining jobs stay pending under `state="failed"`. Result object should carry a failure signal.

**P2 (enforceability / scope-of-guarantee)**

- **[P2] F-01: No-direct-import contract is narrow and bypassable** — `tests/contract/infra/test_no_direct_load_or_fetch.py:17-24,38-55`. Milestone-introduced. (a) Scans only 6 hardcoded files — any new consumer module can import `load_or_fetch_*` freely and the suite stays green; (b) AST check catches only `from … import load_or_fetch*` — module-attribute access, `importlib`, `getattr` all evade; (c) the deferred-target "test" (`:65-68`) is a tautology pinning nothing. Partially registered as `AO-O4_deferred`; the hole is concrete, and the MS-level confirmation should treat the guarantee as "6 named files", not repo-wide.
- **[P2] F-02: Deferred script bypasses façade *and* rate limiter with raw tushare calls** — `scripts/build_sequence_dataset_market_state.py:28-41,321,865`. Pre-existing script, consciously deferred (A2 residual / A2 carry). Beyond the acknowledged `load_or_fetch_*` imports, it calls `pro.fund_daily`/`fut_daily` directly — never through `acquire_tushare_call`, so the 180/80000 caps are unenforced on this path. Deferral should be gated on "not executed during R4", not merely "not scanned".

**P2 (inherited, inside milestone diff range — develop/WT-INFRA provenance)**

- **[P2] F-03: Cache writes are not atomic; corrupt partition fails the load instead of refetching** — `tushare_source.py:298-310` (write in place, no tmp+rename) + `:285-292` (`_read_cached_partitions` catches only `FileNotFoundError`). A crash/concurrent writer mid-`to_parquet` leaves a truncated part; next read raises pyarrow error out of `load_or_fetch_daily_bars` instead of treating cache as miss. Cache should be fail-open.
- **[P2] F-04: Cache-first reads silently serve interior holes** — `tushare_source.py:313-329`. `_date_ranges_to_fetch` with refresh=False only extends span edges; interior gaps (e.g. from an earlier partial failure) are never detected/refetched and are served without warning. The contract's "no permanent holes" guarantee does not extend to the default cache-first path consumers actually use.

**P3 (actionable only)**

- **[P3] F-07: `R4_SYMBOLS_COUNT = 61` hardcoded** — `r4_contract.py:43`. Silently desyncs if the pool is ever regenerated (soft80 deficit-fill is an accepted residual path).
- **[P3] F-08: `make_r4_datalake` doesn't enforce the contract it names** — `r4_contract.py:155-174`. `R4_ADJUST_DEFAULT`/`R4_HISTORY_START` unreferenced by the factory; qfq comes only from a parameter default any caller can override (`lake/__init__.py:128`). Binding is one level softer than contract language suggests.
- **[P3] F-09: `fund_daily` fallback invisible to dry-run budgeting** — `tushare_batch.py:51-58,239-246` vs `tushare_source.py:168-185`. ETF jobs budget `daily+adj_factor` but spend `daily+fund_daily`; self-corrects at runtime via cap raise, but dry-run affordability can disagree with live for ETF-heavy manifests.
- **[P3] F-10: Unadjusted fund prices cached in `tushare_qfq` namespace without provenance** — `tushare_source.py:175-185`. Accepted for 510300 (`index_510300_qfq_only`), but the trigger is generic "daily empty" — reuse on a later-split ETF would silently cache raw prices as qfq. No row-level flag.
- **[P3] F-11: Manifest checkpoint write not atomic** — `tushare_batch.py:198-206`. Crash mid-save corrupts the only resume state; tmp+rename is a cheap fix.
- **[P3] F-12: Partial-window rebuild silently degrades a year part** — `src/ashare_lab/derived/builder.py:129-135`. `start`/`end` slice before feature compute, so a partial rebuild overwrites `year=YYYY/part.parquet` with warm-up-truncated data. Canonical full builds are unaffected (verified deterministic); the register's F1 text covers no-prune but not this degrade half.
- **[P3] F-13: `filter_r4_trial_symbols` has no runtime consumer** — `r4_contract.py:97-108`; used only by contract tests. "默认排除 601989" is enforced by test, not yet by any trial runner — re-check when a trial runner lands.
- **[P3] F-14: Submission-discipline** — pool artifacts exist in 3 locations with `output/stock_pools/` untracked & not gitignored; exported CSVs CRLF vs LF source; no on-disk schema version marker in cache/derived layouts; QA coverage numbers (61/61, 486 parts) require local `inputs/data/cache` + gitignored derived parquet — accurate but not regenerable from a fresh clone.

## Verification (actually executed by this review)

```
# Full R4 surface — 118 passed in 2.67s
python -m pytest tests/contract/infra tests/unit/infra \
  tests/unit/lab/test_dataset_builder_lake.py tests/unit/lab/test_r4_derived_builder.py \
  tests/integration/infra tests/integration/lab/test_r4_derived_builder_integration.py \
  tests/integration/sources/test_tushare_source.py -q

# QA-report focused suite (verbatim from WT-R4-A4-qa-report.md) — 50 passed in 1.66s
pytest tests/unit/infra/test_r4_derived_schema.py tests/contract/infra/test_r4_derived_schema_contract.py \
  tests/unit/lab/test_r4_derived_builder.py tests/integration/lab/test_r4_derived_builder_integration.py \
  tests/unit/infra/test_r4_derived_load.py tests/contract/infra/test_r4_derived_load_contract.py \
  tests/integration/infra/test_r4_derived_load_integration.py tests/integration/dataset/test_dataset_builder.py \
  tests/contract/infra/test_no_direct_load_or_fetch.py tests/unit/lab/test_dataset_builder_lake.py -q

# A2 evidence set — 42 passed;  A3-focused set — 34 passed;  tests/unit/stock_pool — 15 passed
```

- Secret scans: `TUSHARE_TOKEN=`/`ts.set_token('…')` patterns repo-wide → 0; `(token|api_key|secret)[:=] hex≥32` in `src`, `inputs`, `.servo` → 0; `git ls-files | grep .env` → untracked.
- Determinism spot-check: `build_r4_derived_symbol('600519.SH')` → 8/8 parts byte-identical to on-disk derived.

## MS 终验建议

- **Verdict: pass_with_residuals.** No P0/P1; every CS/AC claim checked is backed by code and reproducible tests.
- **Does NOT block Residual Confirmation.** Recommend proceeding with the round; suggest the confirmation explicitly acknowledge: (a) F-01's scan scope ("6 files", not repo-wide) as part of accepting `AO-O4_deferred`; (b) F-02's "deferred = not executed" condition; (c) F-05/F-06 as new minor defects to either accept as residuals or schedule for post-MS fix.
- AC6 gate remains correctly closed (`programmer_confirmed: false`) — final acceptance/merge stays blocked until the programmer confirms, as designed.

## Suggested follow-up

pytest / checks worth re-running at MS close or first post-MS worktrack:

1. `pytest tests/contract/infra tests/unit/infra -q` after any change to `tushare_source.py` / `tushare_batch.py` (covers F-03/F-04/F-05/F-06 fix validation).
2. Add a tmp+rename atomic-write test for cache parts and manifest checkpoints (F-03, F-11).
3. Add a repo-wide (not 6-file) no-direct scan or the AST-hardened contract when `AO-O4` is picked up (F-01).
4. Manual spot-check: confirm `scripts/build_sequence_dataset_market_state.py` is never invoked in R4 pipelines (F-02) — e.g. grep crontab/`deployment/` and run-books.
5. Manual spot-check: `comm -23 inputs/pools/low_manipulation/symbols.csv <(tail -n+2 inputs/pools/research_liquidity_quality/symbols.csv)` should stay empty if the pool is regenerated.
6. When a trial/dataset runner lands, assert it consumes `filter_r4_trial_symbols` (F-13).
