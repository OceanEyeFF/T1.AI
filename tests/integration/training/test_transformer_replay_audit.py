import numpy as np
import pandas as pd
import pytest

from scripts.audit_ashare_transformer_replay import INITIAL_CASH, boundary, value_book


def test_boundary_reports_membership_switch_and_exact_cutoff_ties():
    symbols = [f"S{i:02}" for i in range(1, 17)]
    score = list(range(16, 0, -1))
    score[10] = score[9]
    score[15] = score[14]
    date = pd.Timestamp("2026-11-06")
    before = pd.DataFrame({"score": score, "date": date, "segment": "scored"}, index=symbols)
    after = before.iloc[[*range(9), 10, 9, *range(11, 16)]]
    result = boundary(date, before, after)
    assert result["top10_entries"] == "S11"
    assert result["top10_exits"] == "S10"
    assert result["top10_gap_short"] == result["top10_gap_long"] == 0
    assert result["top10_ties_short"] == result["top10_ties_long"] == "S10|S11"
    assert result["top15_ties_short"] == "S15|S16"
    assert result["top15_replacements"] == 0


def test_replay_attribution_reconciles_carry_fills_and_fees():
    dates = pd.date_range("2026-11-04", periods=3)
    bars = pd.DataFrame({"A": [10, 11, 13]}, index=dates)
    positions = pd.DataFrame({"A": [0, 100, 0]}, index=dates)
    fills = pd.DataFrame(
        {
            "date": dates[1:],
            "symbol": "A",
            "side": ["BUY", "SELL"],
            "shares": 100,
            "price": [10, 12],
            "cost": 5,
        }
    )
    equity = pd.DataFrame(
        {
            "cash": INITIAL_CASH + np.array([0, -1005, 190]),
            "equity": INITIAL_CASH + np.array([0, 95, 190]),
        },
        index=dates,
    )
    ledger = value_book(positions, fills, bars, equity)
    assert ledger["old_shares_pnl"].A.tolist() == [0, 0, 200]
    assert ledger["fill_mark_pnl"].A.tolist() == [0, 100, -100]
    assert ledger["fees"].A.tolist() == [0, 5, 5]
    assert ledger["net_pnl"].A.tolist() == [0, 95, 95]
    with pytest.raises(AssertionError):
        value_book(positions, fills, bars, equity.assign(cash=equity.cash + 1))
