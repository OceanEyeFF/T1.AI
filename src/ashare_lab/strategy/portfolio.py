"""
仓位管理器模块

此模块负责将信号分数转换为目标权重，并实现换仓门槛逻辑，
作为策略层的第二层，专注于"仓位管理"这一单一职责。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioManager:
    """
    仓位管理器

    负责将信号分数转换为目标权重，并应用换仓门槛优化。

    Attributes:
        top_n: 持仓数量（选择排名前 N 的股票）
        rebalance_threshold: 换仓门槛（阶段1暂不使用，留待阶段2实现）
        cost_coverage_ratio: 成本覆盖倍数（阶段1暂不使用，留待阶段2实现）
    """

    top_n: int = 3
    rebalance_threshold: float = 0.05
    cost_coverage_ratio: float = 3.0

    def compute_target_weights(
        self,
        ranked_signals: list[tuple[str, float]],
        current_positions: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """
        计算目标权重

        Args:
            ranked_signals: [(symbol, score), ...] - 按分数降序排列的股票列表
            current_positions: {symbol: weight} - 当前持仓权重（阶段1暂不使用）

        Returns:
            {symbol: weight} - 目标权重字典（权重和 ≤ 1.0）

        Implementation (阶段1 - 基础版本):
            1. 选择排名前 top_n 的股票
            2. 等权重分配（每只股票权重 = 1.0 / top_n）

        Note:
            - 阶段2 将实现换仓门槛逻辑（考虑 current_positions）
            - 阶段2 将实现成本覆盖检查（预期收益 > N * 预期成本）
        """
        # 1. 选择前 top_n 只股票
        selected = [symbol for symbol, _ in ranked_signals[: self.top_n]]

        # 2. 等权重分配
        if not selected:
            return {}

        weight = 1.0 / float(len(selected))
        return {symbol: weight for symbol in selected}

    def _should_rebalance(
        self,
        new_candidate: str,
        new_score: float,
        current_holding: str,
        current_score: float,
    ) -> bool:
        """
        判断是否应该换仓（阶段2实现）

        Args:
            new_candidate: 新候选股票代码
            new_score: 新候选股票分数
            current_holding: 当前持仓股票代码
            current_score: 当前持仓股票分数

        Returns:
            True if 应该换仓, False otherwise

        Implementation (阶段2):
            仅当 (new_score - current_score) > rebalance_threshold 时才换仓
        """
        # TODO: 阶段2实现换仓门槛逻辑
        score_advantage = new_score - current_score
        return score_advantage > self.rebalance_threshold

    def _estimate_cost(
        self,
        turnover_value: float,
    ) -> float:
        """
        估算交易成本（阶段2实现）

        Args:
            turnover_value: 换仓金额（RMB）

        Returns:
            预期成本（RMB）

        Implementation (阶段2):
            cost = max(5.0, turnover_value * 0.001)
        """
        # TODO: 阶段2实现成本估算
        return max(5.0, turnover_value * 0.001)
