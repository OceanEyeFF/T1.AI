"""数据集构建模块"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ashare_lab.dataset.builder import DatasetBuilder, DatasetConfig
from ashare_lab.dataset.preprocessing import (
    FeatureQualityError,
    FeatureQualityReport,
    RobustScaleConfig,
    RollingRobustScaler,
    screen_feature_rows,
)

__all__ = [
    "DatasetBuilder",
    "DatasetConfig",
    "FeatureQualityError",
    "FeatureQualityReport",
    "RobustScaleConfig",
    "RollingRobustScaler",
    "screen_feature_rows",
    "load_sequence_parquet",
]

if TYPE_CHECKING:  # pragma: no cover
    from ashare_lab.dataset.sequence_parquet import load_sequence_parquet


def __getattr__(name: str) -> Any:  # pragma: no cover - legacy lazy import
    if name == "load_sequence_parquet":
        from ashare_lab.dataset.sequence_parquet import load_sequence_parquet

        return load_sequence_parquet
    raise AttributeError(name)
