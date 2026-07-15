---
title: "MS-R4-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-R4-001"
proposed_title: "TuShare 数据湖构建"
updated: "2026-07-15T00:16:00+08:00"
updated_by: "cursor-pre-milestone-intake-continuous"
template_contract_ref: ".agents/skills/servo-pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md"
refresh_reason: "MS-T1-001 formal close; dependency satisfied; prior draft intake stale (blocked on MS-R2/MS-R3)"
continuation_round: 8
---

# MS-R4-001 Pre-Milestone Intake Review

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
  - new_strategy_dimension_weights_deferred_to_A0
  - daily_rpm_numeric_caps_deferred_to_A1_then_approve
continuation_required: false
next_question_blocks_ready: false
awaiting: none_init_completed
decisions_locked:
  - D1=B_direction_not_full_market_and_existing_pool_not_locked
  - D1b=P1_pool_recombination_as_R4_front_worktrack
  - D1c=C2_new_strategy_family_cap_100
  - D2=L2_limited_live_quota_bounded
  - D3=R1_audit_reuse_intersection
  - CG2=M1_normal
  - D4=default_lake_qa_closeout
  - D5=default_tushare_primary_akshare_backup
  - BRIEF=Y_confirmed
```

## Request Summary

```yaml
request_summary: >
  MS-R4-001 pre-milestone intake 已 ready：精选可重组；P1 前置新池；C2≤100；
  L2 limited-live；R1 审计复用；M1/normal；D4 lake+QA 收口；D5 TuShare 默认/
  AkShare 备用；brief 已确认。等待显式「初始化 MS-R4-001」后才可由
  init-milestone-skill 写入/激活。
