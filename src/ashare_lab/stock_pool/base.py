"""选股策略抽象基类。

每个策略是自包含的子文件夹（strategy.py + config + pools/）。
对外暴露统一接口：select(universe) → symbols + metadata。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PoolCandidate:
    """策略产出的候选池。"""

    symbols: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class StockPoolStrategy(ABC):
    """选股策略抽象基类。

    子类只需实现 select()。每个策略放在独立的子文件夹中：

        low_manipulation/
        ├── strategy.py   # class LowManipulationStrategy(StockPoolStrategy)
        ├── config.toml   # 策略参数（权重、阈值等）
        └── pools/        # 产出的 registry 池子
    """

    @abstractmethod
    def select(self, universe: list[str]) -> PoolCandidate:
        """从 universe 中选出符合策略的股票。

        Args:
            universe: 候选股票代码列表

        Returns:
            PoolCandidate(symbols=入选代码, metadata=筛选依据)
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称，用作文件夹名和 pool_family。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """策略的一句话描述。"""
        ...
