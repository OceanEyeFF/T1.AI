from __future__ import annotations

import math

import pytest
import torch

from ashare_lab.recommendation.engine import RecommendationEngine
from ashare_lab.recommendation.trend_aggregation import (
    DEFAULT_TREND_AGGREGATION_WEIGHTS,
    TrendAggregationConfig,
    aggregate_primary_trend_scores,
    rank_primary_trend_scores,
)

from tests.unit.recommendation.test_recommendation_engine import (
    DummyFeatureBuilder,
    DummyMTLModel,
    DummyUniverseFilter,
    _make_symbols,
)


def test_aggregate_primary_trend_scores_basic_ranking() -> None:
    symbols = ["A", "B", "C"]
    predictions = {
        "pred_3d": [1.0, 0.0, -1.0],
        "pred_5d": [1.0, 0.0, -1.0],
        "pred_10d": [1.0, 0.0, -1.0],
    }
    aggregated = aggregate_primary_trend_scores(symbols, predictions)
    ranked = rank_primary_trend_scores(aggregated)
    assert [item.symbol for item in ranked] == ["A", "B", "C"]
    assert ranked[0].aggregate_score > ranked[1].aggregate_score > ranked[2].aggregate_score


def test_aggregate_primary_trend_scores_supports_weight_override() -> None:
    symbols = ["A", "B", "C"]
    predictions = {
        "pred_3d": [2.0, -1.0, 0.0],
        "pred_5d": [0.0, 0.0, 0.0],
        "pred_10d": [0.0, 1.0, -1.0],
    }
    cfg = TrendAggregationConfig(weights={"3d": 1.0, "5d": 0.0, "10d": 0.0})
    aggregated = rank_primary_trend_scores(aggregate_primary_trend_scores(symbols, predictions, cfg))
    assert aggregated[0].symbol == "A"
    assert aggregated[-1].symbol == "B"


def test_aggregate_primary_trend_scores_strict_missing_default() -> None:
    symbols = ["A", "B"]
    predictions = {
        "pred_3d": [1.0, float("nan")],
        "pred_5d": [1.0, 0.0],
        "pred_10d": [1.0, 0.0],
    }
    aggregated = aggregate_primary_trend_scores(symbols, predictions)
    assert math.isfinite(aggregated[0].aggregate_score)
    assert math.isnan(aggregated[1].aggregate_score)


def test_aggregate_primary_trend_scores_allow_partial() -> None:
    symbols = ["A", "B"]
    predictions = {
        "pred_3d": [1.0, float("nan")],
        "pred_5d": [1.0, 0.0],
        "pred_10d": [1.0, 0.0],
    }
    aggregated = aggregate_primary_trend_scores(symbols, predictions, TrendAggregationConfig(allow_partial=True))
    assert math.isfinite(aggregated[1].aggregate_score)


def test_aggregation_weights_are_normalized() -> None:
    total = sum(DEFAULT_TREND_AGGREGATION_WEIGHTS.values())
    assert pytest.approx(total) == 1.0


def test_generate_trend_recommendations_returns_single_ranked_list() -> None:
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}", "volume": 1000, "return_20d": 0.08} for s in symbols}
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    preds = {
        "pred_3d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_5d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_10d": torch.linspace(0.0, 0.11, steps=len(symbols)),
    }
    preds["pred_3d"][-1] = 0.5
    preds["pred_5d"][-1] = 0.5
    preds["pred_10d"][-1] = 0.5

    engine = RecommendationEngine(DummyMTLModel(preds), fb, uf)
    recs, diagnostics = engine.generate_trend_recommendations("20250115", top_n=5)

    assert len(recs) == 5
    assert recs[0].symbol == symbols[-1]
    assert recs[0].predicted_return > recs[-1].predicted_return
    assert "主线聚合" in recs[0].reason
    assert recs[0].symbol in diagnostics
    assert math.isfinite(diagnostics[recs[0].symbol].aggregate_score)
