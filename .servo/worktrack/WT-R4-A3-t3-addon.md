---
title: "WT-R4-A3 T3 Add-on Work Package"
artifact_type: "worktrack-task-addon"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
task_id: "R4-A3-T3"
updated: "2026-07-23T09:30:00+08:00"
owner: "OceanEyeFF"
status: "live_done_pass_with_residuals"
live_pull: "completed_m1_normal_2026-07-23"
---

# WT-R4-A3 T3 Add-on Work Package

> **用途：** 在合同 T3（limited-live 补洞）之外，收口代码审查 P1/P2 与 A3 接线规划，供主对话调度引用。  
> **原则：** Add-on 分 **必修（Blocking live）** / **推荐（同 T3 完成）** / **可选尾巴（不挡 Gate）**。  
> **Init 锁定：** A3_Q1=P1_caps_then_510300_staleness · A3_Q2=keep_v1_until_reselect · A3_Q3=defer_hygiene

## Control Signal

```yaml
worktrack_id: WT-R4-A3
task_id: R4-A3-T3
addon_scope: beyond_contract_t3_core
blocking_live_until:
  - AO-B1
  - AO-B2
  - AO-B3
  - AO-B4
recommended_with_t3:
  - AO-R1
  - AO-R2
  - AO-R3
  - AO-R4
  - AO-R5
deferred_per_A3_Q3:
  - AO-O1
  - AO-O2
  - AO-O3
  - AO-O4
out_of_t3_addon:
  - soft80_expand_or_reselect  # → T4
  - build_sequence_dataset_market_state
  - backtest_sim_hard_cut_tushare
  - full_campaign
```

---

## A. 既定 T3 目标（合同内 — 非 Add-on）

| ID | 交付 | 验收 |
|----|------|------|
| T3-CORE-1 | `510300.SH` 三命名空间 有 parts（qfq / daily_basic / moneyflow，按 A1 inventory） | ✅ qfq 859 rows；basic/mf 残差（ETF） |
| T3-CORE-2 | 池 61 **staleness** 批准清单补洞（A1 inventory 候选） | ✅ 6/7→2026-07-22；601989 上游残差 |
| T3-CORE-3 | **M1/normal 显式批次批准** 后执行 live | ✅ `M1-normal-2026-07-23-510300+staleness7` |
| T3-CORE-4 | 经 `tushare_batch` + DataLake / `load_or_fetch(refresh=True)` 写 cache | ✅ 无脚本旁路直拉 |
| T3-CORE-5 | manifest 落盘（plan → dry_run → run → 可 resume） | ✅ `workspace/r4_a3_t3/*` |

---

## B. Add-on 必修（Blocking — T3 live 前必须完成）

| ID | 项 | 来源 | 做什么 | 完成信号 |
|----|-----|------|--------|----------|
| **AO-B1** | 频率墙 resume 语义 | 审查 P1 | 频率墙时 job **不要**永久 `failed`；改为 `pending` + `paused_freq_wall`，或 `resume_batch` 重置 `frequency_wall:` 失败项 | ✅ 单测：墙后 resume **重试同一 job** |
| **AO-B2** | Live 单一路径 | 审查 P2 + contract | T3 live **只经** `run_batch` executor；禁止脚本/临时路径直调 `fetch_tushare_*` 或旁路 `refresh=True` | ✅ `make_r4_refresh_executor` + T3 notes 调用链 |
| **AO-B3** | `estimated_calls` 对齐 | 审查 P2 | qfq 路径 job 设 `estimated_calls=2`（daily+adj_factor），或 job 粒度改为「一次 symbol 一次 composite fetch」；`can_afford` 与真实 acquire 一致 | ✅ dry_run 预算 = live 实际扣费（mock / R1） |
| **AO-B4** | `_retry_with_backoff` 与频率墙 | 审查 P2 | `load_or_fetch` 遇 2002/频率类错误：**不** tight-loop 3 次；识别 freq wall → 抛出/转 batch pause | ✅ 单测：2002 仅 1 次 attempt |

**Gate 建议：** 缺 AO-B1～B4 不开 live。

---

