# Gate Evidence

> 这是 `.servo/worktrack/gate-evidence.md` 的模板来源，用来记录当前 worktrack 的 gate 证据与裁决依据。
> 按 `Control Signal` / `Supporting Detail` 双层输出：`Control Signal` 只放影响下一动作决策的关键结论；`Supporting Detail` 放完整证据。

## Metadata

- worktrack_id:
- updated:
- gate_round:
- required_evidence_lanes:
- review_profile:

## Review Lane

> review_profile 驱动 review lane 选择：`light` / `standard` / `risky` / `deep`。review lanes 支持并行 `SubAgent` 执行；`deep` 使用四路 review 覆盖；运行时无法委派所选 lanes 时记录 fallback。lane ids 为 `static-semantic-review`（静态语义解释）、`test-review`（测试 review）、`project-security-review`（security review）、`complexity-performance-review`（代码复杂度和性能 review）。

### Control Signal
- review_subagent_lanes:
- review_profile:
- four_lane_dispatch_status:
- confidence:
- ready_for_gate:
- residual_risks:

### Supporting Detail
- input_ref:
- freshness:
- static_semantic_review:
- test_review:
- project_security_review:
- complexity_performance_review:
- four_lane_fallback_reason:
- missing_evidence:
- upstream_constraint_signals:
- low_severity_absorption_applied:

## Validation Lane

### Control Signal
- confidence:
- ready_for_gate:
- residual_risks:

### Supporting Detail
- input_ref:
- freshness:
- missing_evidence:
- upstream_constraint_signals:
- low_severity_absorption_applied:

## Policy Lane

### Control Signal
- confidence:
- ready_for_gate:
- residual_risks:

### Supporting Detail
- input_ref:
- freshness:
- missing_evidence:
- upstream_constraint_signals:
- low_severity_absorption_applied:

## Evidence Assessment

### Control Signal
- node_type:
- applied_gate_criteria:
- fallback_used:
- overall_confidence:
- overall_confidence_reason:
- freshness_blockers:

### Supporting Detail
- node_type_source:
- 完整证据维度摘要（首次生成时填充，后续更新只追加变更）

## Per-Surface Verdicts

### Control Signal
- implementation_surface:
- validation_surface:
- policy_surface:
- low_severity_absorption_reason:

### Supporting Detail
- 各面判定依据与引用

## Recommended Next Route

### Control Signal
- allowed_next_routes:
- recommended_next_route:
- approval_required:
- needs_programmer_approval:
- why:

### Supporting Detail
- approval_scope:
- approval_reason:

## Follow-up Actions

-
