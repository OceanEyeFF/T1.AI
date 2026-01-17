"""技术指标特征集合"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ashare_lab.features.base import BaseFeature


@dataclass(frozen=True)
class MACDLine(BaseFeature):
    """MACD DIF 线 (12, 26)"""

    short: int = 12
    long: int = 26

    @property
    def name(self) -> str:
        return "macd_line"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].shift(1)
        ema_short = close.ewm(span=self.short, adjust=False, min_periods=self.short).mean()
        ema_long = close.ewm(span=self.long, adjust=False, min_periods=self.long).mean()
        return ema_short - ema_long


@dataclass(frozen=True)
class MACDSignal(BaseFeature):
    """MACD 信号线 (9)"""

    short: int = 12
    long: int = 26
    signal: int = 9

    @property
    def name(self) -> str:
        return "macd_signal"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        macd_line = MACDLine(self.short, self.long).compute(data)
        return macd_line.ewm(
            span=self.signal, adjust=False, min_periods=self.signal
        ).mean()


@dataclass(frozen=True)
class MACDHist(BaseFeature):
    """MACD 柱线 (macd_line - macd_signal)"""

    short: int = 12
    long: int = 26
    signal: int = 9

    @property
    def name(self) -> str:
        return "macd_hist"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        macd_line = MACDLine(self.short, self.long).compute(data)
        macd_signal = macd_line.ewm(
            span=self.signal, adjust=False, min_periods=self.signal
        ).mean()
        return macd_line - macd_signal


@dataclass(frozen=True)
class RSI(BaseFeature):
    """相对强弱指数 RSI(14)"""

    period: int = 14

    @property
    def name(self) -> str:
        return f"rsi_{self.period}"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].shift(1)
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(
            alpha=1 / self.period, adjust=False, min_periods=self.period
        ).mean()
        avg_loss = loss.ewm(
            alpha=1 / self.period, adjust=False, min_periods=self.period
        ).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


@dataclass(frozen=True)
class BollingerDeviation(BaseFeature):
    """布林带偏离度 (z-score)"""

    window: int = 20
    num_std: float = 2.0

    @property
    def name(self) -> str:
        return "bollinger_deviation"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].shift(1)
        rolling_mean = close.rolling(window=self.window, min_periods=self.window).mean()
        rolling_std = close.rolling(window=self.window, min_periods=self.window).std()
        return (close - rolling_mean) / rolling_std