```

## Observed Facts

- Control plane idle：`active_milestone: none`；`MS-R4-001` 为唯一 planned milestone（`.servo/repo/milestone-backlog.md`）。
- `depends_on_milestones: MS-T1-001` 已满足：MS-T1 formal close/accepted（merge `eed3e24`；formal-close writeback `aa2b14c` on `develop`）。
- T1→R4 handoff（`.servo/worktrack/WT-T1-A4-r4-handoff.md`）：R4 测试应落在 `tests/integration/sources|dataset` 与 `tests/contract/`；禁止回退扁平 `tests/test_*.py`；T1 未做全市场拉数/配额战役。
- 旧 intake（2026-06-23 draft）状态为 `planned_not_activated`，blocks 写的是 MS-R2/MS-R3 — **已过时**，本轮作废其阻断结论。
- 源码已有 TuShare adapter：`src/ashare_lab/data/tushare_source.py`（daily/qfq、daily_basic、moneyflow、adj_factor；token 自 `TUSHARE_TOKEN` 或参数）。
- AkShare adapter 仍存在：`src/ashare_lab/data/akshare_source.py`；NEXT_STEPS 记「TuShare（主）/ AkShare（备用）」。
- 现有 cache（`inputs/data/cache/`）：`tushare_qfq` / `tushare_moneyflow` / `tushare_daily_basic` 各约 **66** 个 symbol 目录；分区 `year=2023..2026` parquet；另有 `tushare/`、`tushare_fund_daily/`、`tushare_probe_live/`。
- `inputs/data/derived/` 目前仅有 README（衍生层尚未建成）。
- Pool：`inputs/pools/low_manipulation/symbols.csv` = **14** 只（不含表头）。
- 本轮 shell 观测：`TUSHARE_TOKEN=unset`（不等于机器永久无 token；只说明当前会话未注入）。
- 测试布局（MS-T1）：`tests/{unit,integration,contract}/`；已有 `tests/integration/sources/test_tushare_source.py`。
- Zone layout（MS-R2）：cache/derived 落在 `inputs/data/`。
- 高风险信号：外部付费/配额 API、可能的全市场拉数、生产主数据源切换 — 触发 complex-project entry gate。
- Programmer（2026-07-14T21:16+08:00）：确认精选池方向，但指出 **B 的现有精选池不一定优秀，可能需要重新组合股票池**。
- Programmer（2026-07-14T21:39+08:00）：**D1b = P1** — 池重组纳入 R4 前置 worktrack。
- Programmer（2026-07-14T21:44+08:00）：**D1c = C2** — 新策略族 + ≤100 硬上限；旧池仅对照。
- Programmer（2026-07-14T21:48+08:00）：**D2 = L2** — limited-live；禁 full/全市场。
- Programmer（2026-07-14T22:17+08:00）：**D3 = R1** — 审计后复用 cache∩新池；缺口/失败才 limited-live。
- Programmer（2026-07-14T23:32+08:00）：**CG2 = M1 / normal**。
- Programmer（2026-07-15T00:10+08:00）：**BRIEF = Y** — 确认 D4/D5 默认 + suggested brief；intake → ready。
- `low_manipulation` metadata：`pool_size=14`，`total_universe=64`，`score_threshold=60`，proxy 评分非真实控盘概率；生成于 2026-06-22。
- Repo 已有 `stock_pool` 策略/registry 合同（`docs/guides/stock_pool_maintenance_guide.md`）：策略 → `configs/stock_pools/` 三件套导出。

## Inferred Assumptions

- D1 = 非全市场精选；现有池非真理。
- D1b = P1：先新池后灌湖。
- D1c = C2：新 `stock_pool` 策略族；目标池 **≤100**（指数是否另计待 A0 写明）；打分细节可在 A0 草案拍板。
- D2 = L2：允许对批准新池 limited-live 增量补洞；禁止 full-campaign 与全市场；具体日/RPM 上限由 A1 草案后批准。
- D3 = R1：审计后复用旧 cache∩新池；新 symbol / 失败分区才 limited-live。
- CG2 = M1/normal：高风险动作显式批准。
- 「优秀」= 可审计新准则下的可复现池，不是开放式 alpha 研究。
- 现有 ~66 parquet 可作 bootstrap / 与新池交集的 cache-first 输入。
- AkShare 默认保留备用，除非 D5 另定。
- X×Y×Z 训练不属于 R4。

## Unknowns

- ~~D1 / D1b / D1c / D2(CG1) / D3 / CG2 / D4 / D5 / BRIEF~~ 已确认
- 残余（已接受）：新策略维度/权重 → A0；日/RPM 数值 → A1 后再批
- 仍需显式 Init 指令才会 create/activate milestone

## Programmer Decisions Required

```yaml
programmer_decisions_required:
  - id: D1
    status: answered
    answer: "B-direction — 非全市场精选；现有池不锁定"
    answered_at: 2026-07-14T21:16:00+08:00
  - id: D1b
    status: answered
    answer: "P1 — 池重组作为 R4 前置 worktrack"
    answered_at: 2026-07-14T21:39:00+08:00
  - id: D1c
    status: answered
    answer: "C2 — 新策略族 + ≤100 硬上限；旧 low_manipulation 仅对照"
    answered_at: 2026-07-14T21:44:00+08:00
    blocks_ready: false
  - id: D2
    status: answered
    answer: "L2 — limited-live；新池≤100 增量补洞；禁 full/全市场；日/RPM 数字 A1 后再批"
    answered_at: 2026-07-14T21:48:00+08:00
    blocks_ready: false
  - id: D3
    status: answered
    answer: "R1 — 审计后复用 cache∩新池；新 symbol/失败分区才 limited-live"
    answered_at: 2026-07-14T22:17:00+08:00
    blocks_ready: false
  - id: CG2
    status: answered
    answer: "M1 / normal"
    answered_at: 2026-07-14T23:32:00+08:00
    blocks_ready: false
  - id: D4
    status: answered
    answer: "D4-default — lake contract + 质量审计收口；训练矩阵另开 milestone"
    answered_at: 2026-07-15T00:10:00+08:00
    blocks_ready: false
  - id: D5
    status: answered
    answer: "D5-default — 默认路径切 TuShare；AkShare 代码保留备用"
    answered_at: 2026-07-15T00:10:00+08:00
    blocks_ready: false
  - id: BRIEF
    status: answered
    answer: "Y — 确认 D4/D5 默认 + suggested brief"
    answered_at: 2026-07-15T00:10:00+08:00
    blocks_ready: false
