"""
策略层模块 - 拆分为信号生成与仓位管理两层

此模块实现了低换手策略架构：
- signal: 信号生成器（打分/排序）
- portfolio: 仓位管理器（目标权重/换仓门槛）

设计思想：
1. 分离关注点：信号生成与仓位管理解耦
2. 低换手优化：仅当优势足够大才执行换仓
3. 成本感知：预期收益必须覆盖成本
"""

from ashare_lab.strategy.signal import SignalGenerator, MomentumSignalGenerator
from ashare_lab.strategy.portfolio import PortfolioManager

__all__ = [
    "SignalGenerator",
    "MomentumSignalGenerator",
    "PortfolioManager",
]
