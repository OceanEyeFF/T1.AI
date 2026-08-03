---
title: "WT-R4-A4 / post-A4 Test Gap Matrix"
artifact_type: "test-gap-matrix"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-08-03T17:10:00+08:00"
owner: "OceanEyeFF"
tip: "45acfda"
reviewers:
  - composer-2.5 (926fd620)
  - grok-4.5 (bdc4daeb)
status: "partially_closed"
code_fix: true  # TG-04 fail-open only
---

# WT-R4-A4 / post-A4 Test Gap Matrix

> 双模型独立只读审查合并结果。**不改代码**；MS AC6 residual confirmation 另批。  
> Gate 已关（`pass_with_residuals`）。「Blocks re-Gate?」= 若按严格 AC 证据再验是否应阻塞。

## Sources

| Reviewer | Agent | Verdict tone |
|----------|-------|--------------|
| Composer 2.5 | [Composer 2.5 测缺漏](926fd620-f60b-4f70-af71-1a423f7e4122) | F1/load/batch 主路径强；corrupt skip / empty-features prune / schema-on-load 为 P1 |
| Grok 4.5 | [Grok 4.5 测缺漏](bdc4daeb-df7b-4971-b84a-adb42b2bbb4c) | 同向；强调 F-03/F-11 无测、incremental+prune、AO-O2 弱断言 |

## Well covered (共识)

- F1 prune + merge happy path（`test_r4_derived_io_prune.py`）
- Builder cache-only / zero-live / missing-cache / lab-feature 对齐
- `DataLake.load_derived*` schema / as_of / start-end / scope / 可复现
- Build→load integration（full）
- AO-O4-A 全树静态 Import 扫描 + market_state deferred 精确 allowlist
- Batch：freq-wall pause/resume、daily cap、F-05 terminal `failed`≠`completed`
- Dataset AO-O2 路由白盒（DataLake hold / source 切换）

## Gap type legend

- **M** = missing test
- **W** = weak / soft assertion
- **K** = wrong or over-mock（真实路径未跑）

## Unified matrix（按严重度）

