---
title: "MS-R4-001 / WT-R4-A0 Intake Review"
artifact_type: "worktrack-intake-review"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A0"
updated: "2026-07-15T09:05:00+08:00"
owner: "OceanEyeFF"
updated_by: "cursor-worktrack-intake-WT-R4-A0"
---

# MS-R4-001 / WT-R4-A0 Intake Review

## Control Signal

```yaml
selected_worktrack_id: WT-R4-A0
selected_worktrack_title: 新策略准则草案 + ≤100 池导出（registry）+ 与旧池差异说明
target_milestone_id: MS-R4-001
derived_from_milestone: true
active_milestone_ref: .servo/milestone/MS-R4-001.md
active_milestone_branch: milestone/MS-R4-001-tushare-datalake
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
blocker: none
decisions_locked:
  - A0_Q1=T1_research_liquidity_quality
  - soft_target_size=80
  - hard_cap=100
  - strategy_folder_hint: research_liquidity_quality
milestone_review_gate_ready: true
latest_review_status: effective_pass
milestone_review_count: 1
latest_review_checkpoint: MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00
effective_review_pass: true
review_invalidated_by: none
continuation_required: false
continuation_round: 2
next_required_question: null
next_route: Init completed; Dispatch R4-A0-T1 on request
init_completed_at: 2026-07-15T09:12:00+08:00
contract_ref: .servo/worktrack/WT-R4-A0-contract.md
plan_task_queue_ref: .servo/worktrack/WT-R4-A0-plan-task-queue.md
```

## Request Summary

```yaml
request_summary: >
  WT-R4-A0 已 Init（A0_Q1=T1 research_liquidity_quality）。contract + plan queue 已播种；
  selected_next_action=R4-A0-T1（strategy brief）。执行尚未开始。
```

## Repo Fundamentals

```yaml
repo_fundamentals: pass
active_milestone: MS-R4-001
milestone_status: active
baseline_branch: develop
milestone_branch: milestone/MS-R4-001-tushare-datalake
current_branch: milestone/MS-R4-001-tushare-datalake
checkpoint_ref: aa2b14c1cd109e67e5eb48314572e03da1a4e750
decisions_locked_from_milestone:
  - D1=B_direction
  - D1b=P1
  - D1c=C2_cap100
  - D2=L2
  - D3=R1
  - CG2=M1_normal
  - D4=lake_qa_closeout
  - D5=tushare_primary_akshare_backup
goal_alignment: >
  A0 产出可版本化新池（准则 + strategy + registry ≤100 + 与旧池差异），
  是后续湖灌装（A1–A4）的 universe 前置；不是训练/全市场拉数。
prohibited_actions:
  - 全市场 / full-campaign TuShare 拉数
  - 未批准 live 配额战役（L2 允许有限补洞，但 A0 默认 cache-first；live 需显式批准）
  - 把旧 low_manipulation 14 或未审计 ~66 cache 当作最终研究 universe
  - 删除 AkShare 代码
  - 训练矩阵 / 模型重训 / alpha_score 晋升
  - commit/push、破坏性清理、依赖升级（仍审批门控）
  - 越过 A0 去做 A1–A4 主体（合同落地、大规模补洞、derived QA 终稿）
```

## Snapshot Freshness

```yaml
snapshot_freshness: pass_with_caveat
evidence_refs:
  - .servo/control-state.md
  - .servo/milestone/MS-R4-001.md
  - .servo/repo/milestone-backlog.md
  - .servo/repo/MS-R4-001-pre-milestone-intake-review.md
  - .servo/worktrack/WT-T1-A4-r4-handoff.md
  - git HEAD milestone/MS-R4-001-tushare-datalake @ aa2b14c
caveat: >
  MS-R4 Init 写回（control-state / backlog / milestone artifact / intake）仍在工作区未
  commit；不影响 A0 intake 判定。HEAD 相对 develop@aa2b14c 未分叉代码变更。
refresh_required: false
```

## Milestone Purpose Alignment

```yaml
milestone_purpose_alignment: pass
worktrack_role: >
  兑现 P1+C2：新策略族 + ≤100 可版本化池 + 旧池对照；解锁 A1 合同/配额上限建议
  与后续 cache-first/limited-live 灌湖的 universe 锚点。
covers_completion_signals:
  - CS1（可版本化新池 artifact 已注册且 ≤100）的主体
  - CS6（验收绑定批准池版本）的池产物与差异说明部分
does_not_cover:
  - CS2 默认 TuShare 路径测试终态（A2）
  - CS3 cache/derived 可复现 load（A2–A4）
  - CS4 质量审计报告终稿（A4）
  - 日/RPM 数值上限批准（A1）
  - limited-live 增量补洞战役（A3）
```

## Historical Conflict Risk

