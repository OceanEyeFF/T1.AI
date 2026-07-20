"""C3: scripts/run_sim_replay.py minimal smoke against Infra A seeded cache."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support import infra_a as fx
from tests.support.paths import REPO_ROOT


@pytest.mark.contract
def test_run_sim_replay_seeded_cache(tmp_path: Path) -> None:
    out_dir = tmp_path / "sim_out"
    # Copy the seeded cache into tmp so a cache miss can never write real
    # (network) data back into the committed fixture tree.
    cache = tmp_path / "cache"
    shutil.copytree(fx.seeded_cache_dir() / "akshare", cache)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_sim_replay.py",
            "--symbol",
            "600000",
            "--start",
            "20240102",
            "--end",
            "20240115",
            "--cache-dir",
            str(cache),
            "--out-dir",
            str(out_dir),
            "--cash",
            "20000",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src:."},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "wrote" in proc.stdout
    # one replay_* directory created
    kids = list(out_dir.glob("replay_600000_*"))
    assert len(kids) == 1
    assert (kids[0] / "equity.csv").exists()
    assert (kids[0] / "diagnostics.csv").exists()