```

## Risk Flags

```yaml
risk_flags:
  - id: R1
    kind: data
    severity: high
    description: "全市场拉数触发 TuShare 频率墙/配额耗尽；缓解：分阶段 universe + dry-run/cache-first + 显式 live 授权"
  - id: R2
    kind: scope_creep
    severity: high
    description: "R4 滑入 X×Y×Z 训练或模型晋升；缓解：non-goals 锁定训练/晋升，收口在 lake contract + QA"
  - id: R3
    kind: compatibility
    severity: medium
    description: "旧 cache schema/分区与新合同不一致导致假绿；缓解：schema/contract 测试 + 审计 worktrack"
  - id: R4
    kind: security
    severity: medium
    description: "TUSHARE_TOKEN 泄露或写入仓库；缓解：仅环境变量/本地 secret，禁止 commit"
  - id: R5
    kind: complex_project
    severity: medium
    description: "外部 API + 生产源切换 + 大数据量；需 operator_safety_policy 显式确认"
  - id: R6
    kind: governance_gap
    severity: low
    description: "旧 intake 过时；本轮 refresh 后不得沿用 R2/R3 blocks"
  - id: R7
    kind: scope_creep
    severity: medium
    description: "池重组若无边界，可能把 R4 拖成选股研究里程碑；缓解：D1b 明确池工作是 R4 前置切片、并行切片或后置 milestone"
```

## Complex Project Entry Gate

```yaml
complex_project_entry_gate:
  gate_id: "MS-R4-001-CPEG-2026-07-14"
  target_repo: "T1.AI"
  target_milestone_id: "MS-R4-001"
  trigger_source: "pre-milestone-intake"
  entry_verdict: clear
  scanner_evidence_ref: "N/A (manual hydrate; no separate scanner artifact)"
  complexity_signals:
    - signal: external_quota_api
      threshold: "any live TuShare campaign"
      observed_value: "tushare_source + existing caches; TUSHARE_TOKEN unset in this shell"
      confidence: high
      rationale: "Live pull can consume paid quota and hit rate limits"
    - signal: production_source_switch
      threshold: "default source change"
      observed_value: "NEXT_STEPS lists TuShare primary / AkShare backup; both adapters present"
      confidence: high
      rationale: "Default-path migration affects downstream dataset builders"
    - signal: large_universe_pull
      threshold: "full mainboard since 2023"
      observed_value: "D1/D1b/D1c locked: curated ≤100 new strategy; not full mainboard"
      confidence: high
      rationale: "Full-market risk deferred; residual risk is ≤100 limited-live补洞"
  operator_safety_policy:
    docker_compose_permission: blocked
    database_migration_permission: blocked
    deploy_network_permission: requires_approval
    destructive_cleanup_permission: requires_approval
    secrets_policy: "TUSHARE_TOKEN via env only; never commit secrets; no token in artifacts"
    protected_paths:
      - ".env"
      - "inputs/data/cache/"
      - "inputs/data/derived/"
    protected_branches:
      - develop
    allowed_high_risk_command_modes: "normal"
    live_tushare_pull_permission: limited_live_approved_pending_numeric_caps
    quota_consuming_campaign_permission: full_campaign_forbidden
    full_market_pull_permission: forbidden
  dialog_review_questions:
    - id: CG1
      question: "是否允许本 milestone 内进行配额消耗型 TuShare live pull？可选：cache-only / dry-run-only / limited-live(需上限) / full-campaign"
      why_it_matters: "未授权 live pull 时不得把补洞拉数写入 worktrack 验收；与 D2 合并裁决"
      recommended_answer: "limited-live：仅对批准新池（≤100）增量补洞，设 RPM/日调用上限；禁止 silent full-campaign"
      tradeoff: "cache-only 更快更安全但新池缺口可能无法补齐；full-campaign 仍禁止"
      blocks_ready: true
    - id: CG2
      question: "高风险命令模式选 normal / autoreview / yolo？"
      why_it_matters: "决定 live pull 与破坏性清理的自动性"
      recommended_answer: "normal（显式批准每类高风险动作）"
      tradeoff: "yolo 加速但易误耗配额/误删 cache"
      blocks_ready: true
  milestone_blocking_decision:
    - allow_create
    - allow_upsert
    - allow_activate
    - block_derive_worktrack
  reinforcement_milestone_recommendation:
    needed: false
    recommendation_status: not_needed
    recommendation_type: N/A
    suggested_title: ""
    suggested_purpose: ""
    recommendation_reason: "Repo 已有 TuShare adapter、cache 布局与 R2 zone docs；阻断来自 universe/quota 决策，而非弱文档理解缺口"
    temporary_understanding_ref: null
    evidence_refs:
      - ".servo/worktrack/WT-T1-A4-r4-handoff.md"
      - "src/ashare_lab/data/tushare_source.py"
      - "docs/architecture/repo_structure_guide.md"
    confirmation_required: false
    blocks_implementation_until_resolved: false
  evidence_refs:
    - ".servo/repo/milestone-backlog.md"
    - ".servo/worktrack/WT-T1-A4-r4-handoff.md"
    - ".servo/control-state.md"
