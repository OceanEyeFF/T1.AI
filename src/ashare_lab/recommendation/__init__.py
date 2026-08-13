"""Recommendation module.

This package provides:
- recommendation engine (ranking)
- recommendation validation utilities

说明：这里使用惰性导入，避免在仅做静态发现/覆盖率收集时提前加载重量级依赖。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "Recommendation",
    "RecommendationEngine",
    "save_as_csv",
    "save_as_json",
    "save_as_markdown",
    "AggregatedTrendScore",
    "TrendAggregationConfig",
    "aggregate_primary_trend_scores",
    "rank_primary_trend_scores",
    "DailyBarsSource",
    "ODPSourceAdapter",
    "TushareSourceAdapter",
    "ValidationResult",
    "RecommendationValidator",
    "RecommendationHistory",
]

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    from .engine import Recommendation, RecommendationEngine, save_as_csv, save_as_json, save_as_markdown
    from .history import RecommendationHistory
    from .trend_aggregation import (
        AggregatedTrendScore,
        TrendAggregationConfig,
        aggregate_primary_trend_scores,
        rank_primary_trend_scores,
    )
    from .validator import (
        DailyBarsSource,
        ODPSourceAdapter,
        RecommendationValidator,
        TushareSourceAdapter,
        ValidationResult,
    )


def __getattr__(name: str) -> Any:  # pragma: no cover - 运行时按需触发
    if name in {"Recommendation", "RecommendationEngine", "save_as_csv", "save_as_json", "save_as_markdown"}:
        from .engine import Recommendation, RecommendationEngine, save_as_csv, save_as_json, save_as_markdown

        return {
            "Recommendation": Recommendation,
            "RecommendationEngine": RecommendationEngine,
            "save_as_csv": save_as_csv,
            "save_as_json": save_as_json,
            "save_as_markdown": save_as_markdown,
        }[name]

    if name in {
        "AggregatedTrendScore",
        "TrendAggregationConfig",
        "aggregate_primary_trend_scores",
        "rank_primary_trend_scores",
    }:
        from .trend_aggregation import (
            AggregatedTrendScore,
            TrendAggregationConfig,
            aggregate_primary_trend_scores,
            rank_primary_trend_scores,
        )

        return {
            "AggregatedTrendScore": AggregatedTrendScore,
            "TrendAggregationConfig": TrendAggregationConfig,
            "aggregate_primary_trend_scores": aggregate_primary_trend_scores,
            "rank_primary_trend_scores": rank_primary_trend_scores,
        }[name]

    if name in {
        "DailyBarsSource",
        "ODPSourceAdapter",
        "TushareSourceAdapter",
        "ValidationResult",
        "RecommendationValidator",
    }:
        from .validator import (
            DailyBarsSource,
            ODPSourceAdapter,
            RecommendationValidator,
            TushareSourceAdapter,
            ValidationResult,
        )

        return {
            "DailyBarsSource": DailyBarsSource,
            "ODPSourceAdapter": ODPSourceAdapter,
            "TushareSourceAdapter": TushareSourceAdapter,
            "ValidationResult": ValidationResult,
            "RecommendationValidator": RecommendationValidator,
        }[name]

    if name == "RecommendationHistory":
        from .history import RecommendationHistory

        return RecommendationHistory

    raise AttributeError(name)
