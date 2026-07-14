#!/usr/bin/env bash
# Fast lane: unit + contract (excludes integration / slow / gpu).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PYTHONPATH="src:."

pytest -q -m "unit or contract" --tb=line "$@"
