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
