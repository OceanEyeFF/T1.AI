---
title: "WT-R4-A3 T3 Notes"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
task_id: "R4-A3-T3"
updated: "2026-07-23T09:35:00+08:00"
owner: "OceanEyeFF"
status: "live_done_pass_with_residuals"
---

# WT-R4-A3 T3 Notes

> Add-on ref: `.servo/worktrack/WT-R4-A3-t3-addon.md`

## AO-B / AO-R1（零 live — done）

| ID | 状态 |
|----|------|
| AO-B1～B4 | done |
| AO-R1 | done |

## Live 批次批准

| 项 | 内容 |
|----|------|
| 批准人 | OceanEyeFF（主对话） |
| 批准时间 | 2026-07-23T09:29:15+08:00 |
| batch_approve_id | `M1-normal-2026-07-23-510300+staleness7` |
| 批准范围 | ☑ 510300 + staleness-7 |
| M1/normal | ☑ |
| token | env / `.env`（未入仓） |

## Live 执行

| 批次 | Manifest | 结果 |
|------|----------|------|
| 510300 初跑（stock APIs） | `workspace/r4_a3_t3/manifest-510300-live.json` | jobs completed 但 **空帧**（`pro.daily` 对 ETF 为空） |
| 510300 fund 重试 | `workspace/r4_a3_t3/manifest-510300-fund-retry-live.json` | **completed**；`fund_daily` → `tushare_qfq` |
| staleness-7 | `workspace/r4_a3_t3/manifest-staleness-live.json` | **21/21 done** |

Limiter after（初跑）: daily8 + adj8 + basic8 + mf8；fund 重试另计 `fund_daily`.

### 调用链

```
run_batch → make_r4_refresh_executor → DataLake/load_or_fetch(refresh=True)
  → fetch_tushare_daily_bars
      → pro.daily；若空 → pro.fund_daily（ETF）
```

## 验收核对（live 后）

| 期望 | 结果 |
|------|------|
| 510300 `tushare_qfq` 有 parts | **PASS** — 4 parts / 859 rows / 2023-01-03→2026-07-22 |
| 510300 basic/moneyflow | **残差** — ETF 不在 stock `daily_basic`/`moneyflow`（仍空） |
| staleness 6/7 前进到近端 | **PASS** — 6 标的 → 2026-07-22 |
| 601989.SH 前进 | **残差** — TuShare 最晚仍 2025-08-12（`stock_basic` 空；上游耗尽） |

**Verdict:** `pass_with_residuals`  
证据: `workspace/r4_a3_t3/live-verify-report.json`

## 残差交接

- 510300 basic/mf：需基金专用接口或显式豁免三命名空间要求（A1 G2 仅强制 qfq）
- 601989.SH：上游无更新，非 runner bug；可 T4/A4 从池策略侧处理
- soft80 → T4
- AO-O* hygiene → A3_Q3 defer / A4

## 代码增量（live 诊断后）

- `fetch_tushare_daily_bars`：stock `daily` 空时回退 `fund_daily`
- 单测：`tests/unit/infra/test_tushare_fund_daily_fallback.py`
