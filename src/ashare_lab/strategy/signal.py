"""
信号生成器模块

此模块负责计算股票的打分（signal scores）并进行排序，
作为策略层的第一层，专注于"信号生成"这一单一职责。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd


class SignalGenerator(ABC):
    """
    信号生成器基类

    定义了信号生成器的标准接口：
    1. compute_scores: 计算每只股票的打分
    2. rank_stocks: 按分数排序股票
    """

    @abstractmethod
    def compute_scores(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        """
        计算每只股票的打分

        Args:
            today: 当前交易日时间戳
            history: {symbol: DataFrame} - 截至 today 之前的历史数据
                    每个 DataFrame 必须包含 'close' 列（收盘价）

        Returns:
            {symbol: score} - 每只股票的分数（越高越好）

        Note:
            - history 仅包含 today **之前**的数据（避免未来信息泄露）
            - 返回的分数用于排序，具体数值大小不重要
            - 如果股票数据不足或不合格，不应包含在返回结果中
        """
        pass

    def rank_stocks(
        self,
        scores: dict[str, float],
        top_n: int | None = None,
    ) -> list[tuple[str, float]]:
        """
        按分数降序排序股票

        Args:
            scores: {symbol: score} - 股票分数字典
            top_n: 可选，返回前 N 只股票（None 表示返回全部）

        Returns:
            [(symbol, score), ...] - 按分数降序排列的股票列表

        Example:
            >>> scores = {"600519": 0.15, "000333": 0.10, "601318": 0.20}
            >>> ranked = signal_gen.rank_stocks(scores, top_n=2)
            >>> print(ranked)
            [("601318", 0.20), ("600519", 0.15)]
        """
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if top_n is not None:
            return sorted_items[:top_n]
        return sorted_items


@dataclass(frozen=True)
class MomentumSignalGenerator(SignalGenerator):
    """
    动量信号生成器

    基于历史价格动量（lookback 期间的收益率）计算信号分数。
    分数 = (当前价格 / lookback 天前价格) - 1.0

    Attributes:
        lookback: 动量计算回溯天数（默认20天）
        min_history: 最小历史数据要求（默认60天）
    """

    lookback: int = 20
    min_history: int = 60

    def compute_scores(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        """
        计算基于动量的信号分数

        Args:
            today: 当前交易日时间戳
            history: {symbol: DataFrame} - 历史行情数据

        Returns:
            {symbol: momentum_score} - 动量分数（收益率）

        Implementation:
            1. 检查数据是否包含 'close' 列
            2. 检查历史数据长度是否满足 min_history 要求
            3. 计算 lookback 期间的收益率
            4. 过滤掉非有限值（NaN, Inf）
        """
        scores: dict[str, float] = {}

        for symbol, df in history.items():
            # 1. 检查是否有收盘价数据
            if "close" not in df.columns:
                continue

            close = df["close"].dropna()

            # 2. 检查历史数据长度
            min_required = max(self.min_history, self.lookback + 1)
            if len(close) < min_required:
                continue

            # 3. 计算动量（lookback 期间的收益率）
            current_price = float(close.iloc[-1])
            past_price = float(close.iloc[-1 - self.lookback])
            momentum = current_price / past_price - 1.0

            # 4. 过滤非有限值
            if np.isfinite(momentum):
                scores[symbol] = momentum

        return scores
