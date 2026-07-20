"""B0 gate: no live imports of deleted ashare_lab.strategy / strategies."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAN_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
)
FORBIDDEN_PREFIXES = (
    "ashare_lab.strategy",
    "ashare_lab.strategies",
)


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        files.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def _forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name == p or alias.name.startswith(p + ".") for p in FORBIDDEN_PREFIXES):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if any(node.module == p or node.module.startswith(p + ".") for p in FORBIDDEN_PREFIXES):
                hits.append(node.module)
    return hits


@pytest.mark.parametrize("path", _iter_py_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_ashare_lab_strategy_imports(path: Path) -> None:
    hits = _forbidden_imports(path)
    assert hits == [], f"{path.relative_to(REPO_ROOT)} still imports deleted lab strategy: {hits}"
