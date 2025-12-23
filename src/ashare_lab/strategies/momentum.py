from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MomentumTopNStrategy:
    top_n: int = 3
    lookback: int = 20
    min_history: int = 60
    rebalance_threshold: float = 0.05

    def target_weights(
        self,
        today: pd.Timestamp,
        history: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
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

