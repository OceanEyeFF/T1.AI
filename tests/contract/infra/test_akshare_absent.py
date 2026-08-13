"""akshare 单一信源收敛的负向合同：全库无 akshare 运行时表面。

覆盖双路 CodeReview P1：
- SourceKind 精确取值（lake / builder）
- akshare 模块不存在（importlib 探测）
- recommendation 不导出 AkshareSourceAdapter（惰性导出 AttributeError）
- src/ + scripts/ 全树 AST 扫描：无 akshare import
- 依赖清单（pyproject / requirements*）无 akshare
"""

from __future__ import annotations

import ast
import importlib.util
import tomllib
from pathlib import Path
from typing import get_args

import pytest

from ashare_infra.lake import SourceKind as LakeSourceKind
from ashare_lab.dataset.builder import SourceKind as BuilderSourceKind
from tests.support.paths import REPO_ROOT


@pytest.mark.contract
def test_source_kind_surfaces_exact() -> None:
    assert set(get_args(LakeSourceKind)) == {"tushare", "odp", "smoke"}
    assert set(get_args(BuilderSourceKind)) == {"tushare", "odp"}


@pytest.mark.contract
def test_akshare_modules_do_not_exist() -> None:
    assert importlib.util.find_spec("ashare_infra.data.akshare_source") is None
    assert importlib.util.find_spec("ashare_lab.data.akshare_source") is None


@pytest.mark.contract
def test_recommendation_does_not_export_akshare_adapter() -> None:
    import ashare_lab.recommendation as rec

    assert "AkshareSourceAdapter" not in rec.__all__
    with pytest.raises(AttributeError):
        getattr(rec, "AkshareSourceAdapter")


def _py_files() -> list[Path]:
    return [
        *sorted(REPO_ROOT.glob("src/**/*.py")),
        *sorted(REPO_ROOT.glob("scripts/**/*.py")),
    ]


@pytest.mark.contract
def test_no_akshare_imports_in_source_tree() -> None:
    offenders: list[str] = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                if "akshare" in name.lower():
                    offenders.append(f"{path}: {name}")
    assert offenders == []


@pytest.mark.contract
def test_no_akshare_dependency_in_manifests() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps: list[str] = []
    proj = pyproject.get("project") or {}
    deps += list(proj.get("dependencies") or [])
    for group in (proj.get("optional-dependencies") or {}).values():
        deps += list(group)
    assert not any("akshare" in d.lower() for d in deps), deps

    for name in ("requirements.txt", "requirements-dev.txt"):
        path = REPO_ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "akshare" in stripped.lower():
                pytest.fail(f"{name} contains akshare: {stripped}")
