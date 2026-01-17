"""测试技术指标特征"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_lab.features.technical import (
    MACDHist,
    MACDLine,
    MACDSignal,
    RSI,
    BollingerDeviation,
)


def _sample_data() -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=200, freq="D")
    # 构造平滑上涨序列，方便验证
    close = pd.Series(np.linspace(10, 60, num=200), index=dates)
    return pd.DataFrame({"close": close, "volume": 1_000_000}, index=dates)


def test_macd_line_matches_manual() -> None:
    data = _sample_data()
    feature = MACDLine()
    result = feature.compute(data)

    close_shift = data["close"].shift(1)
    ema12 = close_shift.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close_shift.ewm(span=26, adjust=False, min_periods=26).mean()
    expected = ema12 - ema26

    idx = expected.index[60]
    assert np.isclose(result.loc[idx], expected.loc[idx], rtol=1e-9)


def test_macd_signal_and_hist() -> None:
    data = _sample_data()
    signal_feature = MACDSignal()
    hist_feature = MACDHist()

    line = MACDLine().compute(data)
    expected_signal = line.ewm(span=9, adjust=False, min_periods=9).mean()
    expected_hist = line - expected_signal

    idx = expected_signal.index[80]
    assert np.isclose(signal_feature.compute(data).loc[idx], expected_signal.loc[idx], rtol=1e-9)
    assert np.isclose(hist_feature.compute(data).loc[idx], expected_hist.loc[idx], rtol=1e-9)


def test_rsi_alignment() -> None:
    data = _sample_data()
    feature = RSI()
    result = feature.compute(data)

    close_shift = data["close"].shift(1)
    delta = close_shift.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    expected = 100 - (100 / (1 + avg_gain / avg_loss))

    idx = expected.index[50]
    assert np.isclose(result.loc[idx], expected.loc[idx], rtol=1e-9)


def test_bollinger_deviation() -> None:
    data = _sample_data()
    feature = BollingerDeviation()
    result = feature.compute(data)

    close_shift = data["close"].shift(1)
    mean = close_shift.rolling(window=20, min_periods=20).mean()
    std = close_shift.rolling(window=20, min_periods=20).std()
    expected = (close_shift - mean) / std

    idx = expected.index[40]
    assert np.isclose(result.loc[idx], expected.loc[idx], rtol=1e-9)


def test_nan_ratio_under_threshold() -> None:
    data = _sample_data()
    features = [MACDLine(), MACDSignal(), MACDHist(), RSI(), BollingerDeviation()]
    for feat in features:
        result = feat.compute(data)
        assert result.isna().mean() < 0.2
