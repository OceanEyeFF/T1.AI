import numpy as np
import pandas as pd

from ashare_exec.weight_mapper import WeightMapper
from ashare_infra.sim.engine import BacktestConfig, BacktestEngine
from ashare_lab.labels.multi_horizon import MultiHorizonLabel
from ashare_lab.research_baseline import LABELS, ReplayRanking, frozen_split, make_timing


def test_short_suspension_masks_label_without_sliding_trading_entry():
    sessions = pd.bdate_range("2026-02-02", periods=14)
    prices = pd.DataFrame({"open": np.arange(20.0, 34), "volume": 1000.0}, index=sessions)
    suspended = prices.drop(index=sessions[5])
    calculator = MultiHorizonLabel(horizons=[3], label_mode="next_open_to_open")
    result = calculator.compute(suspended, sessions=sessions)
    assert pd.isna(result.loc[sessions[1], "label_3d"])
    assert pd.isna(result.loc[sessions[4], "label_3d"])
    assert result.loc[sessions[6], "label_3d"] == prices.iloc[10].open / prices.iloc[7].open - 1
    assert pd.isna(result.iloc[-1].label_3d)


def test_signal_and_training_freeze_use_actual_trading_sessions():
    sessions = pd.bdate_range("2026-01-05", periods=90).delete(10)
    timing = make_timing(sessions)
    monday = timing.loc["2026-01-12"]
    assert monday.bar_available_at.isoformat() == "2026-01-10T14:30:00+08:00"
    assert monday.signal_at.isoformat() == "2026-01-12T15:00:00+08:00"
    assert monday.entry_at.isoformat() == "2026-01-13T09:30:00+08:00"
    after = sessions[58]
    panel = timing.assign(**dict.fromkeys(LABELS, 0.01)).reset_index()
    train, valid, test, freeze = frozen_split(panel, sessions, after, 16)
    assert panel.loc[train, "label_10d_available_at"].max() < panel.loc[valid, "signal_at"].min()
    assert panel.loc[valid, "label_10d_available_at"].max() <= freeze
    assert panel.loc[test, "date"].min() == sessions[59]


def test_hold_policy_receives_filled_lots_and_can_skip_missing_signal():
    dates = pd.bdate_range("2026-08-14", periods=5)
    bars = pd.DataFrame({"open": 10.0, "close": 10.0, "pre_close": 10.0}, index=dates)
    rankings = {dates[1]: [("A", 1.0)], dates[2]: [("B", 2.0), ("A", 1.0)]}
    engine = BacktestEngine(BacktestConfig(initial_cash=10_000))
    market = {"A": bars, "B": bars}
    fixed = engine.run(market, ReplayRanking(rankings, WeightMapper(top_n=1)))
    aware = engine.run(market, ReplayRanking(rankings, WeightMapper(top_n=1, retention_rank=2)))
    assert fixed.fills[["symbol", "side"]].values.tolist() == [
        ["A", "BUY"],
        ["A", "SELL"],
        ["B", "BUY"],
    ]
    assert aware.fills[["symbol", "side"]].values.tolist() == [["A", "BUY"]]
