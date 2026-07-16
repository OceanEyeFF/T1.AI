#!/usr/bin/env bash
# Infra A lane: lake + sim + guard (unit + integration infra fixtures).
# No network. Uses tests/fixtures/infra_a/.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PYTHONPATH="src:."

echo "== Infra A: guard / lake / sim fixture pack =="
pytest -q \
  tests/unit/guard/ \
  tests/unit/infra/ \
  tests/unit/sim/ \
  tests/unit/backtest/ \
  tests/integration/infra/ \
  tests/contract/infra/ \
  tests/integration/sources/ \
  tests/integration/dataset/test_universe.py \
  --tb=short \
  "$@"
