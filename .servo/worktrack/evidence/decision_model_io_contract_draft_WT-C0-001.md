---
title: "WT-C0-001 Decision Model I/O Contract Draft"
artifact_type: "worktrack-evidence"
worktrack_id: "WT-C0-001"
milestone_id: "MS-S0-001"
updated: "2026-06-11T21:01:55+08:00"
owner: "OceanEyeFF"
---

# WT-C0-001 Decision Model I/O Contract Draft

## Control Signal

- worktrack_result: pass for C0 draft-only scope
- implementation_status: draft_only
- trading_logic_changed: no
- signal_promotion_changed: no
- alpha_score_default_status: candidate_research
- one_day_signal_default_status: disabled
- next_allowed_stage: C1/C2/C3 only under later approved Worktracks

## Existing Surfaces

| Surface | Current fact | C0 implication |
|---|---|---|
| `docs/overview/three_track_development_plan_20260609.md#5` | Defines C0 as I/O freeze only | C0 must not implement trading behavior. |
| `docs/interfaces/protocol.md` | Defines close signal, next-open execution, T+1, limit blocks, risk buy disablement, diagnostics | C0 must preserve these protocol fields and diagnostics names. |
| `docs/modules/system_io_and_architecture_spec.md#5.2` | Trading output includes target positions, orders, risk checks, action, reason | C0 output should align with that shape. |
| `src/ashare_lab/recommendation/engine.py` | Generates recommendation items and trend diagnostics | C0 input can consume fixed signal records without running the recommendation engine. |
| `src/ashare_lab/strategy/portfolio.py` | Computes simple target weights; C1/C2 logic is TODO | C0 drafts fields for later work but does not implement them. |
| `src/ashare_lab/backtest/engine.py` | Produces fills and diagnostics counters | C0 output diagnostics should be compatible with existing counter vocabulary. |

## Decision Input Draft

Each decision input row is a symbol-date record. A replay input can be CSV/Parquet and must be complete enough to produce decisions without executing a model.

Required fields:

- `decision_date`
- `symbol`
- `alpha_score`
- `alpha_score_status`
- `pred_3d`
- `pred_5d`
- `pred_10d`
- `component_weights`
- `current_position_weight`
- `current_position_shares`
- `cash_available`
- `estimated_cost_rate`
- `min_commission`
- `risk_state`
- `tradability_state`
- `protocol`

Optional fields:

- `one_day_signal`
- `one_day_signal_status`
- `uncertainty`
- `signal_version`
- `model_config_id`
- `data_snapshot_id`
- `explain`

Signal status values:

- `candidate_research`
- `continue_research`
- `approved_for_shadow`
- `approved_for_decision_eval`
- `blocked`
- `disabled`

Current defaults after this milestone evidence:

- `alpha_score_status = candidate_research` unless a later gate explicitly promotes it.
- `one_day_signal_status = disabled` because B0 did not prove minute replay readiness.

## Decision Output Draft

Each decision output is a portfolio-date record.

Required top-level fields:

- `decision_date`
- `portfolio_id`
- `target_positions`
- `orders`
- `no_trade_decisions`
- `risk_checks`
- `action_reason`
- `blocked_reason`
- `diagnostics`
- `replay_refs`

`target_positions` item fields:

- `symbol`
- `target_weight`
- `target_shares`
- `source_signal`
- `reason`

`orders` item fields:

- `symbol`
- `side`
- `qty`
- `target_weight`
- `estimated_price`
- `estimated_turnover`
- `estimated_cost`
- `urgency`
- `reason`
- `blocked_reason`

`no_trade_decisions` reason values:

- `signal_not_approved`
- `insufficient_score_edge`
- `cost_not_covered`
- `rebalance_threshold_blocked`
- `risk_buy_disabled`
- `buy_blocked_limit_up`
- `buy_blocked_halt`
- `sell_blocked_limit_down`
- `sell_blocked_tplus1`
- `cash_insufficient`
- `missing_tradability_data`
- `one_day_signal_disabled`
- `no_valid_candidate`

Diagnostics counters:

- `target_position_count`
- `order_count`
- `no_trade_count`
- `rebalance_threshold_blocked`
- `cost_coverage_blocked`
- `risk_buy_disabled`
- `buy_blocked_limit_up`
- `buy_blocked_halt`
- `sell_blocked_limit_down`
- `sell_blocked_tplus1`
- `missing_tradability_data`

## Replay Requirements

- Replay input format: fixed CSV or Parquet.
- Replay must not execute a prediction model.
- Replay must carry `signal_version`, `model_config_id`, `data_snapshot_id`, `protocol_version`, and `decision_config_id` where available.
- Same input records plus same decision config must produce the same output records.
- Missing signal maturity fields must default to the conservative state: do not trade.

## Scope Guards

- C0 does not promote `alpha_score`.
- C0 does not enable `one_day_signal`.
- C0 does not implement rebalance threshold, cost coverage, risk gating, execution diagnostics, portfolio learning, or real order routing.
- Any later logic that turns this draft into behavior requires a new Worktrack and fresh gate evidence.

## Gate Conclusion

C0 passes as a bounded I/O draft. It creates a safe downstream contract shape while preserving that current signals are not production trading inputs. The milestone can now proceed to milestone-level aggregate gate and programmer final acceptance.
