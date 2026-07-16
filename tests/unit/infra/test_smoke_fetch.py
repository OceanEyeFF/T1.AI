"""Smoke fetch: simulate download / add stocks / set start (no network)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ashare_infra.guard.fetch_gate import FetchRole, ScopeFrozenError
from ashare_infra.lake.smoke import SmokeCatalog, SmokeHarness
from tests.support import infra_a as fx


@pytest.fixture
def harness(tmp_path: Path) -> SmokeHarness:
    catalog = SmokeCatalog.from_frames(fx.load_all_bars())
    scope = fx.make_scope(symbols={"600000"}, include_meta=False)
    return SmokeHarness.create(scope, catalog, cache_dir=tmp_path)


def test_simulate_download_materializes_cache(harness: SmokeHarness) -> None:
    rows = harness.simulate_download()
    assert rows["600000"] > 0
    assert (harness.backend.cache_path("600000")).exists()
    bars = harness.load_scope_bars()
    assert "600000" in bars
    assert len(bars["600000"]) == rows["600000"]
    assert any(e.kind == "download" for e in harness.journal)


def test_simulate_add_stocks_then_download(harness: SmokeHarness) -> None:
    harness.simulate_download()
    harness.simulate_add_stocks(["000001", "600001"])
    assert harness.scope.symbols >= frozenset({"600000", "000001", "600001"})
    bars = harness.load_scope_bars()
    assert set(bars) >= {"600000", "000001", "600001"}
    kinds = [e.kind for e in harness.journal]
    assert "add_symbols" in kinds
    assert kinds.count("download") >= 2


def test_simulate_set_start_shrinks_window(harness: SmokeHarness) -> None:
    harness.simulate_download()
    n_full = len(harness.load_scope_bars()["600000"])
    harness.simulate_set_start(date(2024, 1, 8))
    assert harness.scope.window_start == date(2024, 1, 8)
    n_short = len(harness.load_scope_bars()["600000"])
    assert n_short < n_full
    assert any(e.kind == "set_start" for e in harness.journal)


def test_simulate_set_window_root_only(harness: SmokeHarness) -> None:
    from ashare_infra.guard.fetch_gate import RolePermissionError

    with pytest.raises(RolePermissionError):
        harness.simulate_set_window(
            date(2024, 1, 2),
            date(2024, 1, 10),
            role=FetchRole.AUTO_MAINTAIN,
        )


def test_simulate_sim_start_freezes(harness: SmokeHarness) -> None:
    harness.simulate_download()
    harness.simulate_sim_start()
    assert harness.scope.frozen
    with pytest.raises(ScopeFrozenError):
        harness.simulate_add_stocks(["000001"])


def test_smoke_report_shape(harness: SmokeHarness) -> None:
    harness.simulate_download()
    harness.simulate_add_stocks(["000001"])
    report = harness.report()
    assert report["symbols"] == sorted(harness.scope.symbols)
    assert isinstance(report["events"], list)
    assert "000001" in report["cached_symbols"]


def test_cli_default_scenario(tmp_path: Path) -> None:
    report = fx.run_smoke_scenario(tmp_path)
    assert report["frozen"] is True
    assert "600001" in report["symbols"]
    assert report["window_start"] == "2024-01-05"
    step_names = [s["step"] for s in report["scenario_steps"]]
    assert step_names == [
        "download",
        "add_stocks",
        "set_start",
        "load_scope_bars",
        "sim_start",
    ]
