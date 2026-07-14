---
title: "MS-R3-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-R3-001"
updated: "2026-07-14T11:30:00+08:00"
updated_by: "cursor-agent-with-programmer-final-confirmation"
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
---

# MS-R3-001 Pre-Milestone Intake Review

## Intake Status

```yaml
intake_status: ready
programmer_confirmed: true
ready_for_init_milestone: true
confirmation_required: false
intake_skipped: false
skip_reason: null
accepted_risk: []
residual_risk_accepted: true
accepted_residual_risk:
  - P3_aggressive_defaults_mitigated_by_inventory_approval_gate
  - exact_inventory_item_counts_unknown_until_A1
continuation_required: false
next_question_blocks_ready: false
decisions_locked: [D1=B, D2=T2, D3=P3, D4=confirmed]
awaiting: init_milestone_instruction
```

## Request Summary

```yaml
request_summary: >
  Pipeline 中 planned 的 MS-R3-001「旧文件深度清理」。Programmer 已完成 intake
  并最终确认 brief（B+T2+P3）。intake_status=ready；等待显式 Init 指令后才可
  由 init-milestone-skill 写入/激活；确认前与 Init 前均不执行删除。
```

## Observed Facts

- Backlog 登记：`.servo/repo/milestone-backlog.md` — `MS-R3-001` status=`planned`，purpose=「删除 docs/archive/ 中已过期的历史文档、旧实验 TOML、旧脚本、旧 checkpoint，瘦身 Repo」；depends_on=`MS-R2-001`；note=「待 pre-milestone intake」。
- 依赖已满足：`MS-R2-001` completed/accepted（history + control-state final_acceptance）。
- 当前控制面 idle：`active_milestone: none`；`develop @ 7d5a22e`（含刚提交的控制面对齐）。
- `docs/archive/` 现存约 76K、9 个 md（含 README + 若干 202603 旧基线/计划文档）。
- 一级旧目录 `data/ configs/ models/ logs/ output/ experiments/` 已不存在（R2 已迁/清）。
- `inputs/data/cache/akshare*` 合计很小（约百 K 级）；TuShare 缓存合计约 ~24M。
- `workspace/checkpoints/` 约 20M，含 `best_mtl.pt` / `latest_mtl.pt`（2026-03）与 `rolling_dim19/`。
- `scripts/` 约 37 个入口；含大量历史 rolling/ablation/one-off 脚本。
- `docs/research/` 仍有一批 202603 研究计划/PDF/中文笔记（非 archive）。
- MS-R2 residual：pytest **395/397**，2 fail 归因「旧数据集路径」，明确留给后续 R3/R4。
- MS-R4 intake draft 已存在且声明需先完成 R2+R3；R4 不在本轮范围。
- Programmer 本轮表态：「MS-R3-001 的任务内容应该在我了解之后再准备开始」——禁止越过理解/确认直接 Init。
- Programmer 确认 D1：**清理模式 = B 治理清理**（2026-07-14）。
- Programmer 确认 D2：**pytest 债务 = T2 定性后分流**（2026-07-14）。
- Programmer 确认 D3：**默认分类 = P3 偏瘦身**（2026-07-14）— checkpoints 默认建议删；research 过时材料默认建议删；无引用 scripts 默认建议删；**真正删除仍须清单批准**。
- Programmer **最终确认 brief（D4）**（2026-07-14T11:30+08:00）：同意 B+T2+P3 scope / non-goals / acceptance / candidate worktracks；`ready_for_init_milestone=true`。仍禁止在未收到 Init 指令时创建/激活 milestone 或执行删除。

## Inferred Assumptions

- R3 的主价值是「治理型清理 + 路径/测试债务收口」，在 P3 下删除候选面会明显大于仅清 `docs/archive`。
- P3 提高误删研究资产的风险；模式 B 的「清单批准」是主要缓解手段，不可跳过。
- 被现行入口 / `src/` 引用的路径即使在 P3 下也应标「保留」或「待定」，不得进静默删除。

## Unknowns

- ~~D1/D2/D3/D4~~ → 已确认
- A1 inventory 实际条目数量与引用冲突细节（执行期才可知；已接受为 residual risk）

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: D1
    status: answered
    answer: B — 治理清理（inventory-first + 分批审批删除）
    answered_at: 2026-07-14T11:15:00+08:00
    blocks_ready: false
  - id: D2
    status: answered
    answer: T2 — 定性后分流
    answered_at: 2026-07-14T11:20:00+08:00
    blocks_ready: false
  - id: D3
    status: answered
    answer: P3 — 偏瘦身默认分类（仍经清单批）
    answered_at: 2026-07-14T11:25:00+08:00
    blocks_ready: false
  - id: D4
    status: answered
    answer: 确认 brief — ready_for_init_milestone
    answered_at: 2026-07-14T11:30:00+08:00
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: R1
    kind: other
    severity: high
    description: 破坏性清理（删文件/checkpoint）；误删不可轻易恢复
  - id: R2
    kind: scope_creep
    severity: medium
    description: backlog 文案偏窄（archive），实际债务面更广（scripts/tests/checkpoints/research）
  - id: R3
    kind: data
    severity: medium
    description: 若把数据湖重建或大规模 cache 重建塞进 R3，会与 MS-R4 冲突
  - id: R5
    kind: other
    severity: high
    description: D3=P3 偏瘦身 — research/checkpoints 默认进建议删；必须依赖清单审批，禁止把「建议删」当成已批准```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  entry_verdict: clear
  milestone_blocking_decision: allow_create_activate
  complexity_signals:
    - destructive_cleanup
    - residual_test_debt_from_prior_milestone
    - depends_on_completed_restructure_milestone
  scanner_evidence_ref: "local du/ls probe 2026-07-14; milestone-history MS-R2 residual note; programmer D1-D4 confirmation"
  clearance_note: >
    block_init_until_cleanup_mode_confirmed 已解除：D1=B、D2=T2、D3=P3、D4=brief confirmed
    （2026-07-14）。破坏性删除仍须 inventory 清单分批审批；high_risk_command_mode=normal。
  operator_safety_policy:
    destructive_cleanup: require_programmer_approval_per_delete_batch
    protected_paths:
      - src/
      - .servo/goal-charter.md
      - inputs/pools/
      - inputs/configs/profiles/
    high_risk_command_mode: normal
  dialog_review_questions: []
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: not_needed
    reason: repo 结构与 R2 文档已足够支撑 cleanup；programmer 已最终确认 brief
```

