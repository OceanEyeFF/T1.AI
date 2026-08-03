---
title: "Milestone Residual Confirmation: {{milestone_id}}"
artifact_type: "milestone-residual-confirmation"
milestone_id: "{{milestone_id}}"
status: "pending_programmer_confirmation"  # pending_programmer_confirmation | confirmed | rejected | superseded
updated: "{{updated}}"
owner: "OceanEyeFF"
gate: "milestone_final_acceptance"
---

# Milestone Residual Confirmation — {{milestone_id}}

> **硬门控：** Milestone **final acceptance**（含合入 `baseline_branch` / 标记 milestone completed）之前，必须与使用者完成一轮 Residual 确认。  
> 未经本确认，Harness **不得**将 `milestone_acceptance_verdict` 记为 `achieved`，也不得 blind-merge develop。

## Control Signal

```yaml
residual_confirmation_required: true
residual_confirmation_status: pending_programmer_confirmation
programmer_confirmed: false
confirmed_at: N/A
blocks_final_acceptance_until: residual_confirmation_status == confirmed
```

## Purpose（必须同时满足）

1. **记录完整：** 本表覆盖本 Milestone 全部 accepted / deferred residuals（含各 WT Gate 与 T1–Tn review），无遗漏、无口头约定。
2. **使用者清楚：** 每一条 residual 的含义、影响面、当前处置（文档化 / 豁免 / 延后）可读。
3. **接受条件 + 再阻塞条件：** 使用者明确「在什么条件下接受」；以及「遇到什么需求时该 residual 重新变为阻塞、必须再开 worktrack / 修代码」。

## Residual Register

| ID | Source | Summary | Acceptance condition (accepted when…) | Re-blocks when… | Disposition |
|----|--------|---------|----------------------------------------|-----------------|-------------|
| {{id}} | {{wt/gate}} | {{one_line}} | {{condition}} | {{reopen_trigger}} | accepted_residual / deferred / doc_only |

## Confirmation Checklist（使用者逐项确认）

- [ ] **R1 — Completeness:** 上表已包含本 MS 全部已知 residuals；无遗漏项需补充。
- [ ] **R2 — Understanding:** 使用者已阅读并理解每条 residual 的含义与影响。
- [ ] **R3 — Acceptance conditions:** 使用者同意「Acceptance condition」列所述接受边界。
- [ ] **R4 — Re-block triggers:** 使用者同意「Re-blocks when…」列；命中时不得 silently ignore，须新开 WT 或显式改判。
- [ ] **R5 — No silent expand:** 本确认不授权 full-campaign / 训 / 范围外工作。

## Programmer Confirmation

```yaml
# 仅当使用者显式确认后填写
programmer_confirmed: false
confirmation_phrase: N/A   # e.g. 「确认 MS-R4-001 residuals」
confirmed_at: N/A
confirmed_by: N/A
residual_confirmation_status: pending_programmer_confirmation
```

## Non-Goals

- 本文件 **不是** Worktrack Gate 替代品（WT 仍可 `pass_with_residuals`）。
- 本文件 **不是** 自动把 residual 改成 bugfix；再阻塞条件触发后需新的 Init/Dispatch。
