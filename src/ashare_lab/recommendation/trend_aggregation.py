"""Primary 3d/5d/10d trend score aggregation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import math
import numpy as np

from ashare_lab.trend_schema import PRIMARY_TREND_HORIZONS, PRIMARY_TREND_PRED_COLS, target_name_from_pred


@dataclass(frozen=True, slots=True)
class TrendAggregationConfig:
    """Configuration for cross-sectional primary trend aggregation."""

    weights: Mapping[str, float] | None = None
    zscore_clip: float | None = 3.0
    allow_partial: bool = False


@dataclass(frozen=True, slots=True)
class AggregatedTrendScore:
    """Per-symbol aggregated main-line trend score with diagnostics."""

    symbol: str
    aggregate_score: float
    raw_scores: dict[str, float]
    normalized_scores: dict[str, float]
    weighted_contributions: dict[str, float]


DEFAULT_TREND_AGGREGATION_WEIGHTS: dict[str, float] = {
    "3d": 0.2,
    "5d": 0.4,
    "10d": 0.4,
}


def aggregate_primary_trend_scores(
    symbols: Sequence[str],
    predictions: Mapping[str, Any],
    config: TrendAggregationConfig | None = None,
) -> list[AggregatedTrendScore]:
    """Aggregate 3d/5d/10d head outputs into one cross-sectional trend score."""

    cfg = config or TrendAggregationConfig()
    score_matrix = _prediction_matrix(symbols, predictions)
    weights = _resolve_weights(cfg.weights)

    normalized_by_pred = {
        pred_col: _zscore(score_matrix[pred_col], clip=cfg.zscore_clip) for pred_col in PRIMARY_TREND_PRED_COLS
    }

    results: list[AggregatedTrendScore] = []
    for idx, symbol in enumerate(symbols):
        raw_scores = {
            target_name_from_pred(pred_col): float(score_matrix[pred_col][idx]) for pred_col in PRIMARY_TREND_PRED_COLS
        }
        normalized_scores = {
            target_name_from_pred(pred_col): float(normalized_by_pred[pred_col][idx]) for pred_col in PRIMARY_TREND_PRED_COLS
        }

        aggregate_score, contributions = _aggregate_row(normalized_scores, weights, allow_partial=cfg.allow_partial)
        results.append(
            AggregatedTrendScore(
                symbol=str(symbol),
                aggregate_score=aggregate_score,
                raw_scores=raw_scores,
                normalized_scores=normalized_scores,
                weighted_contributions=contributions,
            )
        )

    return results


def rank_primary_trend_scores(
    aggregated_scores: Sequence[AggregatedTrendScore],
) -> list[AggregatedTrendScore]:
    """Rank aggregated scores descending, pushing non-finite scores to the end."""

    return sorted(
        aggregated_scores,
        key=lambda item: (-float(item.aggregate_score), item.symbol)
        if math.isfinite(item.aggregate_score)
        else (float("inf"), item.symbol),
    )


def _prediction_matrix(symbols: Sequence[str], predictions: Mapping[str, Any]) -> dict[str, np.ndarray]:
    n = len(symbols)
    out: dict[str, np.ndarray] = {}
    for pred_col in PRIMARY_TREND_PRED_COLS:
        if pred_col not in predictions:
            raise ValueError(f"predictions missing required key: {pred_col}")
        values = np.asarray(_to_1d_float_list(predictions[pred_col]), dtype=float)
        if values.shape != (n,):
            raise ValueError(f"prediction length mismatch for {pred_col}: {values.shape} != ({n},)")
        out[pred_col] = values
    return out


def _resolve_weights(overrides: Mapping[str, float] | None) -> dict[str, float]:
    base = dict(DEFAULT_TREND_AGGREGATION_WEIGHTS)
    if overrides:
        for key, value in overrides.items():
            name = str(key)
            if name not in base:
                raise ValueError(f"unsupported aggregation weight key: {name}")
            weight = float(value)
            if weight < 0:
                raise ValueError(f"aggregation weight must be non-negative: {name}={weight}")
            base[name] = weight

    total = sum(base.values())
    if total <= 0:
        raise ValueError("aggregation weights sum to 0")
    return {key: value / total for key, value in base.items()}


def _zscore(values: np.ndarray, clip: float | None) -> np.ndarray:
    out = np.full(values.shape, np.nan, dtype=float)
    finite_mask = np.isfinite(values)
    if finite_mask.sum() == 0:
        return out
    finite_values = values[finite_mask]
    mean = float(np.mean(finite_values))
    std = float(np.std(finite_values))
    if std < 1e-12:
        out[finite_mask] = 0.0
    else:
        out[finite_mask] = (finite_values - mean) / std
    if clip is not None:
        out[finite_mask] = np.clip(out[finite_mask], -float(clip), float(clip))
    return out


def _aggregate_row(
    normalized_scores: Mapping[str, float],
    weights: Mapping[str, float],
    *,
    allow_partial: bool,
) -> tuple[float, dict[str, float]]:
    valid_items: list[tuple[str, float, float]] = []
    contributions: dict[str, float] = {}
    for horizon in (f"{h}d" for h in PRIMARY_TREND_HORIZONS):
        score = float(normalized_scores[horizon])
        weight = float(weights[horizon])
        if math.isfinite(score):
            valid_items.append((horizon, score, weight))

    if not valid_items:
        return float("nan"), {f"{h}d": float("nan") for h in PRIMARY_TREND_HORIZONS}

    if not allow_partial and len(valid_items) != len(PRIMARY_TREND_HORIZONS):
        return float("nan"), {f"{h}d": float("nan") for h in PRIMARY_TREND_HORIZONS}

    weight_sum = sum(weight for _, _, weight in valid_items)
    if weight_sum <= 0:
        return float("nan"), {f"{h}d": float("nan") for h in PRIMARY_TREND_HORIZONS}

    aggregate_score = 0.0
    for horizon, score, weight in valid_items:
        normalized_weight = weight / weight_sum
        contrib = normalized_weight * score
        contributions[horizon] = float(contrib)
        aggregate_score += contrib

    for horizon in (f"{h}d" for h in PRIMARY_TREND_HORIZONS):
        contributions.setdefault(horizon, float("nan"))

    return float(aggregate_score), contributions


def _to_1d_float_list(values: Any) -> list[float]:
    if values is None:
        return []
    if hasattr(values, "detach") and hasattr(values, "cpu") and callable(values.detach):
        return [float(x) for x in values.detach().cpu().reshape(-1).tolist()]
    if hasattr(values, "tolist") and callable(values.tolist):
        out = values.tolist()
        if isinstance(out, list):
            if out and isinstance(out[0], list):
                out = [x for row in out for x in row]
            return [float(x) for x in out]
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return [float(x) for x in values]
    raise ValueError(f"unsupported prediction type: {type(values)!r}")

