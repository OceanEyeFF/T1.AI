"""特征计算基础类

所有特征必须遵守严格的时间对齐规则：
- t 日特征仅使用 t-1 及之前的数据
- 禁止使用未来信息（前视偏差）
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseFeature(ABC):
    """特征计算抽象基类

    所有特征计算类必须继承此类并实现 compute 方法。

    时间对齐规则：
        - compute() 方法接收的 DataFrame 应包含 date 索引（datetime64[ns]）
        - 返回的 Series 索引必须与输入对齐
        - t 日特征值仅使用 [0, t-1] 的数据（不包含 t 日）

    示例：
        >>> class Return1D(BaseFeature):
        ...     @property
        ...     def name(self) -> str:
        ...         return "return_1d"
        ...
        ...     def compute(self, data: pd.DataFrame) -> pd.Series:
        ...         # t 日收益率 = (close[t-1] / close[t-2]) - 1
        ...         return data["close"].pct_change(1)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """特征名称（用于列名）"""
        pass

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """计算特征值

        Args:
            data: 历史行情数据（包含 open/high/low/close/volume/amount 列）
                  索引为 date（datetime64[ns]，升序）

        Returns:
            特征值 Series，索引与输入对齐

        注意：
            - 必须严格遵守时间对齐规则（t 日特征仅使用 t-1 及之前数据）
            - 返回的 Series 可能包含 NaN（如窗口期不足）
        """
        pass
