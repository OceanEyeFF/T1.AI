"""Trading calendar helpers (skeleton — exchange calendar wiring later)."""

from __future__ import annotations

from datetime import date

import pandas as pd


def build_union_calendar(data_by_symbol: dict[str, pd.DataFrame]) -> list[date]:
    """Union of all dates present in symbol frames (same semantics as sim.replay)."""
    dates: set[date] = set()
    for df in data_by_symbol.values():
        for ts in pd.DatetimeIndex(df.index):
            dates.add(pd.Timestamp(ts).date())
    return sorted(dates)


def filter_calendar_to_window(
    calendar: list[date],
    window_start: date,
    window_end: date,
) -> list[date]:
    return [d for d in calendar if window_start <= d <= window_end]
