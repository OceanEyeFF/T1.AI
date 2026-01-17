"""价格斜率特征

使用 log(close) 对时间做线性回归斜率，衡量价格趋势。
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from ashare_lab.features.base import BaseFeature


def _slope_calculator(window: int):
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    denom = np.sum((x - x_mean) ** 2)

    def _calc(y: np.ndarray) -> float:
        return float(np.sum((x - x_mean) * (y - y.mean())) / denom)

    return _calc


@dataclass(frozen=True)
class PriceSlope(BaseFeature):
    """log(close) 回归斜率"""

    window: int

    @property
    def name(self) -> str:
        return f"price_slope_{self.window}d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        if "close" not in data:
            raise KeyError("input data must contain 'close'")

        log_close = np.log(data["close"]).shift(1)  # t 日特征不使用当日价格
        calc = _slope_calculator(self.window)
        return log_close.rolling(window=self.window, min_periods=self.window).apply(
            calc, raw=True
        )
