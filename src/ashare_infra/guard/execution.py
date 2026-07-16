"""Return / execution convention helpers."""

from __future__ import annotations

from datetime import date
from enum import Enum

import pandas as pd


class ReturnConvention(str, Enum):
    """Label / evaluation return construction convention."""

    CLOSE_TO_CLOSE = "close_to_close"
    NEXT_OPEN_TO_OPEN = "next_open_to_open"


DEFAULT_IC_CONVENTION = ReturnConvention.CLOSE_TO_CLOSE
DEFAULT_SIM_CONVENTION = ReturnConvention.CLOSE_TO_CLOSE


def _as_ts(value: date | pd.Timestamp | str) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def _next_trade_day(index: pd.DatetimeIndex, day: pd.Timestamp) -> pd.Timestamp | None:
    """First index date strictly after ``day`` (validator calendar-anchor semantics)."""
    later = index[index > day]
    if len(later) == 0:
        return None
    return pd.Timestamp(later[0]).normalize()


def period_return(
    bars: pd.DataFrame,
    start: date | pd.Timestamp | str,
    end: date | pd.Timestamp | str,
    convention: ReturnConvention | str = DEFAULT_IC_CONVENTION,
) -> float:
    """Period return on OHLC bars under ``ReturnConvention``.

    Mirrors ``recommendation.validator`` price anchors:
    - ``close_to_close``: close(end) / close(start) - 1
    - ``next_open_to_open``: open(next(start)) / open(next(end)) - 1
      where next(d) is the first trade day in ``bars`` strictly after d.

    Missing anchors or zero/NaN start price → NaN.
    """
    if isinstance(convention, str):
        convention = ReturnConvention(convention)
    if bars.empty:
        return float("nan")

    work = bars
    if not isinstance(work.index, pd.DatetimeIndex):
        if "date" in work.columns:
            work = work.set_index("date")
        else:
            raise ValueError("bars must have DatetimeIndex or a 'date' column")
    work = work.sort_index()
    work.index = pd.DatetimeIndex(work.index).normalize()
    start_ts, end_ts = _as_ts(start), _as_ts(end)

    if convention is ReturnConvention.CLOSE_TO_CLOSE:
        if start_ts not in work.index or end_ts not in work.index:
            return float("nan")
        start_px = float(work.loc[start_ts, "close"])
        end_px = float(work.loc[end_ts, "close"])
    else:
        trade_dates = pd.DatetimeIndex(work.index).sort_values()
        start_anchor = _next_trade_day(trade_dates, start_ts)
        end_anchor = _next_trade_day(trade_dates, end_ts)
        if start_anchor is None or end_anchor is None:
            return float("nan")
        if start_anchor not in work.index or end_anchor not in work.index:
            return float("nan")
        start_px = float(work.loc[start_anchor, "open"])
        end_px = float(work.loc[end_anchor, "open"])

    if start_px == 0.0 or start_px != start_px or end_px != end_px:
        return float("nan")
    return float(end_px / start_px - 1.0)
