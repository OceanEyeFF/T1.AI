"""Execution-strategy package: Decision → WeightMapper → ``Strategy.target_weights``.

WT-EXEC-001 knife-2 seam. Engine still only accepts ``ashare_infra.sim.engine.Strategy``.
See ``docs/guides/ashare_exec_guide.md``.
"""

from __future__ import annotations

from ashare_exec.adapt import DecisionStrategy, as_strategy
from ashare_exec.decision import (
    DecisionAPI,
    DecisionContext,
    DecisionResult,
    MLStubDecision,
    MomentumDecision,
    SimpleDecisionAPI,
)
from ashare_exec.strategies.momentum import MomentumTopNStrategy
from ashare_exec.weight_mapper import WeightMapper

__all__ = [
    "DecisionAPI",
    "DecisionContext",
    "DecisionResult",
    "DecisionStrategy",
    "MLStubDecision",
    "MomentumDecision",
    "MomentumTopNStrategy",
    "SimpleDecisionAPI",
    "WeightMapper",
    "as_strategy",
]
