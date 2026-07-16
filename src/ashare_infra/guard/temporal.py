"""Temporal as-of truncation helpers."""

from __future__ import annotations

from datetime import date

import pandas as pd


def truncate_as_of(
    df: pd.DataFrame,
    as_of: date | pd.Timestamp,
    *,
    inclusive: bool = True,
) -> pd.DataFrame:
    """Return rows with index date <= (or <) ``as_of``.

    Expects a DatetimeIndex (or a ``date`` column that will be used as index).
    """
    if df.empty:
        return df.copy()

    work = df
    if not isinstance(work.index, pd.DatetimeIndex):
        if "date" in work.columns:
            work = work.set_index("date")
        else:
            raise ValueError("DataFrame must have DatetimeIndex or a 'date' column")
        work.index = pd.to_datetime(work.index)

    end = pd.Timestamp(as_of)
    if inclusive:
        return work.loc[:end].copy()
    return work.loc[work.index < end].copy()
