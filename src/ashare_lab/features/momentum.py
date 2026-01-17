"""价格动量特征

实现基于价格变化的动量特征，严格遵守时间对齐规则。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ashare_lab.features.base import BaseFeature


@dataclass(frozen=True)
class Return1D(BaseFeature):
    """1 日收益率特征

    计算规则：
        return_1d[t] = (close[t-1] / close[t-2]) - 1.0

    时间对齐：
        - t 日特征值使用 t-1 和 t-2 的收盘价
        - 不使用 t 日当天的数据（防止前视偏差）

    示例：
        >>> feature = Return1D()
        >>> result = feature.compute(data)
        >>> # 2024-01-15 的特征值 = (close[2024-01-14] / close[2024-01-13]) - 1
    """

    @property
    def name(self) -> str:
        return "return_1d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算 1 日收益率

        Args:
            data: 历史行情数据（必须包含 close 列）

        Returns:
            1 日收益率 Series
        """
        # 先计算普通收益率 (close[t] / close[t-1] - 1)
        # 然后 shift(1) 确保 t 日特征使用 t-1 的收益率
        # fill_method=None 避免填充 NaN 值（保持数据真实性）
        return data["close"].pct_change(1, fill_method=None).shift(1)


@dataclass(frozen=True)
class Return5D(BaseFeature):
    """5 日收益率特征

    计算规则：
        return_5d[t] = (close[t-1] / close[t-6]) - 1.0

    时间对齐：
        - t 日特征值使用 t-1 和 t-6 的收盘价
        - 不使用 t 日当天的数据（防止前视偏差）

    示例：
        >>> feature = Return5D()
        >>> result = feature.compute(data)
        >>> # 2024-01-15 的特征值 = (close[2024-01-14] / close[2024-01-09]) - 1
    """

    @property
    def name(self) -> str:
        return "return_5d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算 5 日收益率

        Args:
            data: 历史行情数据（必须包含 close 列）

        Returns:
            5 日收益率 Series
        """
        # 先计算 5 日收益率 (close[t] / close[t-5] - 1)
        # 然后 shift(1) 确保 t 日特征使用 t-1 到 t-6 的数据
        # fill_method=None 避免填充 NaN 值（保持数据真实性）
        return data["close"].pct_change(5, fill_method=None).shift(1)


@dataclass(frozen=True)
class Return20D(BaseFeature):
    """20 日收益率特征

    计算规则：
        return_20d[t] = (close[t-1] / close[t-21]) - 1.0

    时间对齐：
        - t 日特征值使用 t-1 和 t-21 的收盘价
        - 不使用 t 日当天的数据（防止前视偏差）

    示例：
        >>> feature = Return20D()
        >>> result = feature.compute(data)
        >>> # 2024-01-15 的特征值 = (close[2024-01-14] / close[2023-12-19]) - 1
    """

    @property
    def name(self) -> str:
        return "return_20d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算 20 日收益率

        Args:
            data: 历史行情数据（必须包含 close 列）

        Returns:
            20 日收益率 Series
        """
        # 先计算 20 日收益率 (close[t] / close[t-20] - 1)
        # 然后 shift(1) 确保 t 日特征使用 t-1 到 t-21 的数据
        # fill_method=None 避免填充 NaN 值（保持数据真实性）
        return data["close"].pct_change(20, fill_method=None).shift(1)


@dataclass(frozen=True)
class Return10D(BaseFeature):
    """10 日收益率特征"""

    @property
    def name(self) -> str:
        return "return_10d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["close"].pct_change(10, fill_method=None).shift(1)


@dataclass(frozen=True)
class Return60D(BaseFeature):
    """60 日收益率特征"""

    @property
    def name(self) -> str:
        return "return_60d"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["close"].pct_change(60, fill_method=None).shift(1)
