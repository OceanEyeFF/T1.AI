import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.build_sequence_dataset import _split_by_fixed_weeks, _split_by_ratio


def test_split_by_fixed_weeks_uses_latest_weeks_for_test() -> None:
    dates = pd.Series(pd.bdate_range("2024-01-02", periods=200))
    m_train, m_valid, m_test, cfg = _split_by_fixed_weeks(dates, valid_weeks=8, test_weeks=8)

    assert cfg["method"] == "fixed_weeks"
    assert int(m_train.sum()) > 0
    assert int(m_valid.sum()) > 0
    assert int(m_test.sum()) > 0

    week_periods = dates.dt.to_period("W-FRI")
    test_weeks = sorted(pd.unique(week_periods[m_test]))
    all_weeks = sorted(pd.unique(week_periods))
    assert test_weeks == all_weeks[-8:]


def test_split_by_fixed_weeks_requires_enough_history() -> None:
    dates = pd.Series(pd.bdate_range("2024-01-02", periods=20))
    with pytest.raises(ValueError):
        _split_by_fixed_weeks(dates, valid_weeks=8, test_weeks=8)


def test_split_by_ratio_back_compat_path() -> None:
    dates = pd.Series(pd.bdate_range("2024-01-02", periods=100))
    m_train, m_valid, m_test, cfg = _split_by_ratio(dates, train_ratio=0.7, valid_ratio=0.2)
    assert cfg["method"] == "ratio"
    assert int(m_train.sum()) > 0
    assert int(m_valid.sum()) > 0
    assert int(m_test.sum()) > 0
    assert int(m_train.sum()) + int(m_valid.sum()) + int(m_test.sum()) == len(dates)
