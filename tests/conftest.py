"""Shared pytest fixtures for Arch-v1 layout."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply Arch-v1 layer markers from path; tag known gpu/slow tests."""
    for item in items:
        path = Path(str(item.fspath)).as_posix()
        if "/tests/unit/" in path or path.endswith("/tests/unit"):
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/tests/contract/" in path:
            item.add_marker(pytest.mark.contract)

        name = item.name
        nodeid = item.nodeid
        if "cuda" in name.lower() or "cuda" in nodeid.lower():
            item.add_marker(pytest.mark.gpu)
        # Heavier training loops — optional slow lane for future CI splitting
        if nodeid.endswith(
            (
                "test_train_loop_updates_params_and_saves_checkpoints",
                "test_early_stopping_triggers_when_val_ic_stalls",
                "test_train_mtl_loads_parquet_sequence_dataset",
                "test_train_mtl_runs_on_cuda_if_available",
            )
        ):
            item.add_marker(pytest.mark.slow)
