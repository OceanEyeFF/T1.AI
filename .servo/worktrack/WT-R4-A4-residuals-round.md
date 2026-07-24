---
title: "WT-R4-A4 Residuals Round"
artifact_type: "worktrack-residuals-round"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A4"
updated: "2026-07-24T14:50:00+08:00"
owner: "OceanEyeFF"
status: "pending_programmer_confirmation"
tip: "15c078d"
---

# WT-R4-A4 Residuals Round（Gate 前强制）

> **硬门控：** T5 之后、**R4-A4-GATE 之前**必须完成本轮。跳过 → **Gate 无效**。  
> 状态：`pending_programmer_confirmation`。  
> MS-level Residual Confirmation（AC6）是**另一次**终验门控，不在本文件确认。

## Control Signal

```yaml
residuals_round_required: true
residuals_round_status: pending_programmer_confirmation
programmer_confirmed: false
blocks_gate_until: residuals_round_status == confirmed
related_ms_residual_confirmation: .servo/repo/MS-R4-001-residual-confirmation.md
ms_status: pending_programmer_confirmation  # separate; do NOT mark confirmed here
```

## Proposed Dispositions（请确认）

每条默认 **proposed accept**（对齐既有 A3 locks + T1–T3 doc-only + AO-O4 defer）。可选：accept / fix / waive+理由。

| ID | Summary | Options | Proposed |
|----|---------|---------|----------|
| soft80_61lt80 | 池 61 < soft_target 80；hard_cap OK | accept / fix(扩池) / waive | **proposed accept** |
| index_510300_qfq_only | `510300.SH` qfq-only；basic/mf N/A | accept / fix / waive | **proposed accept** |
| trial_exclude_601989 | trial 60；registry 仍 61 | accept / fix / waive | **proposed accept** |
| A4_F1 | rebuild 不 prune 旧 year=* | accept / fix(prune) / waive | **proposed accept**（doc-only） |
| A4_F2 | momentum/technical 行数可不等 | accept / fix(强制对齐) / waive | **proposed accept**（doc-only） |
| A4_F4 | load filesystem-only；refresh 不重建 derived | accept / fix(级联) / waive | **proposed accept**（doc-only） |
| AO-O4_deferred | AST 合同补强 optional | accept(defer) / fix(做 AST) / waive | **proposed accept**（defer） |

### Optional footnotes（非阻塞；可点名）

| ID | Note | Proposed |
|----|------|----------|
| A4_F3 | private `_read_cached_partitions` 复用 | footnote OK |
| A4_F5 | infra `load_derived` → lab `symbol_to_ts_code` | footnote OK |

## Programmer Confirmation

请回复确认话术，例如：

> 「确认 WT-R4-A4 Residuals：全部 proposed accept」

或逐条点名 accept / fix / waive。

```yaml
programmer_confirmed: false
confirmation_phrase: N/A
confirmed_at: N/A
residuals_round_status: pending_programmer_confirmation
```

## Separation of Concerns

| Round | Artifact | When |
|-------|----------|------|
| **WT Residuals**（本文件） | Gate 前 | 现在 |
| **MS Residual Confirmation** | `.servo/repo/MS-R4-001-residual-confirmation.md` | A4 Close 后、MS 终验前（AC6） |

## Refs

- QA: `.servo/worktrack/WT-R4-A4-qa-report.md`
- Consistency: `.servo/worktrack/WT-R4-A4-consistency-matrix.md`
- T1–T3 review: `.servo/worktrack/WT-R4-A4-t1-t3-review.md`
- Gate draft: `.servo/worktrack/WT-R4-A4-gate-evidence.md`
