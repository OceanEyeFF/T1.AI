"""WT-INFRA-002: business modules must not directly import load_or_fetch_*."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Locked Phase 2 must-change surfaces (see WT-INFRA-002-brief.md).
SCAN_TARGETS = (
    REPO_ROOT / "src/ashare_lab/recommendation/validator.py",
    REPO_ROOT / "src/ashare_lab/dataset/builder.py",
    REPO_ROOT / "scripts/run_sim_replay.py",
)

# Only lake + data adapters may call load_or_fetch_* (adapters are infra-internal).
ALLOWED_PREFIXES = (
    "ashare_infra.lake",
    "ashare_infra.data",
)


def _imported_load_or_fetch_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                name = alias.name
                if name.startswith("load_or_fetch") or (
                    alias.asname and alias.asname.startswith("load_or_fetch")
                ):
                    if not any(mod.startswith(p) for p in ALLOWED_PREFIXES):
                        hits.append(f"{mod}.{name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "load_or_fetch" in alias.name:
                    hits.append(alias.name)
    return hits


@pytest.mark.parametrize("path", SCAN_TARGETS, ids=lambda p: p.name)
def test_no_direct_load_or_fetch_import(path: Path) -> None:
    assert path.is_file(), f"missing scan target: {path}"
    hits = _imported_load_or_fetch_names(path)
    assert hits == [], f"{path.name} still imports load_or_fetch_*: {hits}"
