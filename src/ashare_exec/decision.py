"""Decision layer: scores / ranked candidates only (no final weights)."""

from __future__ import annotations

import math
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


def _normalize_symbol_key(symbol: Any) -> str:
    """Normalize a score key to match string history keys.

    Aligns with ``ashare_infra.lake.meta._normalize_symbol`` for numeric codes:

    - ``int``/integral ``float`` → digit string (``600000``, ``600000.0`` → ``"600000"``)
    - short digit codes are zero-padded to 6 (``1`` / ``"1"`` → ``"000001"``)
    - ``ts_code``-style suffixes are stripped (``"600000.SH"`` → ``"600000"``)
    - non-integral floats and other types fall back to a stripped ``str()``
    """
    if isinstance(symbol, bool):
        return str(symbol)
    if isinstance(symbol, int):
        text = str(symbol)
    elif isinstance(symbol, float):
        text = str(int(symbol)) if symbol.is_integer() else str(symbol)
    else:
        text = str(symbol).strip()
        if "." in text:
            left = text.split(".", 1)[0]
            if left.isdigit():
                text = left
    if text.isdigit() and len(text) < 6:
        text = text.zfill(6)
    return text


def _merge_stub_scores(
    history: Mapping[str, pd.DataFrame],
    *mappings: Mapping[Any, float] | None,
) -> dict[str, float]:
    """Merge score mappings; later mappings override earlier per symbol.

    - Symbol keys are normalized so numeric / ts_code forms match string
      history keys (``1`` / ``"1"`` → ``"000001"``; ``"600000.SH"`` →
      ``"600000"``; aligns with ``ashare_infra.lake.meta._normalize_symbol``).
    - Only keys present in ``history`` are kept.
    - Non-finite scores (NaN/Inf) are dropped, matching ``MomentumDecision``.
    """
    scores: dict[str, float] = {}
    for mapping in mappings:
        if not isinstance(mapping, Mapping):
            continue
        for symbol, score in mapping.items():
            key = _normalize_symbol_key(symbol)
            if key not in history:
                continue
            value = float(score)
            if math.isfinite(value):
                scores[key] = value
            else:
                scores.pop(key, None)
    return scores


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
        extra = ctx.extras.get("model_scores")
        scores = _merge_stub_scores(ctx.history, self.model_scores, extra)
        return DecisionResult(scores=scores, ranked=_rank_scores(scores))


# Brief name alias
SimpleDecisionAPI = DecisionAPI