## C. Add-on 推荐（同 T3 完成，不扩 WT 叙事）

| ID | 项 | 做什么 | 完成信号 |
|----|-----|--------|----------|
| **AO-R1** | batch ↔ fetch 集成测 | mock `fetch_tushare_*` / DataLake：executor(job) → acquire 计数正确 | ✅ `test_r4_batch_fetch_integration` |
| **AO-R2** | Live fill 脚本/入口 | 薄 CLI 或 `scripts/`：`plan_batch` → `dry_run_batch` → 打印摘要 → `run_batch`（需 env token） | T3 notes 一条命令 |
| **AO-R3** | Manifest 与 inventory 绑定 | manifest `policy` 含 pool_id/version、batch_approve_id、staleness 列表来源 | 可追溯 A1 inventory |
| **AO-R4** | 小清理 | 删未用 `FrequencyWallPause` 或真正使用；`acquire` import 挪到 `tushare_source` 顶部 | lint/风格 |
| **AO-R5** | T3 notes 模板 | 记录：批准人/时间、manifest 路径、API 计数前后 snapshot、510300/staleness 前后 | 供 T5 Gate |

---

## D. Add-on 可选尾巴（A3_Q3 defer — 便宜才做）

| ID | 项 | 默认去向 | 若做 |
|----|-----|----------|------|
| **AO-O1** | tighten no-direct allowlist | A4 | 去掉/收窄 `ashare_infra.data` |
| **AO-O2** | dataset 旧测 10 fail | A4 | 修 monkeypatch/默认源 |
| **AO-O3** | `data_source.toml` 双轨 | 文档 | 注释指向 `make_r4_datalake` |
| **AO-O4** | AST 合同测补强 | 低 | 有 AO-R1 即可 |

**不纳入 T3 Add-on：** `market_state` 脚本、backtest 硬切 tushare、soft80 扩池（→ **T4**）。

---

## E. 建议执行顺序

```
1. AO-B1（resume 语义）           ← 先修，否则 live 无意义
2. AO-B3 + AO-B4（预算/重试）      ← 与 B1 同文件域
3. AO-R1（集成测，零 live）        ← 证明链路
4. T3-CORE dry_run manifest        ← 510300 + staleness 清单
5. [程序员批准 live batch]         ← M1/normal 门控
6. T3-CORE live run + manifest 落盘
7. AO-R2 / R3 / R5 文档化
8. AO-R4 清理（可选）
```

---

## F. T3 完成定义（Core + Add-on）

**可标 T3 done 当且仅当：**

- [x] T3-CORE-1～5 全勾（qfq+staleness live；basic/mf 与 601989 为残差）
- [x] **AO-B1～B4** 全勾
- [x] **AO-R1** 全勾（团队可将 R1 升为必修）
- [x] live 有 manifest + limiter snapshot 证据
- [ ] 无 token 入仓；无 full-campaign

**仍归其他任务：**

- **T4：** soft80 进度或显式残差
- **T5：** 一致性矩阵 + Gate/Close
- **A4 / hygiene：** AO-O1～O4（除非 T3 尾巴顺手）

---

## G. 主对话调度摘要（可复制）

```
T3 = T3-CORE（510300 + staleness live，批准门控）
   + Add-on B1–B4（接线必修）
   + Add-on R1（集成测，推荐必修）
   + hygiene 仍 defer（A3_Q3 → AO-O*）
ref: .servo/worktrack/WT-R4-A3-t3-addon.md
```

---

## H. 相关引用

| 文档 | 路径 |
|------|------|
| A3 contract | `.servo/worktrack/WT-R4-A3-contract.md` |
| A3 plan | `.servo/worktrack/WT-R4-A3-plan-task-queue.md` |
| T1 notes | `.servo/worktrack/WT-R4-A3-t1-notes.md` |
| T2 notes | `.servo/worktrack/WT-R4-A3-t2-notes.md` |
| A2 closeout residuals | `.servo/worktrack/WT-R4-A2-closeout.md` |
| A1 inventory | `.servo/worktrack/WT-R4-A1-cache-inventory.md` |
| Caps config | `inputs/configs/tushare_rate_limits.toml` |
