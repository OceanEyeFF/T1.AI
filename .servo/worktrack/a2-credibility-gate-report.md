---
title: "WT-A2-001 Credibility Gate Report"
artifact_type: "worktrack-report"
worktrack_id: "WT-A2-001"
milestone_id: "MS-S0-001"
updated: "2026-06-11T20:24:20+08:00"
owner: "OceanEyeFF"
---

# WT-A2-001 Credibility Gate Report

## Control Signal

- worktrack_id: WT-A2-001
- milestone_id: MS-S0-001
- report_status: evidence_collected
- model_retraining_performed: false
- external_provider_calls_performed: false
- protocol_artifact: docs/research/mainline_3510d_evaluation_gate_protocol.md
- implementation_change: strict `evaluation_protocol` is now required when `scripts/compare_ic_reports.py --check-protocol` is used.
- historical_artifact_verdict: comparable_but_not_credible
- alpha_score_status: candidate_research_signal_only
- recommended_next_route: WorktrackScope.Verify

## A2-T1 Asset Inventory Result

### Reusable Assets

- `src/ashare_lab/evaluation/metrics.py`: Daily-CS IC / RankIC and monthly aggregation.
- `src/ashare_lab/evaluation/sanity_checks.py`: baseline IC, shuffle, time reverse, lag-1 checks.
- `src/ashare_lab/evaluation/trade_like_panel.py`: `alpha_score` Top-N trade-like comparison proxy.
- `scripts/audit_ic_reports.py`: OOS parquet coverage audit.
- `scripts/compare_ic_reports.py`: same-window Daily-CS comparison and protocol consistency gate.
- `scripts/run_sanity_checks.py`: CLI for shuffle/time-reverse/lag-1 checks.
- `src/ashare_lab/labels/multi_horizon.py`: close-to-close and next-open-to-open label modes.
- Tests: `tests/test_evaluation_metrics.py`, `tests/test_sanity_checks.py`, `tests/test_trade_like_panel.py`, `tests/test_compare_ic_reports.py`, `tests/test_audit_ic_reports.py`, `tests/test_maturity_gate.py`, `tests/test_labels.py`.

### Covered Gate Surfaces

- Daily-CS IC / RankIC: covered.
- Monthly stability: covered.
- Trade-like panel: covered as proxy only.
- Shuffle / time reverse / lag-1: covered.
- OOS/report coverage: covered.
- Protocol consistency: now strict when `--check-protocol` is used.
- Label maturity / trade timing: covered by protocol fields and existing maturity/label tests, but still depends on reports writing the fields.

### Known Gaps

- Independent random-label CLI is not implemented; shuffle is only a proxy.
- Industry / market-cap neutralization gate is not implemented.
- Existing historical evidence is quick8-scale and cannot represent the full mainline 3d/5d/10d model family.
- XGBoost report protocol generation should remain under review before A3 uses it as a same-window baseline.

## Historical Report Audit

Inputs:

- `output/reports/xgb_d1_close_candidate_quick8_20260309.json`
- `output/reports/xgb_nextopen_baseline_quick8_20260309.json`

Evidence:

- `.servo/worktrack/evidence/ic_report_oos_coverage_WT-A2-001-historical.md`
- `.servo/worktrack/evidence/ic_monthly_comparison_WT-A2-001-raw.md`
- `.servo/worktrack/evidence/ic_monthly_comparison_WT-A2-001-calibrated.md`
- `.servo/worktrack/evidence/sanity_xgb_nextopen_quick8_h5_WT-A2-001.json`
- `.servo/worktrack/evidence/sanity_xgb_nextopen_quick8_h10_WT-A2-001.json`

Observed facts:

- OOS coverage exists for both quick8 reports.
- Raw strict comparison uses 2/2 reports in Daily-CS mode over 7 common OOS months.
- Calibrated strict comparison uses 2/2 reports in Daily-CS mode over 7 common OOS months.
- Raw `xgb_nextopen_baseline_quick8` has `mean(IC_5_10)=0.0594` but `mean(RankIC_5_10)=0.0565`, below the `0.08` gate.
- Calibrated results fail strongly for both quick8 reports.
- Sanity checks on `xgb_nextopen_baseline_quick8` fail time-reverse for both h5 and h10, and fail lag-1 for h10.

Interpretation:

- The historical quick8 reports are comparable enough for A2 audit.
- They are not credible enough to promote `alpha_score`.
- Failure is a model/evidence credibility result for these quick8 reports, not a missing-artifact result.

## Validation Evidence

Commands run:

```bash
PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_compare_ic_reports.py tests/test_audit_ic_reports.py tests/test_sanity_checks.py
```

Result:

- `33 passed`

Non-training audit commands run:

```bash
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/audit_ic_reports.py" --reports "output/reports/xgb_d1_close_candidate_quick8_20260309.json" "output/reports/xgb_nextopen_baseline_quick8_20260309.json" --output-dir ".servo/worktrack/evidence" --tag "WT-A2-001-historical"
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/compare_ic_reports.py" --reports "output/reports/xgb_d1_close_candidate_quick8_20260309.json" "output/reports/xgb_nextopen_baseline_quick8_20260309.json" --metric-source raw --monthly-source raw --daily-cs-mode required --check-protocol --output-dir ".servo/worktrack/evidence" --tag "WT-A2-001-raw"
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/compare_ic_reports.py" --reports "output/reports/xgb_d1_close_candidate_quick8_20260309.json" "output/reports/xgb_nextopen_baseline_quick8_20260309.json" --metric-source calibrated --monthly-source calibrated --daily-cs-mode required --check-protocol --output-dir ".servo/worktrack/evidence" --tag "WT-A2-001-calibrated"
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/run_sanity_checks.py" --oos-parquet "output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet" --horizon 5 --output ".servo/worktrack/evidence/sanity_xgb_nextopen_quick8_h5_WT-A2-001.json"
PYTHONPATH="src:." conda run -n "py311-private" python "scripts/run_sanity_checks.py" --oos-parquet "output/reports/xgb_nextopen_baseline_quick8_20260309_oos.parquet" --horizon 10 --output ".servo/worktrack/evidence/sanity_xgb_nextopen_quick8_h10_WT-A2-001.json"
```

## A3 Handoff

- A3 may use the protocol artifact as the fixed comparison contract.
- A3 should first ensure candidate reports include full `evaluation_protocol`.
- A3 should treat random-label and industry / market-cap neutralization as missing anti-cheat enhancements unless implemented.
- A3 must not interpret quick8 OOS coverage as prediction credibility.
