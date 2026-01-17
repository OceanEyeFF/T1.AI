"""特征计算模块"""

from __future__ import annotations

from ashare_lab.features.base import BaseFeature
from ashare_lab.features.momentum import (
    Return1D,
    Return5D,
    Return10D,
    Return20D,
    Return60D,
)
from ashare_lab.features.price_slope import PriceSlope
from ashare_lab.features.volume import AmountChange, RelativeVolume, VolumeChange, VolumeRatio
from ashare_lab.features.technical import (
    MACDHist,
    MACDLine,
    MACDSignal,
    RSI,
    BollingerDeviation,
)

__all__ = [
    "BaseFeature",
    "Return1D",
    "Return5D",
    "Return10D",
    "Return20D",
    "Return60D",
    "PriceSlope",
    "VolumeRatio",
    "VolumeChange",
    "AmountChange",
    "RelativeVolume",
    "MACDLine",
    "MACDSignal",
    "MACDHist",
    "RSI",
    "BollingerDeviation",
]
