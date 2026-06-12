---
title: "WT-A3-001 Optimization Queue"
artifact_type: "worktrack-report"
worktrack_id: "WT-A3-001"
milestone_id: "MS-S0-001"
updated: "2026-06-11T20:55:00+08:00"
owner: "OceanEyeFF"
---

# WT-A3-001 Optimization Queue

## Control Signal

- worktrack_id: WT-A3-001
- report_status: queue_defined
- model_training_performed: false
- external_provider_calls_performed: false
- dry_run_manifest: .servo/worktrack/evidence/multilevel_tuning_manifest_WT-A3-001-dryrun.json
- protocol_dependency: docs/research/mainline_3510d_evaluation_gate_protocol.md
- alpha_score_status: candidate_research_signal_only
- recommended_next_route: WorktrackScope.Verify

## A3-T1 Candidate Source Inventory

### Existing Sources

- `docs/research/mainline_3510d_evaluation_gate_protocol.md`: A2 protocol and promotion rules.
- `docs/research/multilevel_tuning_plan_20260307.md`: L1/L2/L3 tuning dimensions and execution examples.
- `docs/research/mainline_3510d_model_development_plan_20260310.md`: LSTM and XGBoost baseline closure order.
- `scripts/run_multilevel_tuning.py`: dry-run plan generator and optional execution runner.
- `scripts/auto_tune_xgb.py`: Optuna XGB execution runner; not safe for this planning-only Worktrack unless `n_trials=0` summary mode is used.
- `configs/experiments/lstm_rolling_baseline.toml`
- `configs/experiments/lstm_rolling_fastpilot.toml`
- `configs/experiments/xgb_rolling_baseline.toml`
- `configs/experiments/xgb_rolling_fastpilot.toml`

### Readiness Observations

- LSTM rolling script writes `evaluation_protocol`, `comparison_panel`, and OOS parquet path.
- XGBoost rolling script has maturity gate and OOS parquet support, but static inspection did not confirm `evaluation_protocol` or `comparison_panel` writeout.
- `run_multilevel_tuning.py` dry-run produces LSTM/XGB L1 commands without executing training when `--execute` is omitted.
- Current dry-run compare commands include `--check-protocol` after the A3 tool alignment fix.

## Prioritized Queue

| priority | candidate_id | family | task | why first | A2 prerequisite | execution status |
|---:|---|---|---|---|---|---|
| 1 | A3-Q1 | tooling/protocol | `run_multilevel_tuning.py` generated compare commands include `--check-protocol` | Prevents A3 from bypassing A2 protocol | A2 report contract | done |
| 2 | A3-Q2 | XGBoost baseline | Confirm and, if needed, add XGB `evaluation_protocol` / `comparison_panel` report writeout | XGB cannot be a fair baseline if report contract is incomplete | required before XGB compare | planned, medium risk |
| 3 | A3-Q3 | LSTM baseline | Run limited L1 dry-run manifest review for LSTM learning-rate/dropout/loss-weight candidates | Low-risk queue shape, no training yet | protocol-ready script | dry-run ready |
| 4 | A3-Q4 | XGBoost baseline | Run limited L1 dry-run manifest review for n_estimators/depth/learning-rate candidates | Establish XGB queue after protocol readiness | blocked by Q2 for execution | dry-run ready |
| 5 | A3-Q5 | stability | Define L2 window/regularization candidates for reducing worst month and negative streak | Targets A2 failure modes directly | Q1/Q2 + baseline evidence | planned |
| 6 | A3-Q6 | fusion | Define lightweight fusion only after LSTM/XGB same-window reports pass protocol | Avoids hiding weak base models with aggregation | requires credible LSTM/XGB evidence | deferred |

## Candidate Interpretation Rules

- `go`: candidate reports satisfy A2 protocol, pass raw or calibrated strict gate with anti-cheat support, and trade-like panel is not contradictory.
- `no-go`: candidate has comparable OOS/report coverage but fails strict metrics or sanity checks.
- `continue-research`: report contract incomplete, protocol command missing, shared OOS window absent, or anti-cheat surfaces missing.

## Dry-Run Evidence

Commands run:

```bash
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/run_multilevel_tuning.py" --model both --level L1 --max-runs-per-level 4
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/run_multilevel_tuning.py" --model both --level L1 --max-runs-per-level 4 --output-dir ".servo/worktrack/evidence" --tag "WT-A3-001-dryrun"
```

Result:

- No `--execute` flag was used.
- LSTM L1 planned runs: 4.
- XGB L1 planned runs: 4.
- Initial manifest saved: `output/reports/multilevel_tuning_manifest_20260611.json`.
- Final Worktrack manifest saved: `.servo/worktrack/evidence/multilevel_tuning_manifest_WT-A3-001-dryrun.json`.
- A3 fixed generated compare commands so final dry-run commands include `--check-protocol`.

## Validation Evidence

```bash
PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_multilevel_tuning.py tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py
```

Result:

- `28 passed`

## Future Execution Slice Boundary

Any actual training execution must be a separate Worktrack task or execution slice with explicit scope:

- exact model family and candidate count
- dataset path and OOS window
- expected runtime budget
- generated artifact paths
- A2 validation commands including `--check-protocol`
- stop conditions for failing protocol or sanity gates

## Gate Handoff

- This planning-only Worktrack can pass if it documents the queue, dry-run finding, and execution boundary.
- It must not claim any candidate model is improved or tradable.