## Open Questions (continuous intake)

### answered_questions

- **Q1 / D1** = **B** 治理清理
- **Q2 / D2** = **T2** pytest 定性后分流
- **Q3 / D3** = **P3** 偏瘦身默认分类（仍须清单批才删）
- **Q4 / D4** = **确认** brief（2026-07-14T11:30+08:00）

### next_required_question

```yaml
answered_questions: [D1=B, D2=T2, D3=P3, D4=confirmed]
unresolved_questions: []
continuation_state:
  continuation_required: false
  checkpoint: MS-R3-001-intake-2026-07-14T11:30:00+08:00
continuation_reason: null
next_required_question: null
next_question_blocks_ready: false
```

## Recommended Answers

1. D1=B、D2=T2、D3=P3、D4=confirmed — **全部锁定**
2. 下一步：等你下达「初始化 / Init MS-R3-001」后再跑 `init-milestone-skill`
3. 硬边界：`src/`、pools/profiles、goal-charter、TuShare 主缓存默认不删

## Scope Boundary（已确认）

**In scope**
- Inventory：删除 / 保留 / 待定（含引用审计 + 2-fail 定性）
- 默认分类 **P3**：未引用旧 checkpoint → 建议删；过时 `docs/research` / archive → 建议删；无引用 one-off scripts → 建议删；AkShare 探针缓存 → 建议删
- 经批准后分批删除 + 入口文档/gitignore 同步
- T2：可路径修复/死测退役的进 R3；数据湖依赖 defer R4

**Out of scope / Non-goals**
- TuShare 数据湖 / 为修测重建大数据（R4）
- 模型重训 / 信号晋升 / `src` 业务重构
- 未批准清单上的删除；把「建议删」直接当已删
- 未收到 Init 指令时自动 Init / 自动执行删除

## Acceptance Signals（已确认）

- 批准过的 inventory + 执行记录完整
- 批准删除项已移除，无意外引用断裂
- 不引入新的 pytest 失败
- 2-fail：定性记录齐全；R3 可修项已处置或 R4 defer 已书面交接
- 不触碰 R4 数据拉取

## Suggested Milestone Brief（已确认 — 可交 init-milestone）

```yaml
suggested_milestone_brief:
  milestone_id: MS-R3-001
  title: 旧文件深度清理
  purpose: >
    在 R2 三区布局上，以治理模式（inventory→批准→分批删除）按 P3 偏瘦身默认分类
    清除过期文档/脚本/checkpoint 等治理债务；对 R2 遗留 2 fail 按 T2 分流；为 R4 数据湖腾出干净仓库面。
  milestone_kind: goal-driven
  status_identity: programmer_confirmed_ready_for_init
  cleanup_mode: B_governance_inventory_first
  pytest_debt_policy: T2_triage_then_split
  retention_defaults: P3_aggressive_suggest_delete
  depends_on_milestones: [MS-R2-001]
  candidate_worktracks:
    - WT-R3-A1: inventory + 引用审计 + 2-fail 定性（只读；产出清单）
    - WT-R3-A2: 按批准清单分批删除/退役（破坏性，需批）
    - WT-R3-A3: 文档/入口一致性 + R3 侧可修测处置 + R4 defer 交接
  protected_paths:
    - src/
    - .servo/goal-charter.md
    - inputs/pools/
    - inputs/configs/profiles/
    - inputs/data/cache/tushare*
  high_risk_command_mode: normal
```

## Confirmation State

```yaml
programmer_confirmed: true
ready_for_init_milestone: true
intake_status: ready
intake_skipped: false
residual_risk_accepted: true
accepted_residual_risk:
  - P3_aggressive_defaults_mitigated_by_inventory_approval_gate
  - exact_inventory_item_counts_unknown_until_A1
effective_review_pass: true
milestone_review_gate_handoff:
  review_status: effective_pass
  latest_review_checkpoint: MS-R3-001-intake-2026-07-14T11:30:00+08:00
  milestone_review_count: 1
  effective_review_pass: true
  review_invalidated_by: null
```

## Handoff To Init Milestone

```yaml
handoff_to_init_milestone: true
handoff_ref: .servo/repo/MS-R3-001-pre-milestone-intake-review.md
blocked_reason: null
next_safe_actions:
  - 等待 programmer 明确指令「初始化 MS-R3-001」/ Init
  - 届时由 init-milestone-skill 写入 milestone artifact + backlog（planned→可激活规则按 harness）
  - 在此之前禁止删除、禁止 Worktrack Init
```

## Skip Record

```yaml
intake_skipped: false
```
