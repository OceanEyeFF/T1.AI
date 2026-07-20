"""Knife-2 white-box: Decision → WeightMapper → DecisionStrategy → BacktestEngine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_exec import (
    DecisionContext,
    DecisionResult,
    MLStubDecision,
    MomentumDecision,
    MomentumTopNStrategy,
    WeightMapper,
    as_strategy,
)
from ashare_infra.sim.engine import BacktestConfig, BacktestEngine


def _ohlcv(close: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": [1_000_000.0] * len(close),
        },
        index=pd.date_range(start, periods=len(close), freq="B"),
    )


def _synthetic_universe(n: int = 80) -> dict[str, pd.DataFrame]:
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    return {
        "600000": pd.DataFrame(
            {
                "open": np.linspace(10.0, 12.0, n),
                "high": np.linspace(10.2, 12.2, n),
                "low": np.linspace(9.8, 11.8, n),
                "close": np.linspace(10.0, 12.0, n),
                "volume": np.full(n, 1_000_000.0),
            },
            index=idx,
        ),
        "000001": pd.DataFrame(
            {
                "open": np.linspace(20.0, 18.0, n),
                "high": np.linspace(20.2, 18.2, n),
                "low": np.linspace(19.8, 17.8, n),
                "close": np.linspace(20.0, 18.0, n),
                "volume": np.full(n, 1_000_000.0),
            },
            index=idx,
        ),
    }


def test_momentum_decision_scores_only() -> None:
    history = {
        "A": _ohlcv([10, 10, 11, 12]),
        "B": _ohlcv([10, 10, 10, 10]),
        "C": pd.DataFrame({"open": [1, 2, 3, 4]}),
    }
    result = MomentumDecision(lookback=2, min_history=4).decide(
        DecisionContext(today=pd.Timestamp("2024-03-15"), history=history)
    )
    assert set(result.scores) == {"A", "B"}
    assert result.ranked[0][0] == "A"
    assert not hasattr(result, "weights")
    assert isinstance(result, DecisionResult)


def test_weight_mapper_equal_top_n() -> None:
    mapper = WeightMapper(top_n=2)
    w = mapper.map_weights([("A", 0.9), ("B", 0.5), ("C", 0.1)])
    assert set(w.keys()) == {"A", "B"}
    assert w["A"] == pytest.approx(0.5)
    assert w["B"] == pytest.approx(0.5)
    assert mapper.map_weights([]) == {}


def test_momentum_top_n_uses_shared_seam() -> None:
    """MomentumTopNStrategy must delegate to DecisionStrategy (no weight bypass)."""
    strat = MomentumTopNStrategy(top_n=2, lookback=2, min_history=4)
    adapter = strat._adapter
    assert isinstance(adapter.decision, MomentumDecision)
    assert isinstance(adapter.mapper, WeightMapper)
    assert adapter.mapper.top_n == 2


def test_mechanical_and_ml_stub_share_adapt_path() -> None:
    history = {
        "A": _ohlcv([10, 10, 11, 12]),
        "B": _ohlcv([10, 10, 10, 10]),
        "C": _ohlcv([10, 11, 12, 13]),
    }
    today = pd.Timestamp("2024-03-15")
    mapper = WeightMapper(top_n=2)

    mech = as_strategy(MomentumDecision(lookback=2, min_history=4), mapper)
    stub = as_strategy(
        MLStubDecision(model_scores={"A": 0.1, "B": 0.9, "C": 0.5}),
        mapper,
    )

    w_mech = mech.target_weights(today, history)
    w_stub = stub.target_weights(today, history)

    assert set(w_mech.keys()) == {"A", "C"}  # A higher momentum than B; C highest
    assert set(w_stub.keys()) == {"B", "C"}  # stub ranks B > C > A
    assert sum(w_mech.values()) == pytest.approx(1.0)
    assert sum(w_stub.values()) == pytest.approx(1.0)


def test_ml_stub_accepts_int_symbol_keys() -> None:
    history = {"600000": _ohlcv([10.0] * 5)}
    result = MLStubDecision(model_scores={600000: 0.9}).decide(
        DecisionContext(today=pd.Timestamp("2024-01-10"), history=history)
    )
    assert result.scores == {"600000": pytest.approx(0.9)}
    assert result.ranked[0][0] == "600000"


def test_ml_stub_zero_pads_short_numeric_keys() -> None:
    """``1`` / ``"1"`` must match history key ``"000001"`` (lake.meta parity)."""
    history = {"000001": _ohlcv([10.0] * 5)}
    for key in (1, 1.0, "1"):
        result = MLStubDecision(model_scores={key: 0.8}).decide(
            DecisionContext(today=pd.Timestamp("2024-01-10"), history=history)
        )
        assert result.scores == {"000001": pytest.approx(0.8)}, f"failed for key={key!r}"


def test_ml_stub_strips_ts_code_suffix() -> None:
    history = {"600000": _ohlcv([10.0] * 5)}
    result = MLStubDecision(model_scores={"600000.SH": 0.6}).decide(
        DecisionContext(today=pd.Timestamp("2024-01-10"), history=history)
    )
    assert result.scores == {"600000": pytest.approx(0.6)}


def test_ml_stub_accepts_integral_float_symbol_keys() -> None:
    """``600000.0`` must normalize to ``"600000"`` (not ``"600000.0"``)."""
    history = {"600000": _ohlcv([10.0] * 5)}
    result = MLStubDecision(model_scores={600000.0: 0.7}).decide(
        DecisionContext(today=pd.Timestamp("2024-01-10"), history=history)
    )
    assert result.scores == {"600000": pytest.approx(0.7)}


def test_ml_stub_drops_non_finite_scores() -> None:
    """NaN/Inf stub scores must be dropped (parity with MomentumDecision)."""
    history = {"A": _ohlcv([10.0] * 5), "B": _ohlcv([10.0] * 5), "C": _ohlcv([10.0] * 5)}
    result = MLStubDecision(
        model_scores={"A": float("nan"), "B": float("inf"), "C": 0.3}
    ).decide(DecisionContext(today=pd.Timestamp("2024-01-10"), history=history))
    assert result.scores == {"C": pytest.approx(0.3)}
    assert [s for s, _ in result.ranked] == ["C"]


def test_ml_stub_nan_override_removes_prior_score() -> None:
    """A later NaN override invalidates an earlier finite score for that symbol."""
    history = {"A": _ohlcv([10.0] * 5), "B": _ohlcv([10.0] * 5)}
    stub = as_strategy(
        MLStubDecision(model_scores={"A": 1.0, "B": 0.5}),
        WeightMapper(top_n=2),
        extras={"model_scores": {"A": float("nan")}},
    )
    w = stub.target_weights(pd.Timestamp("2024-01-10"), history)
    assert set(w.keys()) == {"B"}


def test_ml_stub_extras_override_scores() -> None:
    history = {"A": _ohlcv([10] * 5), "B": _ohlcv([10] * 5)}
    stub = as_strategy(
        MLStubDecision(model_scores={"A": 1.0, "B": 0.0}),
        WeightMapper(top_n=1),
    )
    w_construction = stub.target_weights(pd.Timestamp("2024-01-10"), history)
    assert list(w_construction.keys()) == ["A"]

    stub_extra = as_strategy(
        MLStubDecision(),
        WeightMapper(top_n=1),
        extras={"model_scores": {"A": -1.0, "B": 2.0}},
    )
    w = stub_extra.target_weights(pd.Timestamp("2024-01-10"), history)
    assert list(w.keys()) == ["B"]


def test_backtest_engine_mechanical_via_seam() -> None:
    data = _synthetic_universe()
    engine = BacktestEngine(BacktestConfig(initial_cash=100_000.0, lot_size=100))
    strategy = as_strategy(
        MomentumDecision(lookback=5, min_history=20),
        WeightMapper(top_n=1),
    )
    result = engine.run(data, strategy=strategy)
    assert not result.equity_curve.empty
    assert result.stats["final_equity"] > 0


def test_backtest_engine_ml_stub_via_same_seam() -> None:
    data = _synthetic_universe()
    engine = BacktestEngine(BacktestConfig(initial_cash=100_000.0, lot_size=100))
    strategy = as_strategy(
        MLStubDecision(model_scores={"600000": 1.0, "000001": -1.0}),
        WeightMapper(top_n=1),
    )
    result = engine.run(data, strategy=strategy)
    assert not result.equity_curve.empty
    assert result.stats["final_equity"] > 0


def test_decision_result_has_no_weights_field() -> None:
    fields = set(DecisionResult.__dataclass_fields__)
    assert "weights" not in fields
    assert fields == {"scores", "ranked"}
