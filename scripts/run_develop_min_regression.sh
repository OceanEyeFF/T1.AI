#!/usr/bin/env bash
# Develop min regression — aliases to Arch-v1 fast lane (unit + contract).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${repo_root}/scripts/run_tests_fast.sh" "$@"
