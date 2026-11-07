"""Deprecated import path for the retired static generic trainer."""

from __future__ import annotations

from typing import Any

_MESSAGE = (
    "ashare_lab.training.trainer is retired. Use Feature Contract-aware rolling training instead."
)


def _retired(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError(_MESSAGE)


TrainerConfig = _retired
StockDataset = _retired
EarlyStopping = _retired
Trainer = _retired

__all__ = ["EarlyStopping", "StockDataset", "Trainer", "TrainerConfig"]
