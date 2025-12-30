"""超额收益标签

定义基于次日收益的超额收益标签，用于预测模型训练。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ExcessReturnLabel:
    """超额收益标签

    计算规则：
        label[t] = (stock_close[t+1] / stock_close[t] - 1) - (benchmark_close[t+1] / benchmark_close[t] - 1)

    时间对齐：
        - label[t] 对应的是 t+1 日的超额收益
        - 配合特征使用时，特征[t] 使用 t-1 及之前的数据，标签[t] 使用 t+1 的收益
        - 这样避免了前视偏差

    示例：
        >>> label = ExcessReturnLabel()
        >>> result = label.compute(stock_data, benchmark_data)
        >>> # 2024-01-15 的标签 = (stock收益[2024-01-16] - benchmark收益[2024-01-16])
    """

    @property
    def name(self) -> str:
        return "excess_return"

    def compute(
        self,
        stock_data: pd.DataFrame,
        benchmark_data: pd.DataFrame,
    ) -> pd.Series:
        """计算超额收益标签

        Args:
            stock_data: 股票历史行情数据（必须包含 close 列）
                       索引为 date（datetime64[ns]，升序）
            benchmark_data: 基准历史行情数据（必须包含 close 列）
                           索引为 date（datetime64[ns]，升序）

        Returns:
            超额收益 Series，索引与输入对齐

        注意：
            - label[t] 使用 t+1 日的收益（未来 1 日收益）
            - 最后一个交易日的标签为 NaN（无未来数据）
        """
        # 计算股票次日收益率
        # pct_change() 计算 (close[t] / close[t-1] - 1)
        # shift(-1) 将未来收益移到当前日期，使得 label[t] = return[t+1]
        stock_return = stock_data["close"].pct_change(1, fill_method=None).shift(-1)

        # 计算基准次日收益率
        benchmark_return = benchmark_data["close"].pct_change(1, fill_method=None).shift(-1)

        # 对齐基准收益到股票数据的索引
        # 使用 reindex 确保两者索引一致
        benchmark_return_aligned = benchmark_return.reindex(stock_data.index)

        # 计算超额收益
        excess_return = stock_return - benchmark_return_aligned

        return excess_return


@dataclass(frozen=True)
class ForwardReturnLabel:
    """前向收益率标签（不考虑基准）

    计算规则：
        label[t] = (close[t+1] / close[t]) - 1

    时间对齐：
        - label[t] 对应的是 t+1 日的收益率
        - 不需要基准数据，直接使用股票收益

    示例：
        >>> label = ForwardReturnLabel()
        >>> result = label.compute(stock_data)
        >>> # 2024-01-15 的标签 = (close[2024-01-16] / close[2024-01-15]) - 1
    """

    @property
    def name(self) -> str:
        return "forward_return"

    def compute(self, stock_data: pd.DataFrame) -> pd.Series:
        """计算前向收益率标签

        Args:
            stock_data: 股票历史行情数据（必须包含 close 列）

        Returns:
            前向收益率 Series
        """
        # 计算次日收益率
        # pct_change() 计算 (close[t] / close[t-1] - 1)
        # shift(-1) 将未来收益移到当前日期
        return stock_data["close"].pct_change(1, fill_method=None).shift(-1)
