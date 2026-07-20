"""Decision layer: scores / ranked candidates only (no final weights)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DecisionContext:
    """Extensible decision inputs.

    ``history`` matches ``Strategy.target_weights`` history. Extra keys (model
    handles, feature frames, ``as_of``, etc.) go in ``extras`` without changing
    the engine Protocol.
    """

    today: pd.Timestamp
    history: Mapping[str, pd.DataFrame]
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionResult:
    """Scores and a descending ranked candidate list. Never final portfolio weights."""

    scores: dict[str, float]
    ranked: list[tuple[str, float]]


class DecisionAPI(Protocol):
    def decide(self, ctx: DecisionContext) -> DecisionResult: ...


def _rank_scores(scores: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


@dataclass(frozen=True)
class MomentumDecision:
    """Mechanical lookback-return scores (same formula as B0 MomentumTopN)."""

    lookback: int = 20
    min_history: int = 60

    def decide(self, ctx: DecisionContext) -> DecisionResult:
        _ = ctx.today
        scores: dict[str, float] = {}
        for symbol, df in ctx.history.items():
            if "close" not in df.columns:
                continue
            close = df["close"].dropna()
            if len(close) < max(self.min_history, self.lookback + 1):
                continue
            r = float(close.iloc[-1] / close.iloc[-1 - self.lookback] - 1.0)
            if np.isfinite(r):
                scores[symbol] = r
        return DecisionResult(scores=scores, ranked=_rank_scores(scores))


@dataclass(frozen=True)
class MLStubDecision:
    """Knife-2 ML stub: inject fake model scores; no training / inference.

    Prefer construction-time ``model_scores``. Optional override via
    ``ctx.extras["model_scores"]`` (mapping) for per-call injection.
    """

    model_scores: Mapping[str, float] = field(default_factory=dict)

    def decide(self, ctx: DecisionContext) -> DecisionResult:
        scores: dict[str, float] = {
            symbol: float(score)
            for symbol, score in self.model_scores.items()
            if symbol in ctx.history
        }
        extra = ctx.extras.get("model_scores")
        if isinstance(extra, Mapping):
            for symbol, score in extra.items():
                if symbol in ctx.history:
                    scores[str(symbol)] = float(score)
        return DecisionResult(scores=scores, ranked=_rank_scores(scores))


# Brief name alias
SimpleDecisionAPI = DecisionAPI
