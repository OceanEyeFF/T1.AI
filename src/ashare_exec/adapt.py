"""Adapt DecisionAPI + WeightMapper into ``ashare_infra.sim.engine.Strategy``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from ashare_exec.decision import DecisionAPI, DecisionContext
from ashare_exec.weight_mapper import WeightMapper


@dataclass(frozen=True)
class DecisionStrategy:
    """``Strategy`` adapter: decide → map_weights → ``target_weights``.

    Engine still only sees ``target_weights(today, history)``. Extra decision
    context is attached via ``extras`` (extensible beyond history).
    """

    decision: DecisionAPI
    mapper: WeightMapper
    extras: Mapping[str, Any] | None = None

    def target_weights(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        ctx = DecisionContext(
            today=today,
            history=history,
            extras=dict(self.extras or {}),
        )
        result = self.decision.decide(ctx)
        return self.mapper.map_weights(result.ranked)


def as_strategy(
    decision: DecisionAPI,
    mapper: WeightMapper,
    *,
    extras: Mapping[str, Any] | None = None,
) -> DecisionStrategy:
    """Build a Strategy-compatible adapter on the shared Decision → Mapper seam."""
    return DecisionStrategy(decision=decision, mapper=mapper, extras=extras)
