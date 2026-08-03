---
title: "WT-R4-A4 Residuals Round"
artifact_type: "worktrack-residuals-round"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-28T15:17:00+08:00"
owner: "OceanEyeFF"
status: "confirmed"
tip: "60cbf22"
---

# WT-R4-A4 Residuals Round（Gate 前强制）

> **硬门控：** T5 之后、**R4-A4-GATE 之前**必须完成本轮。跳过 → **Gate 无效**。  
> 状态：`confirmed`（programmer 2026-07-28）。  
> MS-level Residual Confirmation（AC6）是**另一次**终验门控，不在本文件确认。

## Control Signal

```yaml
residuals_round_required: true
residuals_round_status: confirmed
programmer_confirmed: true
confirmation_phrase: 「确认 Residuals，再 Formal Gate」
confirmed_at: "2026-07-28T15:17:00+08:00"
tip: 60cbf22
blocks_gate_until: residuals_round_status == confirmed
related_ms_residual_confirmation: .servo/repo/MS-R4-001-residual-confirmation.md
ms_status: pending_programmer_confirmation  # separate; do NOT mark confirmed here
```

## Dispositions（全部 accepted）

每条由 programmer 话术「确认 Residuals，再 Formal Gate」确认为 **accepted**（对齐既有 A3 locks + T1–T3 doc-only + AO-O4 defer）。

| ID | Summary | Options | Disposition |
|----|---------|---------|-------------|
| soft80_61lt80 | 池 61 < soft_target 80；hard_cap OK | accept / fix(扩池) / waive | **accepted** |
| index_510300_qfq_only | `510300.SH` qfq-only；basic/mf N/A | accept / fix / waive | **accepted** |
| trial_exclude_601989 | trial 60；registry 仍 61 | accept / fix / waive | **accepted** |
| A4_F1 | rebuild 不 prune 旧 year=* | accept / fix(prune) / waive | **accepted**（doc-only） |
| A4_F2 | momentum/technical 行数可不等 | accept / fix(强制对齐) / waive | **accepted**（doc-only） |
| A4_F4 | load filesystem-only；refresh 不重建 derived | accept / fix(级联) / waive | **accepted**（doc-only） |
| AO-O4_deferred | AST 合同补强 optional | accept(defer) / fix(做 AST) / waive | **accepted**（defer） |

### Optional footnotes（非阻塞；可点名）

| ID | Note | Disposition |
|----|------|-------------|
| A4_F3 | private `_read_cached_partitions` 复用 | footnote OK |
| A4_F5 | infra `load_derived` → lab `symbol_to_ts_code` | footnote OK |

## Programmer Confirmation

```yaml
programmer_confirmed: true
confirmation_phrase: 「确认 Residuals，再 Formal Gate」
confirmed_at: "2026-07-28T15:17:00+08:00"
residuals_round_status: confirmed
disposition: all_proposed_accept → accepted
tip: 60cbf22
```

## Separation of Concerns

| Round | Artifact | When |
|-------|----------|------|
| **WT Residuals**（本文件） | Gate 前 | **confirmed** 2026-07-28 |
| **MS Residual Confirmation** | `.servo/repo/MS-R4-001-residual-confirmation.md` | A4 Close 后、MS 终验前（AC6）— **仍 pending** |

## Refs

- QA: `.servo/worktrack/WT-R4-A4-qa-report.md`
- Consistency: `.servo/worktrack/WT-R4-A4-consistency-matrix.md`
- T1–T3 review: `.servo/worktrack/WT-R4-A4-t1-t3-review.md`
- Gate: `.servo/worktrack/WT-R4-A4-gate-evidence.md`
