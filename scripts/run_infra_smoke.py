#!/usr/bin/env python3
"""Infra smoke runner — simulated download / add stock / set start (no network).

Examples
--------
    conda activate py311-private
    export PYTHONPATH=src:.

    python scripts/run_infra_smoke.py
    python scripts/run_infra_smoke.py --cache-dir /tmp/infra_smoke --json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    from tests.support.infra_a import run_smoke_scenario

    parser = argparse.ArgumentParser(description="Infra smoke fetch scenario (no network)")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cleanup = None
    cache_dir = args.cache_dir
    if cache_dir is None:
        cleanup = tempfile.TemporaryDirectory(prefix="infra_smoke_")
        cache_dir = Path(cleanup.name)
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        report = run_smoke_scenario(cache_dir)
    finally:
        pass

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== Infra Smoke Report ===")
        print(f"scope_id     : {report['scope_id']}")
        print(f"frozen       : {report['frozen']}")
        print(f"symbols      : {report['symbols']}")
        print(f"window       : {report['window_start']} → {report['window_end']}")
        print(f"cached       : {report['cached_symbols']}")
        print("--- scenario ---")
        for step in report["scenario_steps"]:
            print(f"  • {step['step']}: { {k: v for k, v in step.items() if k != 'step'} }")
        print("--- journal ---")
        for ev in report["events"]:
            print(
                f"  [{ev['at']}] {ev['kind']}: "
                f"{ {k: v for k, v in ev.items() if k not in ('kind', 'at')} }"
            )

    if cleanup is not None:
        cleanup.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
