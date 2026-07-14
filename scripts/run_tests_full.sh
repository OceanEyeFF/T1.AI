#!/usr/bin/env bash
# Full lane: entire Arch-v1 suite.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PYTHONPATH="src:."

pytest -q --tb=line "$@"
