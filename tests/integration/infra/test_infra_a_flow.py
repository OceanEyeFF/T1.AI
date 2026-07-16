"""Infra A integration: DataLake + TestSession end-to-end on fixture pack."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.guard.fetch_gate import FetchGate, FetchRole, ScopeFrozenError
from ashare_infra.lake import DataLake
from ashare_infra.sim import LimitOrder, ReplayConfig, ScriptedPlanner, SimConfig
from ashare_infra.sim.session import TestSession
from tests.support import infra_a as fx


def test_i1_datalake_reads_seeded_akshare_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DataLake is the only entry; wrap load_or_fetch with seeded cache hits."""
    import ashare_infra.data.akshare_source as ak

    seeded = fx.seeded_cache_dir() / "akshare"

    def fake_load(req, cache_dir, refresh=False):
        _ = cache_dir, refresh
        path = seeded / f"{req.symbol}_daily_{req.adjust}_{req.start_date}_{req.end_date}.csv"
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
        return df

    monkeypatch.setattr(ak, "load_or_fetch_daily_bars", fake_load)
    lake = DataLake(cache_dir=tmp_path, default_source="akshare")
    scope = fx.make_scope(symbols={"600000", "000001"}, include_meta=False)
    bars = lake.load_scope_bars(scope)
    assert set(bars) == {"600000", "000001"}
    assert len(bars["600000"]) >= 5


def test_i2_sim_start_freezes_then_replay() -> None:
    scope = fx.make_sim_scope()
    gate = FetchGate(scope=scope)
    gate.sim_start()
    assert gate.scope.frozen
    with pytest.raises(ScopeFrozenError):
        gate.add_symbols({"600001"}, role=FetchRole.ROOT)

    session = TestSession(scope=gate.scope, gate=gate)
    data = fx.load_all_bars(list(gate.scope.symbols))
    # drop symbols with incomplete history for a clean buy/sell on 600000
    planner = ScriptedPlanner(
        {
            date(2024, 1, 3): [
                LimitOrder(symbol="600000", side="BUY", shares=100, limit_price=20.0)
            ],
            date(2024, 1, 5): [
                LimitOrder(symbol="600000", side="SELL", shares=100, limit_price=1.0)
            ],
        }
    )
    result = session.run_replay(
        data,
        planner,
    )
    assert result.diagnostics["days"] >= 5
    assert result.diagnostics["fills"] >= 1
    assert not result.equity_curve.empty


def test_i2b_missing_bar_reject_on_fixture_day() -> None:
    """Orders against an empty bar map on the missing-bar day → missing_bar reject."""
    from ashare_infra.sim import PaperBroker

    day = date.fromisoformat(fx.expected("missing_bar_day"))
    broker = PaperBroker(SimConfig(initial_cash=50_000, max_participation=1.0))
    broker.submit([LimitOrder(symbol="600003", side="BUY", shares=100, limit_price=50.0)])
    day_result = broker.match_day(day, {})
    assert day_result.rejects and day_result.rejects[0].reason == "missing_bar"


def test_i3_session_score_ic() -> None:
    preds, labels = fx.load_ic_panel()
    session = TestSession.for_ic({"600000", "000001", "600003"}, *fx.window())
    stats = session.score_ic(preds, labels)
    assert stats["n_days"] == int(fx.expected("ic_panel_n_days"))
    assert stats["mean_ic"] > 0.5


def test_c1_lab_shim_identity() -> None:
    from ashare_infra.sim import PaperBroker as InfraBroker
    from ashare_infra.sim import BacktestEngine as InfraEngine
    from ashare_lab.sim import PaperBroker as LabBroker
    from ashare_lab.backtest.engine import BacktestEngine as LabEngine
    from ashare_infra.guard.metrics import calculate_daily_cs_ic as infra_ic
    from ashare_lab.evaluation.metrics import calculate_daily_cs_ic as lab_ic

    assert LabBroker is InfraBroker
    assert LabEngine is InfraEngine
    assert lab_ic is infra_ic


def test_i4_stockpool_triggers_maintain(tmp_path: Path) -> None:
    """STOCKPOOL_REQUEST add_symbols → AUTO_MAINTAIN download (journal order)."""
    from ashare_infra.guard.fetch_gate import FetchRole

    harness = fx.build_smoke_harness(tmp_path, symbols={"600000"})
    harness.simulate_download()
    before = len(harness.journal)
    harness.simulate_add_stocks(["600001"], role=FetchRole.STOCKPOOL_REQUEST)
    events = harness.journal[before:]
    kinds = [e.kind for e in events]
    assert "add_symbols" in kinds
    assert "download" in kinds
    assert kinds.index("add_symbols") < kinds.index("download")
    assert "600001" in harness.scope.symbols
    assert (tmp_path / "smoke" / "600001.parquet").exists()


def test_i5_guard_sanity_on_infra_a_panel() -> None:
    from ashare_infra.guard.sanity import compute_baseline_ic, shuffle_test

    preds, labels = fx.load_ic_panel()
    baseline = compute_baseline_ic(preds, labels)
    assert baseline["mean_ic"] > 0.0
    shuffled = shuffle_test(preds, labels, n_trials=5, threshold=0.25, seed=7)
    assert abs(shuffled["mean_ic"]) < 0.25
    assert shuffled["pass"] is True


def test_c4_lab_universe_types_shim_identity() -> None:
    from ashare_infra.types import Fill as InfraFill
    from ashare_infra.types import Order as InfraOrder
    from ashare_infra.types import Side as InfraSide
    from ashare_infra.universe import is_allowed_a_share_symbol as infra_ok
    from ashare_lab.types import Fill as LabFill
    from ashare_lab.types import Order as LabOrder
    from ashare_lab.types import Side as LabSide
    from ashare_lab.universe import is_allowed_a_share_symbol as lab_ok

    assert lab_ok is infra_ok
    assert LabFill is InfraFill
    assert LabOrder is InfraOrder
    assert LabSide is InfraSide
    assert lab_ok("600000") is True
    assert lab_ok("688001") is False
