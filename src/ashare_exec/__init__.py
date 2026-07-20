"""Execution-strategy package: Decision/scores → weights → ``Strategy.target_weights``.

B0 (WT-EXEC-001): mechanical strategies that satisfy ``ashare_infra.sim.engine.Strategy``.
Knife-2 will add DecisionAPI + WeightMapper seam; do not bypass that seam later.
"""

from __future__ import annotations

from ashare_exec.strategies.momentum import MomentumTopNStrategy

__all__ = ["MomentumTopNStrategy"]
