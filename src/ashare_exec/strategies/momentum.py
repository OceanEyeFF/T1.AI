"""Mechanical lookback-momentum Top-N strategy (via Decision → Mapper seam)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import pandas as pd

from ashare_exec.adapt import DecisionStrategy, as_strategy
from ashare_exec.decision import MomentumDecision
from ashare_exec.weight_mapper import WeightMapper


@dataclass(frozen=True)
class MomentumTopNStrategy:
    """Equal-weight top-N by lookback return — same seam as ML stubs.

    Internally: ``MomentumDecision`` → ``WeightMapper`` → ``DecisionStrategy``.
    Do not reintroduce a direct weight shortcut here.
    """

    top_n: int = 3
    lookback: int = 20
    min_history: int = 60
    rebalance_threshold: float = 0.05

    @cached_property
    def _adapter(self) -> DecisionStrategy:
        _ = self.rebalance_threshold  # reserved; WeightMapper turnover is a later WT
        return as_strategy(
            MomentumDecision(lookback=self.lookback, min_history=self.min_history),
            WeightMapper(top_n=self.top_n),
        )

    def target_weights(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        return self._adapter.target_weights(today, history)
