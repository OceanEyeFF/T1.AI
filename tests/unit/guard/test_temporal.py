"""U-G7: truncate_as_of unit tests."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ashare_infra.guard.temporal import truncate_as_of


def _frame() -> pd.DataFrame:
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    return pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0]}, index=idx)


def test_truncate_as_of_inclusive() -> None:
    out = truncate_as_of(_frame(), date(2024, 1, 3), inclusive=True)
    assert list(out.index.date) == [date(2024, 1, 2), date(2024, 1, 3)]


def test_truncate_as_of_exclusive() -> None:
    out = truncate_as_of(_frame(), date(2024, 1, 3), inclusive=False)
    assert list(out.index.date) == [date(2024, 1, 2)]


def test_truncate_as_of_empty() -> None:
    empty = pd.DataFrame(columns=["close"])
    out = truncate_as_of(empty, date(2024, 1, 3))
    assert out.empty


def test_truncate_as_of_date_column() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-05"]),
            "close": [1.0, 2.0],
        }
    )
    out = truncate_as_of(df, date(2024, 1, 3))
    assert len(out) == 1
    assert float(out.iloc[0]["close"]) == 1.0


def test_truncate_as_of_requires_index_or_date_col() -> None:
    df = pd.DataFrame({"close": [1.0]}, index=[0])
    with pytest.raises(ValueError, match="DatetimeIndex"):
        truncate_as_of(df, date(2024, 1, 3))