```

## Open Questions

```yaml
open_questions: []
answered_questions:
  - D1=B_direction
  - D1b=P1
  - D1c=C2_cap100
  - D2=L2
  - D3=R1
  - CG2=M1
  - D4=default_lake_qa
  - D5=default_tushare_primary
  - BRIEF=Y
unresolved_questions: []
```

## Continuous Intake State

```yaml
continuation_state:
  continuation_required: false
  continuation_round: 8
  continuation_reason: "BRIEF=Y; intake ready; await explicit Init instruction"
  answered_questions:
    - id: D1
      answer_summary: "B-direction — 非全市场精选；现有池不锁定，可重组"
      answered_at: 2026-07-14T21:16:00+08:00
      source: programmer
    - id: D1b
      answer_summary: "P1 — 池重组作为 R4 前置 worktrack"
      answered_at: 2026-07-14T21:39:00+08:00
      source: programmer
    - id: D1c
      answer_summary: "C2 — 新策略族 + ≤100 硬上限；旧池仅对照"
      answered_at: 2026-07-14T21:44:00+08:00
      source: programmer
    - id: D2
      answer_summary: "L2 — limited-live；禁 full/全市场；日/RPM 数字 A1 后再批"
      answered_at: 2026-07-14T21:48:00+08:00
      source: programmer
    - id: D3
      answer_summary: "R1 — 审计后复用 cache∩新池；缺口/失败才 limited-live"
      answered_at: 2026-07-14T22:17:00+08:00
      source: programmer
    - id: CG2
      answer_summary: "M1 / normal"
      answered_at: 2026-07-14T23:32:00+08:00
      source: programmer
    - id: D4
      answer_summary: "lake+QA 收口；训练另开"
      answered_at: 2026-07-15T00:10:00+08:00
      source: programmer
    - id: D5
      answer_summary: "TuShare 默认；AkShare 保留备用"
      answered_at: 2026-07-15T00:10:00+08:00
      source: programmer
    - id: BRIEF
      answer_summary: "Y — 确认 D4/D5 默认 + suggested brief"
      answered_at: 2026-07-15T00:10:00+08:00
      source: programmer
  unresolved_questions: []
  next_required_question: null
  next_question_blocks_ready: false
  residual_risk_accepted: true
  accepted_residual_risk:
    - new_strategy_dimension_weights_deferred_to_A0
    - daily_rpm_numeric_caps_deferred_to_A1_then_approve
