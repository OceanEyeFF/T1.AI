"""WT-INFRA-002 / AO-O1: business modules must not directly import load_or_fetch_*.

Only ``ashare_infra.lake`` is allowlisted (DataLake façade). ``ashare_infra.data``
is intentionally excluded so consumers cannot bypass DataLake and still pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Phase 2 must-change + script anti-regression surfaces (WT-INFRA-002-brief.md).
SCAN_TARGETS = (
    REPO_ROOT / "src/ashare_lab/recommendation/validator.py",
    REPO_ROOT / "src/ashare_lab/dataset/builder.py",
    REPO_ROOT / "scripts/run_sim_replay.py",
    REPO_ROOT / "scripts/run_backtest.py",
    REPO_ROOT / "scripts/generate_daily_recommendations.py",
    REPO_ROOT / "scripts/build_sequence_dataset.py",
)

# Still deferred: needs DataLake APIs for daily_basic / moneyflow / ODP historical.
DEFERRED_SCAN_TARGETS = (
    REPO_ROOT / "scripts/build_sequence_dataset_market_state.py",
)

# AO-O1 (WT-R4-A4-T4): only DataLake façade may import load_or_fetch_*.
# Do NOT allowlist ashare_infra.data — that would greenlight bypassing DataLake.
ALLOWED_PREFIXES = (
    "ashare_infra.lake",
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


@pytest.mark.parametrize("path", DEFERRED_SCAN_TARGETS, ids=lambda p: p.name)
def test_deferred_targets_still_documented(path: Path) -> None:
    """Deferred scripts are listed in this module until DataLake grows extra APIs."""
    assert path.is_file()
    assert path in DEFERRED_SCAN_TARGETS
