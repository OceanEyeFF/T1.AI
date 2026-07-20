"""Contract: Decision modules must not mint final portfolio weights."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DECISION_FILE = REPO_ROOT / "src/ashare_exec/decision.py"


def test_decision_module_has_no_target_weights_or_map_weights() -> None:
    tree = ast.parse(DECISION_FILE.read_text(encoding="utf-8"), filename=str(DECISION_FILE))
    forbidden_defs = {"target_weights", "map_weights", "compute_target_weights"}
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden_defs:
            found.append(node.name)
    assert found == [], f"decision.py must not define weight APIs: {found}"


def test_decision_result_annotation_has_no_weights() -> None:
    src = DECISION_FILE.read_text(encoding="utf-8")
    # Soft lock: DecisionResult docstring / fields stay scores + ranked only.
    assert "class DecisionResult" in src
    assert "scores:" in src
    assert "ranked:" in src
    assert "weights:" not in src.split("class DecisionResult", 1)[1].split("class ", 1)[0]
