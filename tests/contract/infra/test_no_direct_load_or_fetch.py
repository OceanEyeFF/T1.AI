"""AO-O4-A (post-A4): static Import/ImportFrom scan for load_or_fetch*.

Tier A = static ``ast.Import`` / ``ast.ImportFrom`` only. Dynamic bypasses
(``getattr``, ``importlib``, ``__import__``, string-based attribute access)
are intentionally **not** detected here; that remains deferred beyond AO-O4-A.

Only modules under ``ashare_infra.lake*`` may import ``load_or_fetch*``.
Full-tree scan covers ``src/ashare_lab/**/*.py`` and ``scripts/**/*.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

SCAN_ROOTS = (
    REPO_ROOT / "src/ashare_lab",
    REPO_ROOT / "scripts",
)

# Historical Phase-2 / WT-INFRA-002 surfaces — still asserted zero-forbidden.
LEGACY_SCAN_TARGETS = (
    REPO_ROOT / "src/ashare_lab/recommendation/validator.py",
    REPO_ROOT / "src/ashare_lab/dataset/builder.py",
    REPO_ROOT / "scripts/run_sim_replay.py",
    REPO_ROOT / "scripts/run_backtest.py",
    REPO_ROOT / "scripts/generate_daily_recommendations.py",
    REPO_ROOT / "scripts/build_sequence_dataset.py",
)

# Deferred: needs DataLake APIs for daily_basic / moneyflow / ODP historical.
# Skipped from hard-fail full-tree check; documented + intentional-import tests.
ALLOWLISTED_DEFERRED_PATHS = frozenset(
    {
        REPO_ROOT / "scripts/build_sequence_dataset_market_state.py",
    }
)

ALLOWED_PREFIXES = (
    "ashare_infra.lake",
)


def _iter_scan_py_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        assert root.is_dir(), f"missing scan root: {root}"
        files.extend(sorted(p for p in root.rglob("*.py") if p.is_file()))
    return files


def _imported_load_or_fetch_names(path: Path) -> list[str]:
    """Return forbidden load_or_fetch* import specs (static Import/ImportFrom only)."""
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


def _any_load_or_fetch_import(path: Path) -> list[str]:
    """All load_or_fetch* Import/ImportFrom names (allowed or not)."""
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
                    hits.append(f"{mod}.{name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "load_or_fetch" in alias.name:
                    hits.append(alias.name)
    return hits


def _called_load_or_fetch_names(path: Path) -> list[str]:
    """别名旁路检测：``import x as y; y.load_or_fetch_*()`` 级别的直接调用。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                module_aliases[alias.asname or alias.name] = f"{mod}.{alias.name}"

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr.startswith("load_or_fetch"):
            if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
                target = module_aliases[func.value.id]
                if not any(target.startswith(p) for p in ALLOWED_PREFIXES):
                    hits.append(f"{target} (via {func.value.id}.{func.attr})")
    return hits


def _called_load_or_fetch_from_text(source: str) -> list[str]:
    """测试辅助：对源码片段执行同一扫描（用于锁死扫描器自身行为）。"""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(source)
        tmp = Path(fh.name)
    try:
        return _called_load_or_fetch_names(tmp)
    finally:
        tmp.unlink()


@pytest.mark.parametrize("path", LEGACY_SCAN_TARGETS, ids=lambda p: p.name)
def test_legacy_scan_targets_zero_forbidden(path: Path) -> None:
    """Regression: old SCAN_TARGETS still have zero forbidden imports."""
    assert path.is_file(), f"missing legacy scan target: {path}"
    assert path in _iter_scan_py_files()
    hits = _imported_load_or_fetch_names(path)
    assert hits == [], f"{path.name} still imports load_or_fetch_*: {hits}"


@pytest.mark.parametrize(
    "path", sorted(ALLOWLISTED_DEFERRED_PATHS), ids=lambda p: p.name
)
def test_deferred_allowlisted_paths_exist_and_import_load_or_fetch(path: Path) -> None:
    """Allowlist is intentional: file exists and still imports load_or_fetch*."""
    assert path.is_file(), f"missing deferred allowlisted path: {path}"
    hits = _any_load_or_fetch_import(path)
    assert hits, f"{path.name} is allowlisted but has no load_or_fetch import"


def test_deferred_allowlist_is_exactly_known_offender() -> None:
    """Only the documented deferred script is allowlisted under scan roots."""
    assert len(ALLOWLISTED_DEFERRED_PATHS) == 1
    only = next(iter(ALLOWLISTED_DEFERRED_PATHS))
    assert only.name == "build_sequence_dataset_market_state.py"
    assert only.is_file()


def test_full_tree_no_forbidden_load_or_fetch_outside_deferred() -> None:
    """Every *.py under ashare_lab/ + scripts/ is clean except deferred allowlist."""
    offenders: list[str] = []
    for path in _iter_scan_py_files():
        if path in ALLOWLISTED_DEFERRED_PATHS:
            continue
        hits = _imported_load_or_fetch_names(path)
        if hits:
            offenders.append(f"{path.relative_to(REPO_ROOT)}: {hits}")
    assert offenders == [], "forbidden load_or_fetch* imports:\n" + "\n".join(offenders)


def test_deferred_allowlist_covers_all_current_offenders() -> None:
    """No surprise offenders outside ALLOWLISTED_DEFERRED_PATHS."""
    found: list[Path] = []
    for path in _iter_scan_py_files():
        if _imported_load_or_fetch_names(path):
            found.append(path)
    assert set(found) == set(ALLOWLISTED_DEFERRED_PATHS), (
        f"unexpected offenders={found}; allowlist={sorted(ALLOWLISTED_DEFERRED_PATHS)}"
    )


def test_scanner_detects_module_alias_bypass() -> None:
    """锁死扫描器自身行为：import 别名直调 load_or_fetch 必须被抓到。"""
    hits = _called_load_or_fetch_from_text(
        "import ashare_lab.data.tushare_source as ts\n"
        "def f(req, cache):\n"
        "    return ts.load_or_fetch_daily_bars(req, cache)\n"
    )
    assert hits == ["ashare_lab.data.tushare_source (via ts.load_or_fetch_daily_bars)"]


def test_scanner_ignores_allowed_prefix_and_non_calls() -> None:
    """ashare_infra.lake 前缀的别名调用豁免；普通属性访问不误报。"""
    hits = _called_load_or_fetch_from_text(
        "import ashare_infra.lake as lk\n"
        "def f(req, cache):\n"
        "    return lk.load_or_fetch_daily_bars(req, cache)\n"
        "def g(x):\n"
        "    return x.load_or_fetch_daily_bars\n"  # 非调用，不应命中
    )
    assert hits == []


@pytest.mark.parametrize("path", _iter_scan_py_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_full_tree_zero_alias_bypass_calls(path: Path) -> None:
    hits = _called_load_or_fetch_names(path)
    assert hits == [], f"{path} 通过别名直调 load_or_fetch*: {hits}"
