"""U-G8: ReturnConvention + period_return on Infra A bars."""

from __future__ import annotations

from datetime import date

import math

import pytest

from ashare_infra.guard.execution import (
    DEFAULT_IC_CONVENTION,
    DEFAULT_SIM_CONVENTION,
    ReturnConvention,
    period_return,
)
from tests.support import infra_a as fx


def test_convention_values_match_validator_literals() -> None:
    assert ReturnConvention.CLOSE_TO_CLOSE.value == "close_to_close"
    assert ReturnConvention.NEXT_OPEN_TO_OPEN.value == "next_open_to_open"
    assert DEFAULT_IC_CONVENTION is ReturnConvention.CLOSE_TO_CLOSE
    assert DEFAULT_SIM_CONVENTION is ReturnConvention.CLOSE_TO_CLOSE


def test_close_to_close_on_fixture_bars() -> None:
    bars = fx.load_bars("600000")
    # 2024-01-02 close=10.0 → 2024-01-04 close=10.0 → ret=0
    ret = period_return(
        bars,
        date(2024, 1, 2),
        date(2024, 1, 4),
        ReturnConvention.CLOSE_TO_CLOSE,
    )
    assert ret == pytest.approx(0.0)


def test_next_open_to_open_on_fixture_bars() -> None:
    bars = fx.load_bars("600000")
    # next(2024-01-02)=01-03 open=10.01; next(2024-01-03)=01-04 open=9.91
    ret = period_return(
        bars,
        date(2024, 1, 2),
        date(2024, 1, 3),
        ReturnConvention.NEXT_OPEN_TO_OPEN,
    )
    assert ret == pytest.approx(9.91 / 10.01 - 1.0)


def test_missing_anchor_returns_nan() -> None:
    bars = fx.load_bars("600000")
    ret = period_return(
        bars,
        date(2023, 12, 1),
        date(2024, 1, 4),
        ReturnConvention.CLOSE_TO_CLOSE,
    )
    assert math.isnan(ret)


def test_period_return_empty_bars_is_nan() -> None:
    import pandas as pd

    ret = period_return(
        pd.DataFrame(),
        date(2024, 1, 2),
        date(2024, 1, 3),
        ReturnConvention.CLOSE_TO_CLOSE,
    )
    assert math.isnan(ret)


def test_period_return_date_column_index() -> None:
    import pandas as pd

    bars = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "close": [10.0, 11.0],
            "open": [10.0, 10.5],
        }
    )
    ret = period_return(
        bars,
        date(2024, 1, 2),
        date(2024, 1, 3),
        ReturnConvention.CLOSE_TO_CLOSE,
    )
    assert ret == pytest.approx(0.1)


def test_period_return_zero_start_price_is_nan() -> None:
    import pandas as pd

    bars = pd.DataFrame(
        {"close": [0.0, 11.0], "open": [0.0, 10.5]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )
    ret = period_return(
        bars,
        date(2024, 1, 2),
        date(2024, 1, 3),
        ReturnConvention.CLOSE_TO_CLOSE,
    )
    assert math.isnan(ret)
