#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PYTHONPATH="src:."

pytest -q \
  tests/unit/evaluation/test_trade_like_panel.py \
  tests/unit/recommendation/test_trend_aggregation.py \
  tests/unit/recommendation/test_trend_schema.py \
  tests/integration/training/test_lstm_dynamic_heads.py \
  tests/integration/training/test_multilevel_tuning.py
