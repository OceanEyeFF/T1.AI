#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PYTHONPATH="src:."

pytest -q \
  tests/test_trade_like_panel.py \
  tests/test_trend_aggregation.py \
  tests/test_trend_schema.py \
  tests/test_lstm_dynamic_heads.py \
  tests/test_multilevel_tuning.py
