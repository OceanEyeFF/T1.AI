---
title: "Milestone Residual Confirmation: MS-R4-001"
artifact_type: "milestone-residual-confirmation"
milestone_id: "MS-R4-001"
status: "pending_programmer_confirmation"
updated: "2026-08-03T14:53:00+08:00"
owner: "OceanEyeFF"
gate: "milestone_final_acceptance"
checkpoint_note: "A4 Gate/Close seeded final residual set; WT residuals round confirmed 2026-07-28 (WT-level only); status still pending_programmer_confirmation for MS final acceptance"
---

# Milestone Residual Confirmation — MS-R4-001

> **硬门控：** MS-R4-001 **final acceptance**（A4_Q7：WT close ≠ MS 终验）前，必须与使用者完成本轮 Residual 确认。  
> 状态：`pending_programmer_confirmation`（**未确认**）。  
> A4 Gate/Close（2026-07-28，`pass_with_residuals`）已播种最终 residual 集合；WT Residuals round 已 confirmed（WT-level only）。MS 终验前再对表一轮。

## Control Signal

```yaml
residual_confirmation_required: true
residual_confirmation_status: pending_programmer_confirmation
programmer_confirmed: false
confirmed_at: N/A
blocks_final_acceptance_until: residual_confirmation_status == confirmed
related_wt_close_policy: A4_Q7_wt_close_only
wt_r4_a4_gate: pass_with_residuals  # 2026-07-28
wt_r4_a4_residuals_round: confirmed  # WT-level only; 2026-07-28
```

## Purpose（必须同时满足）

1. **记录完整：** 下表覆盖 MS-R4-001 全部已登记 residuals。
2. **使用者清楚：** 每条可读、可追溯到 WT Gate / review。
3. **接受条件 + 再阻塞条件：** 明确接受边界；命中 reopen 触发器时重新阻塞。

## Residual Register（当前已知；终验前冻结）

| ID | Source | Summary | Acceptance condition | Re-blocks when… | Disposition |
|----|--------|---------|----------------------|-----------------|-------------|
| soft80_61lt80 | WT-R4-A3-T4/Gate | 池 61 < soft_target 80；hard_cap 100 已满足 | 接受「实验池不必凑满 80」；不默认可扩池 | 需求变为「必须 ≥80 / 扩池 live / 重选 registry」 | accepted_residual |
| index_510300_qfq_only | WT-R4-A3-T3/T4 | `510300.SH` 仅要求 qfq；basic/moneyflow 不适用 ETF | 接受 qfq-only 锚；basic/mf 不进硬 AC | 需求变为「指数/ETF 必须具备股票同构 basic/mf」 | accepted_residual |
| trial_exclude_601989 | WT-R4-A3-T4 | `601989` 留在 registry，默认 trial 子集排除（上游耗尽） | 接受 trial 默认 60；registry 仍计 61 | 需求变为「trial/训练必须含 601989 且要新鲜 bars」 | accepted_residual |
| A4_F1_stale_year_no_prune | WT-R4-A4 T1–T3 review | derived 重建只覆盖同年 `part.parquet`，不 prune 旧 `year=*` | 接受增量覆盖语义；严格对齐需手动清目录 | 需求变为「rebuild 必须与 cache 年份集合严格一致 / 自动 prune」 | fixed_post_a4 |
| A4_F2_family_row_mismatch | WT-R4-A4 T1–T3 review | momentum/technical warm-up 后行数可不等 | 接受按 family 读 + 显式 date join | 需求变为「两 family 必须等长日历 / 强制内连接」 | doc_only |
| A4_F4_refresh_not_rebuild | WT-R4-A4 T1–T3 review | `load_derived*` 只读盘；`DataLake.refresh` 不重建 derived | 接受 load≠build；刷新走 builder | 需求变为「refresh=True 必须级联重建 derived」 | doc_only |
| AO-O_hygiene | A3→A4 AC / A4-T4 | AO-O1 allowlist + AO-O2 dataset_builder（+O3 doc）；AO-O4 deferred | T4 已完成；accept 以 T4 notes 为准 | 回归再破 allowlist / dataset 旧测再红；或要求强制做 AO-O4 AST | closed_in_A4_T4 |
| AO-O4_deferred | A4-T4/T5 QA / post-A4 | AO-O4-A static Import/ImportFrom full-tree scan **done** post-A4；dynamic getattr/importlib AST 仍 deferred | 接受 dynamic AST defer；不阻塞 MS residual 确认 | 需求变为「必须补 dynamic AST 合同」 | deferred |

### Optional footnotes（非阻塞，终验可点名）

| ID | Note |
|----|------|
| A4_F3 | private `_read_cached_partitions` 复用 |
| A4_F5 | infra `load_derived` → lab `symbol_to_ts_code` |

## Confirmation Checklist（终验时由使用者勾选）

- [ ] **R1 — Completeness:** 上表已是 MS-R4-001 完整 residual 集合（含 A4 Close / QA 最终增补）。
- [ ] **R2 — Understanding:** 已理解每条含义与影响。
- [ ] **R3 — Acceptance conditions:** 同意各「Acceptance condition」。
- [ ] **R4 — Re-block triggers:** 同意各「Re-blocks when…」；命中则新开 WT / 改判，不得 silent ignore。
- [ ] **R5 — No silent expand:** 本确认不授权 full-campaign / 训 / Phase4 / EXEC-002 / blind merge。

## Programmer Confirmation

```yaml
programmer_confirmed: false
confirmation_phrase: N/A
# 期望话术示例：「确认 MS-R4-001 residuals」或逐条点名接受
confirmed_at: N/A
confirmed_by: N/A
residual_confirmation_status: pending_programmer_confirmation
```

## Refs

- T5 QA: `.servo/worktrack/WT-R4-A4-qa-report.md`
- WT Residuals round: `.servo/worktrack/WT-R4-A4-residuals-round.md`（confirmed 2026-07-28，WT-level）
- Gate: `.servo/worktrack/WT-R4-A4-gate-evidence.md`（accepted pass_with_residuals）
- Closeout: `.servo/worktrack/WT-R4-A4-closeout.md`
- T1–T3 review: `.servo/worktrack/WT-R4-A4-t1-t3-review.md`
- A3 closeout: `.servo/worktrack/WT-R4-A3-closeout.md`
- Template: `.servo/template/milestone-residual-confirmation.template.md`