```yaml
historical_conflict_risk: medium
prior_context:
  - low_manipulation：14 只，threshold=60，total_universe≈64；proxy 评分非真实控盘概率
  - inputs/data/cache/tushare_* ≈66 symbols；derived 几乎空
  - stock_pool 已有 low_manipulation 实现；momentum/value 仅为占位（无 strategy.py）
  - A0 若无明确命题，易滑成开放式「更优选股」研究（milestone non-goal）
conflict_controls:
  - 硬上限 ≤100；旧池仅对照基线
  - A0 默认 cache-first 打分/导出；禁止 silent full-campaign
  - 准则必须可审计写入文档 + config；权重在草案批准前不得伪装为长期 truth
  - registry 导出走既有 stock_pool 合同（三件套），禁止手改 configs 冒充注册
```

## Observed Facts (A0-relevant)

- Active milestone MS-R4-001；branch `milestone/MS-R4-001-tushare-datalake`。
- A0 在 worktrack_list 首位；status planned。
- `src/ashare_lab/stock_pool/low_manipulation/` 含 strategy + config；`momentum/`、`value/` 仅占位。
- `inputs/pools/low_manipulation/symbols.csv` = 14；cache qfq 目录 ≈66。
- Milestone residual：策略维度/权重下沉 A0；日/RPM 下沉 A1。

## Inferred Assumptions

- A0 应以「可审计准则 + registry 池」收口，而非最优 alpha 研究。
- 打分/筛选尽量基于现有 cache；缺数据 symbol 记缺口，留给 A3 limited-live。
- 新策略应用新 folder 名（C2），不覆写 `low_manipulation` 目录。

## Unknowns Blocking Ready

- ~~A0_Q1~~ → T1 research_liquidity_quality；软目标 ≤80；硬上限 100
- 具体维度权重数值 — 属 A0 草案产出（Init 后起草再批）；已接受为 residual
- 缺 cache 的 symbol 缺口列表 — 执行中产出，留给 A3 limited-live

## Open Question (one at a time)

```yaml
open_questions: []
answered_questions:
  - id: A0_Q1
    answer: "T1 — research_liquidity_quality；软目标 ≤80；硬上限 100；旧池仅对照"
    answered_at: 2026-07-15T09:05:00+08:00
    source: programmer
unresolved_questions: []
```

## Continuous Intake State

```yaml
continuation_state:
  continuation_required: false
  continuation_round: 2
  continuation_reason: "A0_Q1=T1 confirmed; intake ready_for_worktrack_init"
  answered_questions:
    - id: A0_Q1
      answer_summary: "T1 — research_liquidity_quality；软目标 ≤80；硬上限 100"
      answered_at: 2026-07-15T09:05:00+08:00
      source: programmer
  unresolved_questions: []
  next_required_question: null
  next_question_blocks_ready: false
  residual_risk_accepted: true
  accepted_residual_risk:
    - dimension_weights_drafted_in_A0_then_approved
    - cache_gaps_listed_for_A3_limited_live
```

## Worktrack Adjustment Recommendations

```yaml
worktrack_adjustment_recommendations: none
add_remove_worktrack_recommendations: none
reason: >
  A0 已在 confirmed milestone worktrack_list 首位，与 P1/C2 一致；无需增删重排。
  命题确认后保持 A0 范围，不把 A1–A4 并入。
```

## Confirmed A0 Scope (after A0_Q1=T1)

```yaml
strategy_thesis: research_liquidity_quality
strategy_folder: research_liquidity_quality
soft_target_size: 80
hard_cap: 100
old_pool_role: contrast_baseline_only
in_scope:
  - 可审计准则文档（维度定义、硬过滤、软目标 ≤80、硬上限 100、非目标声明）
  - 新 strategy folder `research_liquidity_quality` + StockPoolStrategy 实现 + config.toml
  - cache-first 选股/打分（可用现有 tushare_* cache；缺口列表化，不 silent live）
  - registry 导出三件套，symbols_count ≤100（目标 ≤80）
  - 与 custom_low_manipulation_v1 / inputs/pools/low_manipulation 的差异报告
out_of_scope:
  - A1 日/RPM 数值最终批准与湖合同终稿
  - A2–A4 加载路径重构、limited-live 战役、derived QA 终稿
  - 训练/回测/信号晋升
  - 全市场拉数
node_type: feature
suggested_deliverables:
  - .servo/worktrack/WT-R4-A0-strategy-brief.md（或 docs 下约定路径）
  - src/ashare_lab/stock_pool/<new_strategy>/
  - configs/stock_pools/<pool_id>.{toml,csv,json} via registry API
  - diff report vs old pool
```

## Verdict

```yaml
intake_review_verdict: ready_for_worktrack_init
ready_for_worktrack_init: true
blockers: none
decisions_locked:
  - A0_Q1=T1_research_liquidity_quality
  - soft_target_size=80
  - hard_cap=100
programmer_trigger: "Init WT-R4-A0 — received 2026-07-15T09:12:00+08:00"
init_status: completed
```

## Handoff

- Init 已完成：contract + plan queue 已写入；复用 milestone 分支（one-development-branch-per-milestone）。
- 下一步：Dispatch `R4-A0-T1`（strategy brief）。执行尚未开始。