```

## Recommended Answers

```yaml
recommended_answers:
  D1:
    answer: "B-direction（非全市场）+ 现有池不锁定"
    status: programmer_confirmed
  D1b:
    answer: "P1 — 池重组作为 R4 前置 worktrack，再灌湖"
    status: programmer_confirmed
  D1c:
    answer: "C2 — 新策略族 + ≤100 硬上限；旧 low_manipulation 仅对照"
    status: programmer_confirmed
  D2:
    answer: "L2 — limited-live（新池增量补洞 + 日/RPM 上限；禁 full/全市场）"
    status: programmer_confirmed
  D3:
    answer: "R1 — 审计后复用 cache∩新池；新 symbol/失败分区才 limited-live"
    status: programmer_confirmed
  CG2:
    answer: "M1 / normal"
    status: programmer_confirmed
  D4:
    answer: "D4-default — lake+QA 收口；训练另开"
    status: programmer_confirmed
  D5:
    answer: "D5-default — TuShare 默认；AkShare 保留备用"
    status: programmer_confirmed
  BRIEF:
    answer: "Y — 确认 brief 与 D4/D5 默认"
    status: programmer_confirmed
  D4:
    answer: "R4 以 lake contract + 质量审计收口；训练矩阵另开 milestone"
  D5:
    answer: "默认路径切 TuShare；AkShare 代码保留备用"
```

## Scope Boundary

```yaml
scope_boundary:
  in_scope:
    - "TuShare 作为默认日频数据源合同（qfq / moneyflow / daily_basic，自 2023-01-01）"
    - "inputs/data/cache 分区 parquet 湖布局与可复现 fetch/load 路径"
    - "inputs/data/derived 高阶衍生特征层的最小可用合同（动量/波动/技术指标一类）"
    - "cache-first + 经批准的增量 live 补洞（D2=L2；D3=R1 审计复用交集）"
    - "schema/contract 测试与质量审计（完整性、复权口径、分区约定）"
    - "按 T1 handoff 将相关测试放入 tests/integration/sources|dataset 与 tests/contract"
    - "可版本化新策略池重组/注册（P1+C2：新策略族，≤100）——旧 low_manipulation 仅对照"
  out_of_scope:
    - "未批准的全市场 silent full-campaign"
    - "X×Y×Z 全量训练、模型重训、alpha_score 晋升"
    - "分钟级/stk_mins 数据湖（属 1d 线前置）"
    - "删除 AkShare 代码（除非 D5 显式批准）"
    - "把旧 low_manipulation 14 或未审计 ~66 cache 默认为最终研究 universe"
    - "无准则、无规模上限的开放式「找更优股票」研究"
    - "commit/push、破坏性清理、依赖升级、生产部署（仍审批门控）"
```

## Non Goals

```yaml
non_goals:
  - "把 R4 做成训练/回测里程碑"
  - "在未锁定 universe 前宣称「全市场数据湖已完成」"
  - "把「最优选股研究」做成无边界开放题（需 D1c 收束准则+上限）"
  - "回退 tests/ 到扁平布局"
  - "把 token 或原始密钥写入仓库/artifact"
```

## Acceptance Signals

```yaml
acceptance_signals:
  - "CS1: 默认数据源合同文档/代码路径以 TuShare 为准（AkShare 备用语义清晰）"
  - "CS2: 批准 universe（经 D1b 路径产出的池）在 cache 中具备约定字段与 year 分区，可复现 load"
  - "CS3: derived 层最小合同落地并可被测试断言"
  - "CS4: schema/contract + 质量审计报告存在；缺口有明确补洞或 defer 记录"
  - "CS5: 无未批准配额战役；无 token 泄露；测试落在 Arch-v1 布局"
  - "CS6: 最终验收不默认绑定旧 low_manipulation；绑定经批准的 pool artifact/version"
