"""MS-R4 / WT-R4-A4-T3: derived load API contract (Arch-v1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_infra.lake import DataLake
from ashare_infra.lake.r4_contract import (
    R4_DERIVED_ROOT,
    make_r4_datalake,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DERIVED_README = REPO_ROOT / R4_DERIVED_ROOT / "README.md"


@pytest.mark.contract
def test_make_r4_datalake_binds_derived_root() -> None:
    lake = make_r4_datalake()
    assert lake.derived_root == R4_DERIVED_ROOT
    assert lake.resolved_derived_root() == R4_DERIVED_ROOT
    assert hasattr(lake, "load_derived")
    assert hasattr(lake, "load_derived_minimal")
    assert hasattr(lake, "load_scope_derived")


@pytest.mark.contract
def test_datalake_load_derived_is_filesystem_only_surface() -> None:
    """Load path is on DataLake; does not require refresh/token for derived."""
    lake = DataLake(cache_dir=Path("inputs/data/cache"), derived_root=R4_DERIVED_ROOT)
    assert lake.refresh is False
    assert callable(lake.load_derived)


@pytest.mark.contract
def test_derived_readme_documents_load_api() -> None:
    assert DERIVED_README.is_file()
    text = DERIVED_README.read_text(encoding="utf-8")
    assert "load_derived" in text
    assert "DataLake" in text or "make_r4_datalake" in text
    assert "零 live" in text or "zero live" in text.lower() or "filesystem" in text.lower()
