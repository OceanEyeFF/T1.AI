from __future__ import annotations

import sys
from pathlib import Path

import pytest


from scripts.env_guard import ensure_required_conda_env


def test_env_guard_accepts_expected_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "ashare-lab")
    monkeypatch.setattr(sys, "executable", "/home/user/miniconda3/envs/ashare-lab/bin/python")
    ensure_required_conda_env("ashare-lab")


def test_env_guard_rejects_base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")
    monkeypatch.setattr(sys, "executable", "/home/user/miniconda3/bin/python")
    with pytest.raises(RuntimeError):
        ensure_required_conda_env("ashare-lab")