```

## Suggested Milestone Brief

```yaml
suggested_milestone_brief:
  milestone_id: MS-R4-001
  title: TuShare 数据湖构建（精选池重组 + 可复现湖合同）
  purpose: >
    在 R2/R3/T1 基线上：先以新 stock_pool 策略族重组可版本化精选池（≤100），
    再以 TuShare 为默认日频源，按 R1 审计复用 + L2 limited-live 构建
    cache/derived 可复现数据湖与质量审计；不以旧 low_manipulation 为最终 universe，
    不做全市场/full-campaign，不做训练矩阵/模型晋升。
  milestone_kind: goal-driven
  status: initialized_active
  depends_on_milestones: [MS-T1-001]
  priority: 5
  completion_threshold_pct: 100
  decisions_locked:
    - D1=B_direction
    - D1b=P1
    - D1c=C2_cap100
    - D2=L2
    - D3=R1
    - CG2=M1_normal
    - D4=default_lake_qa_closeout
    - D5=default_tushare_primary_akshare_backup
  candidate_worktracks:
    - WT-R4-A0: 新策略准则草案 + ≤100 池导出（registry）+ 与旧池差异说明
    - WT-R4-A1: 湖/源合同 + cache inventory + schema + 日/RPM 上限建议（供批准）
    - WT-R4-A2: Cache-first 加载路径与 contract/integration 测试（Arch-v1）
    - WT-R4-A3: 经批准的 limited-live 增量补洞 + 频率墙/简历策略（normal 模式）
    - WT-R4-A4: derived 最小实现 + 质量审计报告收口（非训练）
  completion_signals:
    - "可版本化新池 artifact 已注册且 ≤100"
    - "默认 TuShare 路径可用且有测试；AkShare 仍为备用"
    - "批准池的 cache/derived 可复现 load"
    - "质量审计报告已交接；无未批准 full/全市场战役"
  acceptance_criteria:
    - "决策 D1–D5/CG2 已写入 contract"
    - "验收绑定批准池版本，而非旧 low_manipulation"
    - "Arch-v1 测试布局保持"
    - "无 token 入仓；无未批准 full-campaign"
  activation_intent: "activated 2026-07-15 after explicit Init"
  scope_boundary_note: "Initialized and activated 2026-07-15"
```

## Confirmation State

```yaml
confirmation_state:
  confirmation_required: false
  programmer_confirmed: true
  confirmed_answers:
    - D1: "B-direction; existing curated pool not locked; recombination possible"
    - D1b: "P1 — pool recombination as R4 front worktrack"
    - D1c: "C2 — new strategy family, cap ≤100"
    - D2: "L2 — limited-live; full/full-market forbidden"
    - D3: "R1 — audit-reuse cache∩new pool"
    - CG2: "M1 / normal"
    - D4: "lake+QA closeout; training deferred"
    - D5: "TuShare primary; AkShare backup"
    - BRIEF: "Y"
  residual_risk:
    - new_strategy_dimension_weights_deferred_to_A0
    - daily_rpm_numeric_caps_deferred_to_A1_then_approve
  residual_risk_accepted: true
  accepted_residual_risk:
    - new_strategy_dimension_weights_deferred_to_A0
    - daily_rpm_numeric_caps_deferred_to_A1_then_approve
```

## Skip Record

```yaml
skip_record:
  intake_skipped: false
  skip_reason: null
  accepted_risk: []
  note: "not skipped; ready granted via BRIEF=Y path, not skip path"
```

## Handoff To Init Milestone

```yaml
handoff_to_init_milestone:
  allowed: false
  handoff_reason: "Init completed 2026-07-15T00:16:00+08:00; milestone active; see .servo/milestone/MS-R4-001.md"
  required_inputs: []
  blocked_by: []
  init_completed: true
  artifact_path: .servo/milestone/MS-R4-001.md
  milestone_branch: milestone/MS-R4-001-tushare-datalake
```

## Milestone Review Gate Handoff

```yaml
milestone_review_gate_handoff:
  target_milestone_id: MS-R4-001
  review_status: effective_pass
  milestone_review_count_increment: 1
  latest_review_status: effective_pass
  latest_review_checkpoint: "MS-R4-001-intake-ready-2026-07-15T00:10:00+08:00"
  latest_review_ref: ".servo/repo/MS-R4-001-pre-milestone-intake-review.md"
  effective_review_pass: true
  review_invalidated_by:
    worktrack_list_changed: false
    completion_signals_changed: false
    acceptance_criteria_changed: false
    scope_or_non_goals_changed: false
    risk_boundary_changed: false
    note: "Fresh effective pass after continuous intake rounds 1-8"
  blockers: []
```
