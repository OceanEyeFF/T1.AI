"""量价特征

实现基于成交量和成交额的特征，严格遵守时间对齐规则。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ashare_lab.features.base import BaseFeature


@dataclass(frozen=True)
class VolumeRatio(BaseFeature):
    """量比特征

    计算规则：
        volume_ratio[t] = volume[t-1] / mean(volume[t-window:t-1])

    时间对齐：
        - t 日特征值使用 t-1 及之前的成交量
        - 不使用 t 日当天的数据（防止前视偏差）

    参数：
        window: 均值计算窗口（默认 5 日）

    示例：
        >>> feature = VolumeRatio(window=5)
        >>> result = feature.compute(data)
        >>> # 2024-01-10 的特征值 = volume[2024-01-09] / mean(volume[2024-01-05:2024-01-09])
    """

    window: int = 5

    @property
    def name(self) -> str:
        return f"volume_ratio_{self.window}d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算量比

        Args:
            data: 历史行情数据（必须包含 volume 列）

        Returns:
            量比 Series
        """
        # 计算滚动均值（窗口期内的平均成交量）
        rolling_mean = data["volume"].rolling(window=self.window, min_periods=1).mean()

        # 计算量比：当前成交量 / 滚动均值
        # 使用 shift(1) 确保 t 日特征使用 t-1 的数据
        volume_shifted = data["volume"].shift(1)
        rolling_mean_shifted = rolling_mean.shift(1)

        return volume_shifted / rolling_mean_shifted


@dataclass(frozen=True)
class AmountChange(BaseFeature):
    """成交额变化特征

    计算规则：
        amount_change[t] = (amount[t-1] / amount[t-2]) - 1.0

    时间对齐：
        - t 日特征值使用 t-1 和 t-2 的成交额
        - 不使用 t 日当天的数据（防止前视偏差）

    示例：
        >>> feature = AmountChange()
        >>> result = feature.compute(data)
        >>> # 2024-01-15 的特征值 = (amount[2024-01-14] / amount[2024-01-13]) - 1
    """

    @property
    def name(self) -> str:
        return "amount_change"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算成交额变化率

        Args:
            data: 历史行情数据（必须包含 amount 列）

        Returns:
            成交额变化率 Series
        """
        # 计算成交额变化率 (amount[t] / amount[t-1] - 1)
        # 然后 shift(1) 确保 t 日特征使用 t-1 的变化率
        # fill_method=None 避免填充 NaN 值（保持数据真实性）
        return data["amount"].pct_change(1, fill_method=None).shift(1)


@dataclass(frozen=True)
class VolumeChange(BaseFeature):
    """成交量变化特征

    计算规则：
        volume_change[t] = (volume[t-1] / volume[t-2]) - 1.0

    时间对齐：
        - t 日特征值使用 t-1 和 t-2 的成交量
        - 不使用 t 日当天的数据（防止前视偏差）

    示例：
        >>> feature = VolumeChange()
        >>> result = feature.compute(data)
        >>> # 2024-01-15 的特征值 = (volume[2024-01-14] / volume[2024-01-13]) - 1
    """

    @property
    def name(self) -> str:
        return "volume_change"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算成交量变化率

        Args:
            data: 历史行情数据（必须包含 volume 列）

        Returns:
            成交量变化率 Series
        """
        # 计算成交量变化率 (volume[t] / volume[t-1] - 1)
        # 然后 shift(1) 确保 t 日特征使用 t-1 的变化率
        # fill_method=None 避免填充 NaN 值（保持数据真实性）
        return data["volume"].pct_change(1, fill_method=None).shift(1)
