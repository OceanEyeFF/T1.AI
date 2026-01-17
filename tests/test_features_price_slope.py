"""测试价格斜率特征"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.features.price_slope import PriceSlope


@pytest.fixture
def exp_trend_data() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    # 构造指数增长序列，使 log(close) 线性，理论斜率=0.01
    t = np.arange(40)
    close = np.exp(0.01 * t) * 100
    return pd.DataFrame({"close": close, "volume": 1_000_000}, index=dates)


def test_price_slope_value(exp_trend_data: pd.DataFrame) -> None:
    feature = PriceSlope(window=5)
    result = feature.compute(exp_trend_data)

    # 理论斜率约等于 0.01
    idx = result.index[20]
    assert np.isclose(result.loc[idx], 0.01, atol=1e-4)


def test_price_slope_missing_column() -> None:
    feature = PriceSlope(window=5)
    with pytest.raises(KeyError):
        feature.compute(pd.DataFrame({"volume": [1, 2, 3]}))
