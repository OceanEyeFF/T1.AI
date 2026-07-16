"""C2: run_infra_smoke.py --json schema contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.paths import REPO_ROOT

REQUIRED_TOP = {
    "scope_id",
    "frozen",
    "symbols",
    "window_start",
    "window_end",
    "events",
    "scenario_steps",
}


@pytest.mark.contract
def test_smoke_json_schema_keys(tmp_path: Path) -> None:
    cache = tmp_path / "smoke_cache"
    env = {**os.environ, "PYTHONPATH": "src:."}
    proc = subprocess.run(
        [sys.executable, "scripts/run_infra_smoke.py", "--json", "--cache-dir", str(cache)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    missing = REQUIRED_TOP - set(report)
    assert not missing, f"missing keys: {missing}"
    assert isinstance(report["events"], list)
    assert isinstance(report["scenario_steps"], list)
    assert report["frozen"] is True
    assert len(report["scenario_steps"]) >= 1
    for step in report["scenario_steps"]:
        assert "step" in step
