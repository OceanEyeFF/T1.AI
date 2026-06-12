"""Runtime environment guard for training scripts.

Ensures scripts run under the documented conda environment.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_required_conda_env(required_env: str = "py311-private") -> None:
    """Raise when current python runtime is not from the expected conda env."""
    exe = str(Path(sys.executable).resolve()).replace("\\", "/")
    expected_token = f"/envs/{required_env}/"
    conda_default_env = str(os.environ.get("CONDA_DEFAULT_ENV", "")).strip()

    problems: list[str] = []
    if expected_token not in exe:
        problems.append(
            f"python executable 不在目标 conda 环境下: {exe} (expected path contains '{expected_token}')"
        )
    if conda_default_env and conda_default_env != required_env:
        problems.append(
            f"CONDA_DEFAULT_ENV={conda_default_env!r}, expected {required_env!r}"
        )

    if problems:
        joined = "; ".join(problems)
        raise RuntimeError(
            f"环境检查失败: {joined}. "
            f"请使用 `conda run -n {required_env} python ...` 或先执行 `conda activate {required_env}`。"
        )
