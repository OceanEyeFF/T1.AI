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


def test_i1_datalake_reads_seeded_tushare_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DataLake 是唯一入口；scope 层 bare symbols 经薄 shim 进入**真实**
    load_or_fetch_daily_bars 读写链路消费 seeded cache（D5：不再内联重实现读取）。"""
    import ashare_infra.data.tushare_source as ts
    from ashare_infra.data.tushare_source import TushareDailyBarsRequest

    seeded = fx.seeded_cache_dir()
    real_load = ts.load_or_fetch_daily_bars  # 在 patch 前捕获真实函数

    def boom(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = cache_dir, refresh
        raise AssertionError(f"unexpected fetch: {req.symbol!r}（seeded cache 应全命中）")

    def shim(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = cache_dir, refresh
        ts_code = f"{req.symbol}.{'SH' if req.symbol.startswith('6') else 'SZ'}"
        return real_load(
            TushareDailyBarsRequest(
                symbol=ts_code,
                start_date=req.start_date,
                end_date=req.end_date,
                adjust=req.adjust,
            ),
            seeded,
            refresh=refresh,
        )

    monkeypatch.setattr(ts, "load_or_fetch_daily_bars", shim)
    monkeypatch.setattr(ts, "fetch_tushare_daily_bars", boom)

    lake = DataLake(cache_dir=tmp_path, default_source="tushare")
    scope = fx.make_scope(symbols={"600000", "000001"}, include_meta=False)
    bars = lake.load_scope_bars(scope)
    assert set(bars) == {"600000", "000001"}
    assert len(bars["600000"]) >= 5


def test_i1b_weekend_gap_no_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """交易日缺口用例（D5）：真实 loader 读回后周末不得产生行。"""
    import ashare_infra.data.tushare_source as ts

    def boom(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = cache_dir, refresh
        raise AssertionError(f"unexpected fetch: {req.symbol!r}")

    monkeypatch.setattr(ts, "fetch_tushare_daily_bars", boom)
    lake = DataLake(cache_dir=fx.seeded_cache_dir(), default_source="tushare")
    bars = lake.load_daily_bars(
        "600000.SH", "2024-01-02", "2024-01-15", source="tushare", adjust="qfq"
    )
    assert len(bars) == 10, "fixture 应覆盖 manifest calendar 全部 10 个交易日"
    assert bars.index.is_monotonic_increasing
    for weekend in ("2024-01-06", "2024-01-07", "2024-01-13", "2024-01-14"):
        assert pd.Timestamp(weekend) not in bars.index, f"周末 {weekend} 不应有行情行"
    # 与 manifest calendar 一一对应（缺口即周末，无其他缺洞）
    expected_days = [pd.Timestamp(d) for d in fx.calendar()]
    assert list(bars.index.normalize()) == expected_days


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