| Gap ID | Area | Sev | Type | What's missing / weak | Evidence | Suggested test (1 line) | Agree | Blocks re-Gate? |
|--------|------|-----|------|----------------------|----------|-------------------------|-------|-----------------|
| TG-01 | Cache IO (F-03) | P1 | M | `_read_cached_partitions` corrupt/truncated skip 无测 | `tushare_source._read_cached_partitions` `except (OSError, ValueError)` | 一好一坏 `year=*/part.parquet`；load 仅保留好年 | both | **yes** |
| TG-02 | Builder F1 | P1 | M | `rebuild="incremental"` 未断言 prune-to-cache | `build_r4_derived_symbol` 总调 `_prune_families_to_cache`；测仅 full | 陈旧 year + 仅当前 cache year；incremental 后陈旧 year 消失 | both | **yes** |
| TG-03 | Builder F1 | P1 | M | `skipped_empty_features` + 仍 prune 无测 | builder empty-features 分支 + prune always | 极短 bars → `skipped_empty_features` 且 stale year 被 prune | both | **yes** |
| TG-04 | Derived read | P1 | M | `read_r4_derived_parts` **无** corrupt skip（与 cache F-03 不对称） | bare `pd.read_parquet` | 坏 part：文档化 raise **或** fail-open + 测 | Grok | **yes** |
| TG-05 | DataLake load | P1 | M | 盘上缺必填列 → `ValueError` 无测 | `DataLake.load_derived` missing-columns | 写缺 `rsi_14`/`return_5d` parquet；load 抛错 | both | **yes** |
| TG-06 | Builder | P1 | M | full + `start`/`end` 整年覆盖语义未锁定 | `write_r4_derived_parts` 覆盖整年 part | mid-year `start` 后断言 year part 是否被截断 | Grok | **yes** |
| TG-07 | Batch (F-11) | P1 | M | `BatchManifest.save` 原子 tmp+replace 无测 | `*.json.tmp` → `replace` | 断言无残留 `.tmp` | both | no |
| TG-08 | Cache IO (F-03) | P1 | M | `_write_partitioned` 原子写无测 | `part.parquet.tmp`+`replace` | 写两次；最终可读且无 `.tmp` | both | no |
| TG-09 | Derived IO | P2 | M | `write_r4_derived_parts` 原子写无测 | 同 tmp+replace | overwrite 后无 `.tmp` + roundtrip | both | no |
| TG-10 | Derived IO | P2 | M | empty write→`[]`；缺列 `ValueError` | `write_r4_derived_parts` | 空 DF / 缺 `return_5d` | both | no |
| TG-11 | Derived IO | P2 | M | prune 清空后 `symbol_dir.rmdir` | `prune_r4_derived_years` `keep_years={}` | 断言 `{family}/{ts_code}` 消失 | both | no |
| TG-12 | Derived IO | P2 | M | merge 空边 / date 列 / 无 date raise | `merge_r4_derived_by_date` | 参数化 empty / column / invalid | both | no |
| TG-13 | Builder | P2 | M | `start`/`end` / `R4_HISTORY_START` slice | builder 切片分支 | 跨年 cache；有无 start 断言日期集合 | both | no |
| TG-14 | Integration | P2 | M | 无 F1 prune / incremental E2E | integration 仅 happy full | batch rebuild 后 stale year 消失 | both | no |
| TG-15 | Batch | P2 | M | 非墙失败后后续 job 仍 `pending` | `run_batch` 遇非墙失败 early return | 3 job；中失败；后续 pending；resume 跑完 | Grok | no |
| TG-16 | Batch | P2 | M | typed `FrequencyWallPause` 路径 | `except FrequencyWallPause` | executor 抛该类型；pause 语义 | both | no |
| TG-17 | Dataset AO-O2 | P2 | W | quality warn 断言过软 | `or len(log_text) > 0` | 强制高 NaN；断言具体 warning 子串 | both | no |
| TG-18 | Dataset AO-O2 | P2 | M/K | 无真实 `source=tushare` year-partition cache E2E | integration 用 akshare fixture 或整方法 mock | 种 `tushare_qfq/.../year=*/`；不 mock lake 构建 | both | no |
| TG-19 | Dataset AO-O2 | P2 | M | 单票 load 吞异常未测 | `_load_stock_data` except continue | 一 raise 一成功；部分构建 | Grok | no |
| TG-20 | AO-O4-A | P2 | M | 动态旁路（getattr/importlib）故意不扫 | Tier A docstring | 保持 residual；可选 Tier-B xfail fixture | both | no |
| TG-21 | Derived IO | P3 | W | incremental merge 断言弱（`!= 99.0`） | `test_incremental_merge_new_wins_on_shared_date` | 对 lab 重算精确值 | Composer | no |
| TG-22 | Contract | P3 | W | load contract 仅 hasattr/README | `test_r4_derived_load_contract.py` | 可保持薄；或加一次 filesystem smoke | both | no |
| TG-23 | Builder | P3 | M | 非法 `rebuild=` raise | `ValueError` | `rebuild="partial"` raises | both | no |
| TG-24 | Batch | P3 | M | `max_jobs` / completed resume early-return / moneyflow-only | `run_batch` / `resume_batch` / executor | 各补一条窄测 | Composer | no |
| TG-25 | Dataset | P3 | W | fixture `np.random` 可抖 | `sample_stock_cache` | 固定 seed | Grok | no |

## Top priorities（合并）

1. **TG-01** — cache corrupt skip（F-03 声称修复、零测试）
2. **TG-02 / TG-03** — incremental + empty-features 路径的 F1 prune 不变量
3. **TG-04 / TG-05** — derived 读损坏语义不对称；load 缺列硬失败
4. **TG-06** — full rebuild + date slice 的整年覆盖语义锁定
5. **TG-07 / TG-08** — atomic manifest/cache write 回归护栏

## Distinctions

| Kind | Gap IDs |
|------|---------|
| Missing | TG-01–16, TG-18–20, TG-23–24 |
| Weak assert | TG-17, TG-21, TG-22, TG-25 |
| Over-mock | TG-18（部分） |

## Next (需你点头)

- 不自动修测。若要补，建议先做 **P1 簇（TG-01…TG-06）**，再单独 commit。
- MS AC6 residual confirmation 仍另批。


## Remediation status (2026-08-03)

Focused suite after gap fill: **86 passed** (derived/batch/allowlist/dataset related).

| Gap IDs | Status |
|---------|--------|
| TG-01…TG-13, TG-15, TG-16, TG-17, TG-21, TG-23 | **closed** (tests; TG-04 also fail-open in `read_r4_derived_parts`) |
| TG-14, TG-18–20, TG-22, TG-24–25 | **deferred** |

Production delta: `read_r4_derived_parts` corrupt/truncated skip (align cache F-03).
