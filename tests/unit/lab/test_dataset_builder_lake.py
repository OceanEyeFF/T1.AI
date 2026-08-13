"""Phase 2 T2 white-box: DatasetBuilder routes loads through DataLake + symbols."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from ashare_infra.lake import DataLake
from ashare_lab.dataset.builder import DatasetBuilder, DatasetConfig
from ashare_lab.features.base import BaseFeature


class _NoopFeature(BaseFeature):
    @property
    def name(self) -> str:
        return "noop"

    def compute(self, data: pd.DataFrame) -> pd.Series:  # noqa: ARG002
        return pd.Series(dtype=float)


def _config(tmp_path: Path, *, source: str = "tushare") -> DatasetConfig:
    return DatasetConfig(
        name="wb_lake",
        symbols=["600519"],
        start_date="20240101",
        end_date="20240131",
        features=[_NoopFeature()],
        source=source,  # type: ignore[arg-type]
        cache_dir=tmp_path,
        label_type="excess_return",
        benchmark_code="000300",
    )


def test_builder_holds_datalake(tmp_path: Path) -> None:
    builder = DatasetBuilder(_config(tmp_path))
    assert isinstance(builder._lake, DataLake)
    assert builder._lake.cache_dir == tmp_path
    assert builder._lake.default_source == "tushare"


def test_builder_tushare_uses_r4_factory(tmp_path: Path) -> None:
    builder = DatasetBuilder(_config(tmp_path, source="tushare"))
    assert isinstance(builder._lake, DataLake)
    assert builder._lake.default_source == "tushare"
    assert builder._lake.refresh is False


def test_resolve_lake_symbol_by_source(tmp_path: Path) -> None:
    builder = DatasetBuilder(_config(tmp_path, source="tushare"))
    assert builder._resolve_lake_symbol("600519", "tushare") == "600519.SH"
    assert builder._resolve_lake_symbol("000001", "odp") == "000001.SZ"


def test_load_stock_data_calls_lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder = DatasetBuilder(_config(tmp_path, source="tushare"))
    frame = pd.DataFrame(
        {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )
    mock_load = MagicMock(return_value=frame)
    monkeypatch.setattr(builder._lake, "load_daily_bars", mock_load)

    builder._load_stock_data()

    mock_load.assert_called_once_with(
        "600519.SH",
        "20240101",
        "20240131",
        source="tushare",
        adjust="qfq",
    )
    assert "600519" in builder.stock_data


def test_load_benchmark_calls_load_index_daily(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = DatasetBuilder(_config(tmp_path))
    frame = pd.DataFrame(
        {"close": [1.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )
    mock_index = MagicMock(return_value=frame)
    monkeypatch.setattr(builder._lake, "load_index_daily", mock_index)

    builder._load_benchmark_data()

    mock_index.assert_called_once_with("000300", "20240101", "20240131")
    assert builder.benchmark_data is not None
