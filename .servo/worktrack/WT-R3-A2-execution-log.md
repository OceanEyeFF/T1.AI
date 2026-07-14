---
title: "WT-R3-A2 Delete Execution Log"
artifact_type: "worktrack-execution-log"
milestone_id: "MS-R3-001"
worktrack_id: "WT-R3-A2"
updated: "2026-07-14T13:05:00+08:00"
---

# WT-R3-A2 Delete Execution Log

## Approval

- source: programmer message「Batch A + BatchB 的内容都可以删」
- inventory: `.servo/worktrack/WT-R3-A1-inventory.md`
- batches: A + B
- retained: Batch C / protected paths

## Deleted (summary)

- docs/archive/* body files（保留空壳 README）
- docs/research 过时 md/pdf（保留 checklist / eval gate / daily_cs / low_manipulation / README）
- workspace/checkpoints/best_mtl.pt, latest_mtl.pt, rolling_dim19/
- inputs/data/cache/akshare* + odp + 根目录散落 csv
- inputs/configs/experiments/{lstm,xgb}_rolling_{baseline,fastpilot}.toml
- scripts: run_dim52_group_ablation, run_lstm_dim16_vs_dim19_market, run_lstm_walkforward_sign_calibration, run_lstm_rolling_retrain_dim19_h2, clean_data.sh, build_universe, select_industry_stocks
- inputs/pools/momentum, inputs/pools/value 空壳

## Coupling fixes

- tests/test_deployment_files.py → 改验 `docs/guides/daily_pipeline_ops.md`
- tests/test_multilevel_tuning.py dry-run → 使用 tmp stub configs
- docs/research/README.md / daily_cs_eval_workflow.md / NEXT_STEPS.md / ROADMAP.md / experiments README / pyproject omit 清理

## Not deleted

- TuShare caches, low_manipulation pool, profiles, src, retained research docs, experiments README

## Residual

- F1/F2 stock_pool path failures still present → WT-R3-A3
