"""数据集构建模块"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ashare_lab.dataset.builder import DatasetBuilder, DatasetConfig

__all__ = ["DatasetBuilder", "DatasetConfig", "load_sequence_parquet"]

if TYPE_CHECKING:  # pragma: no cover
    from ashare_lab.dataset.sequence_parquet import load_sequence_parquet


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "load_sequence_parquet":
        from ashare_lab.dataset.sequence_parquet import load_sequence_parquet

        return load_sequence_parquet
    raise AttributeError(name)
