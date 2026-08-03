---
title: "WT-R4-A2 Code Review Checklist (filled)"
artifact_type: "worktrack-code-review"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A2"
updated: "2026-07-22T11:45:00+08:00"
scope: "adede39..HEAD (c80b7ae + d21420f), exclude .servo"
proposed_gate: "pass_with_residuals"
reviewer: "Cursor-A2-prep"
---

# WT-R4-A2 Code Review Checklist

**范围:** `adede39..HEAD`（`c80b7ae` + `d21420f`），排除 `.servo`  
**建议 Gate 文案（主线程填写）:** `pass_with_residuals`  
**本清单用途:** 勾选审查项；Gate/Close 回主对话处理  
**再核时间:** 2026-07-22（本地聚焦套件 40 passed；dataset 旧测 10 failed 已复现）

---

## A. 范围与边界

- [x] 无 `src/ashare_exec` / 未把 EXEC 路径带进 milestone  
  - 证据: diff 无 `ashare_exec`；`src/ashare_exec` 不存在
- [x] `pyproject.toml` 仅 `ashare_lab*` + `ashare_infra*`  
  - 证据: `include = ["ashare_lab*", "ashare_infra*"]`
- [x] 未 blind merge `develop` 的无关大块  
  - 证据: 77 非 `.servo` 路径均为 land + cutover + contracts/tests/configs；无 EXEC/train/Phase4
- [x] 改动落在 DataLake land + consumer cutover + contracts/tests/configs

## B. A1 合同绑定（`make_r4_datalake`）

- [x] `default_source=tushare`（`R4_PRIMARY_SOURCE`）
- [x] 调用方使用 `R4_ADJUST_DEFAULT`（`qfq`）— builder / scripts / generate_*
- [x] 默认 `refresh=False`
- [x] 默认 `cache_root=inputs/data/cache`（`R4_CACHE_ROOT`）
- [x] 常量与池绑定可读：`R4_STOCK_POOL_*` / `R4_HISTORY_START` / `R4_SYMBOLS_COUNT=61`

## C. Consumer cutover（必须面）

- [x] `src/ashare_lab/dataset/builder.py` → DataLake / `make_r4_datalake`
- [x] `src/ashare_lab/recommendation/validator.py`（TuShare 路径）→ `make_r4_datalake`
- [x] `scripts/run_backtest.py`
- [x] `scripts/run_sim_replay.py`
- [x] `scripts/generate_daily_recommendations.py`
- [x] `scripts/build_sequence_dataset.py`
- [x] 上述 6 面无直接 `load_or_fetch_*`（经 lab.data 或 infra.data 旁路都不行，理想状态）  
  - 证据: AST `test_no_direct_load_or_fetch` 绿；源码仅 `make_r4_datalake` / `DataLake`  
  - 注: 合同 allowlist 仍允许 `ashare_infra.data`（见 G P1）— 当前 6 面未实际旁路

## D. Lab shim / 包结构

- [x] `ashare_lab.data.*` 为 infra shim（非第二套实现）
- [x] `ashare_lab.sim` / `symbols` 等兼容层行为合理、无静默双写

## E. Caps / 安全

- [x] `inputs/configs/tushare_rate_limits.toml` 存在且为 180 rpm / 80000
- [x] `load_r4_rate_limits` / `r4_approved_*` 可读
- [x] **知悉残差:** caps **未**接到 fetch 限流（A3 接线）  
  - 证据: `tushare_source` 仅 env token + backoff sleep；未读 `r4_approved_*`
- [x] 无硬编码 `TUSHARE_TOKEN`；仅 env / 显式参数
- [x] 聚焦测试零 live / fetch 被 monkeypatch（cache-hit）

## F. 合同与测试证据

- [x] `tests/contract/infra/test_r4_cache_schema_contract.py`：池 61、三 namespace 覆盖、列 schema、year 分区
- [x] 510300 无 parts（accepted residual）显式断言
- [x] soft80（61<80）为 accepted residual（注意 `<80` 写法偏脆）
- [x] `tests/integration/infra/test_r4_datalake_cache_as_of.py`：cache-hit + `as_of`
- [x] `tests/contract/infra/test_no_direct_load_or_fetch.py` 覆盖必须面
- [x] 聚焦 A2 套件本地可绿（unit/contract/integration 子集）— **40 passed**

## G. 已知问题（勾选 = 已确认存在并接受进残差）

### P1（建议进 A3，不阻塞“A2 AC 满足”叙事）

- [x] **Dataset 默认源切换未修旧测:** `tests/integration/dataset/test_dataset_builder.py` **10 failed**（复现 2026-07-22）
- [x] **no-direct allowlist 过宽:** 允许 `ashare_infra.data`，可绕过 DataLake 仍绿
- [x] **caps 未 enforce:** 配置落地 ≠ 运行时限流

### P2（文档/跟踪即可）

- [x] `data_source.toml` 仍默认 `akshare`，与 R4 factory 双轨
- [x] soft80 用 `assert len < 80` 锁定，池扩大会反杀
- [x] `build_sequence_dataset_market_state.py` 仍直连 `load_or_fetch_*`（已 `DEFERRED_SCAN_TARGETS`）
- [x] `run_backtest` / `run_sim_replay` 硬切 tushare（无 `--source`）为故意破坏性变更

## H. Reviewer 签字栏

| 项 | 内容 |
|---|---|
| Reviewer | Cursor-A2-prep（清单核验） |
| 日期 | 2026-07-22 |
| 实现结论 | ☐ pass　☑ pass_with_residuals　☐ fail |
| 阻塞 Gate 的 P0？ | ☐ 有　☑ 无 |
| 残差交接主对话 | ☑ soft80/510300　☑ dataset 旧测　☑ allowlist　☑ caps 接线　☑ deferred market_state　☑ toml 双轨 |
| 备注 | A–F 全勾。Gate **accepted** `pass_with_residuals` @ 2026-07-22T11:54；Close 完成。下一：WT-R4-A3 intake（不自动 Init）。 |

---

## 主对话 Gate 就绪摘要

```
verdict: pass_with_residuals
range: adede39..HEAD (c80b7ae, d21420f)
blocking_p0: none
focused_suite: 40 passed
residuals_handoff:
  - soft80 (61<80) + 510300 empty parts
  - dataset integration 10 failed (default→tushare)
  - no-direct ALLOWED_PREFIXES includes ashare_infra.data
  - caps config not wired to fetch
  - deferred: build_sequence_dataset_market_state.py
  - data_source.toml still akshare default
next_after_close: WT-R4-A3 intake (not auto)
```
