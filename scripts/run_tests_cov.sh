#!/usr/bin/env bash
# Full suite with coverage; enforces pyproject fail_under.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PYTHONPATH="src:."

pytest -q --cov=ashare_lab --cov-report=term-missing --tb=line "$@"
