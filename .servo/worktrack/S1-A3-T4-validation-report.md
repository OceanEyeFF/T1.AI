---
title: "S1-A3-T4 Validation Report"
artifact_type: "worktrack-task-evidence"
updated: "2026-06-16T16:00:00+08:00"
owner: "OceanEyeFF"
---

# S1-A3-T4 Validation Report

## Control Signal

- task_id: S1-A3-T4
- task_title: Add focused tests and smoke checker evidence
- task_status: completed
- validation_result: pass
- recommended_next_action: S1-A3-T5 Produce gate evidence
- blocked_by_data: no for writer contract validation; historical report OOS absence remains a residual data limitation.

## Validation Commands

- `python -m py_compile scripts/run_xgboost_rolling_retrain_regime.py tests/test_xgboost_report_contract.py`
  - result: pass
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_xgboost_report_contract.py`
  - result: `2 passed`
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py`
  - result: `21 passed`
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_xgboost_report_contract.py tests/test_trade_like_panel.py tests/test_sanity_checks.py`
  - result: `43 passed`
- `PYTHONPATH="src:." conda run -n "py311-private" python scripts/compare_ic_reports.py --reports <tmp>/r1.json <tmp>/r2.json --daily-cs-mode off --check-protocol --output-dir <tmp>/out --tag xgb-contract-smoke`
  - result: pass; printed `[协议检查] 协议一致`

## Coverage Interpretation

- `tests/test_xgboost_report_contract.py` verifies that the XGBoost helper emits the strict protocol keys consumed by `compare_ic_reports.py`.
- The same test verifies the XGBoost comparison panel path on an in-memory primary 3d/5d/10d OOS frame.
- Existing compare/audit tests confirm missing protocol still fails and OOS path discovery behavior is unchanged.
- Trade-like panel tests confirm the reused comparison helper remains stable.
- Sanity check tests confirm A1/A2 guardrail code remains green after this report writer patch.

## Scope Control

- provider_calls: none
- long_training: none
- dependency_changes: none
- production_artifacts: none; smoke output was written under a temporary directory and removed
- commit_push_release: none

## Residual Risk

- No end-to-end XGBoost retraining was run by design.
- Historical `output/reports/mainline_3510d/xgb_fastpilot_20260323.json` still lacks OOS parquet path and cannot satisfy strict daily-CS without a matching OOS artifact.
