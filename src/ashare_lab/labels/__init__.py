"""标签计算模块"""

from __future__ import annotations

from ashare_lab.labels.excess_return import ExcessReturnLabel, ForwardReturnLabel
from ashare_lab.labels.multi_horizon import MultiHorizonLabel

__all__ = ["ExcessReturnLabel", "ForwardReturnLabel", "MultiHorizonLabel"]
