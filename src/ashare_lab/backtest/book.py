"""Shim: ``ashare_lab.backtest.book`` → ``ashare_infra.sim.book``."""

from ashare_infra.sim.book import Lot, PositionBook

__all__ = ["Lot", "PositionBook"]
