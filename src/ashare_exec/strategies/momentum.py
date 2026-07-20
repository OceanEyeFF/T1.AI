"""Mechanical lookback-momentum Top-N strategy (B0).

Implements ``ashare_infra.sim.engine.Strategy.target_weights`` directly.
Knife-2 will route the same logic through DecisionAPI + WeightMapper; this
monolith is intentional for B0 stand-up only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MomentumTopNStrategy:
    """Equal-weight the top-N symbols by lookback return.

    Parameters
    ----------
    top_n:
        Max names to hold (fewer if not enough eligible symbols).
    lookback:
        Bars between past and current close for the momentum score.
    min_history:
        Require at least this many non-NaN closes (also at least ``lookback + 1``).
    rebalance_threshold:
        Reserved for knife-2 / future turnover logic; unused in B0.
    """

    top_n: int = 3
    lookback: int = 20
    min_history: int = 60
    rebalance_threshold: float = 0.05

    def target_weights(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        _ = today
        scores: list[tuple[str, float]] = []
        for symbol, df in history.items():
            if "close" not in df.columns:
                continue
            close = df["close"].dropna()
            if len(close) < max(self.min_history, self.lookback + 1):
                continue
            r = float(close.iloc[-1] / close.iloc[-1 - self.lookback] - 1.0)
            if np.isfinite(r):
                scores.append((symbol, r))

        scores.sort(key=lambda x: x[1], reverse=True)
        selected = [s for s, _ in scores[: self.top_n]]
        if not selected:
            return {}

        w = 1.0 / float(len(selected))
        return {s: w for s in selected}
