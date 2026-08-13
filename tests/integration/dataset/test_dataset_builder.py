"""测试数据集构建器

验证完整的数据集构建流程，包括数据加载、特征计算、标签生成、数据切分和文件保存。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ashare_lab.dataset.builder import DatasetBuilder, DatasetConfig
from ashare_lab.features.momentum import Return1D, Return5D, Return20D
from ashare_lab.features.volume import AmountChange, VolumeChange, VolumeRatio
from ashare_lab.symbols import symbol_to_odp_equity_symbol, symbol_to_ts_code

# AO-O2 (WT-R4-A4-T4): fixtures seed TuShare qfq partition caches; tests use
# source="tushare" (DatasetConfig default since R4).


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """创建临时缓存目录"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """创建临时输出目录"""
    output_dir = tmp_path / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_stock_cache(temp_cache_dir: Path) -> Path:
    """创建测试股票数据缓存（R4 TuShare qfq 分区布局：cache/tushare_qfq/{ts_code}/）。"""
    from ashare_infra.data.tushare_source import _write_partitioned

    # 创建 30 天的测试数据（足够计算 20 日动量）
    dates = pd.date_range("2024-01-01", periods=30, freq="D")

    for symbol in ["600519", "000333"]:
        # 生成模拟价格数据
        base_price = 100.0 if symbol == "600519" else 50.0
        prices = base_price + np.cumsum(np.random.randn(30) * 0.5)
        prices = np.maximum(prices, base_price * 0.8)  # 防止负价格

        df = pd.DataFrame(
            {
                "open": prices - 0.5,
                "high": prices + 1.0,
                "low": prices - 1.0,
                "close": prices,
                "volume": 1000000 + np.random.randint(-100000, 100000, size=30),
                "amount": prices * (1000000 + np.random.randint(-100000, 100000, size=30)),
            },
            index=dates,
        )
        df.index.name = "date"

        # 保存到缓存（模拟 tushare_qfq 分区格式）
        _write_partitioned(
            df, temp_cache_dir / "tushare_qfq" / symbol_to_ts_code(symbol)
        )

    return temp_cache_dir


@pytest.fixture
def sample_benchmark_cache(temp_cache_dir: Path) -> Path:
    """创建测试基准数据缓存"""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    base_price = 3000.0
    prices = base_price + np.cumsum(np.random.randn(30) * 5)

    df = pd.DataFrame(
        {
            "date": dates,
            "open": prices - 5,
            "high": prices + 10,
            "low": prices - 10,
            "close": prices,
            "volume": 100000000,
            "amount": prices * 100000000,
        }
    )

    # 保存到缓存（模拟指数数据缓存格式）
    # 格式应匹配 index_source.py: index_{symbol}_daily_{start}_{end}.csv
    cache_file = temp_cache_dir / "index_000300_daily_20240101_20240130.csv"
    df.to_csv(cache_file, index=False)

    return temp_cache_dir


class TestDatasetBuilder:
    """测试数据集构建器"""

    def test_build_complete_pipeline(
        self,
        sample_stock_cache: Path,
        sample_benchmark_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试完整构建流程"""
        # 配置数据集
        features = [
            Return1D(),
            Return5D(),
            Return20D(),
            VolumeRatio(window=5),
            VolumeChange(),
            AmountChange(),
        ]

        config = DatasetConfig(
            name="test_dataset",
            symbols=["600519", "000333"],
            start_date="20240101",
            end_date="20240130",
            features=features,
            label_type="excess_return",
            train_end_date="20240121",  # 70% split
            valid_end_date="20240125",  # 85% split
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        # 构建数据集
        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 验证输出目录
        assert output_path.exists()
        assert output_path == temp_output_dir / "test_dataset"

        # 验证输出文件存在
        assert (output_path / "train.parquet").exists()
        assert (output_path / "valid.parquet").exists()
        assert (output_path / "test.parquet").exists()
        assert (output_path / "metadata.yaml").exists()

    def test_dataset_structure(
        self,
        sample_stock_cache: Path,
        sample_benchmark_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试数据集结构正确性"""
        features = [Return1D(), Return5D()]

        config = DatasetConfig(
            name="test_structure",
            symbols=["600519"],
            start_date="20240101",
            end_date="20240130",
            features=features,
            label_type="forward_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 读取训练集
        train_df = pd.read_parquet(output_path / "train.parquet")

        # 验证列存在
        assert "date" in train_df.columns
        assert "symbol" in train_df.columns
        assert "return_1d" in train_df.columns
        assert "return_5d" in train_df.columns
        assert "label" in train_df.columns
        assert "close" in train_df.columns

        # 验证数据类型
        assert pd.api.types.is_datetime64_any_dtype(train_df["date"])
        assert pd.api.types.is_string_dtype(train_df["symbol"])

        # 验证股票数量
        assert len(train_df["symbol"].unique()) == 1
        assert train_df["symbol"].iloc[0] == "600519"

    def test_dataset_split(
        self,
        sample_stock_cache: Path,
        sample_benchmark_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试数据集切分逻辑"""
        config = DatasetConfig(
            name="test_split",
            symbols=["600519", "000333"],
            start_date="20240101",
            end_date="20240130",
            features=[Return1D()],
            label_type="forward_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 读取所有数据集
        train_df = pd.read_parquet(output_path / "train.parquet")
        valid_df = pd.read_parquet(output_path / "valid.parquet")
        test_df = pd.read_parquet(output_path / "test.parquet")

        # 验证日期范围
        train_end = pd.to_datetime("20240121")
        valid_end = pd.to_datetime("20240125")

        assert (train_df["date"] <= train_end).all()
        assert ((valid_df["date"] > train_end) & (valid_df["date"] <= valid_end)).all()
        assert (test_df["date"] > valid_end).all()

        # 验证没有数据丢失（考虑到多只股票）
        total_samples = len(train_df) + len(valid_df) + len(test_df)
        assert total_samples > 0

    def test_metadata_generation(
        self,
        sample_stock_cache: Path,
        sample_benchmark_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试元数据生成"""
        import yaml  # 本地导入，仅在需要时使用

        features = [Return1D(), Return5D(), VolumeRatio()]

        config = DatasetConfig(
            name="test_metadata",
            symbols=["600519"],
            start_date="20240101",
            end_date="20240130",
            features=features,
            label_type="excess_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 读取元数据
        with open(output_path / "metadata.yaml", encoding="utf-8") as f:
            metadata = yaml.safe_load(f)

        # 验证元数据内容
        assert metadata["name"] == "test_metadata"
        assert "created_at" in metadata
        assert metadata["date_range"]["start"] == "20240101"
        assert metadata["date_range"]["end"] == "20240130"

        # 验证特征信息
        assert len(metadata["features"]) == 3
        feature_names = [f["name"] for f in metadata["features"]]
        assert "return_1d" in feature_names
        assert "return_5d" in feature_names
        assert "volume_ratio_5d" in feature_names  # 包含窗口参数

        # 验证标签信息
        assert metadata["label"]["name"] == "excess_return"
        assert metadata["label"]["type"] == "regression"

        # 验证切分信息
        assert metadata["split"]["method"] == "fixed_window"
        assert metadata["split"]["train_end"] == "20240121"
        assert metadata["split"]["valid_end"] == "20240125"

        # 验证统计信息
        assert "statistics" in metadata
        assert metadata["statistics"]["train_samples"] > 0
        assert metadata["statistics"]["valid_samples"] > 0
        assert metadata["statistics"]["test_samples"] > 0
        assert "nan_ratio" in metadata["statistics"]

    def test_excess_return_label_with_benchmark(
        self,
        sample_stock_cache: Path,
        sample_benchmark_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试超额收益标签（需要基准数据）"""
        config = DatasetConfig(
            name="test_excess",
            symbols=["600519"],
            start_date="20240101",
            end_date="20240130",
            features=[Return1D()],
            label_type="excess_return",
            benchmark_code="000300",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 验证数据集生成成功
        train_df = pd.read_parquet(output_path / "train.parquet")
        assert "label" in train_df.columns

        # 验证标签不全是 NaN（应该有有效的超额收益值）
        assert not train_df["label"].isna().all()

    def test_forward_return_label_without_benchmark(
        self,
        sample_stock_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试前向收益标签（不需要基准数据）"""
        config = DatasetConfig(
            name="test_forward",
            symbols=["600519"],
            start_date="20240101",
            end_date="20240130",
            features=[Return1D()],
            label_type="forward_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 验证数据集生成成功
        train_df = pd.read_parquet(output_path / "train.parquet")
        assert "label" in train_df.columns

        # 验证标签不全是 NaN
        assert not train_df["label"].isna().all()

    def test_quality_check_warns_high_nan(
        self,
        sample_stock_cache: Path,
        temp_output_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """测试数据质量检查（NaN 比例过高时应警告）"""
        # 使用需要长窗口的特征（会产生较多 NaN）
        config = DatasetConfig(
            name="test_quality",
            symbols=["600519"],
            start_date="20240101",
            end_date="20240130",
            features=[Return20D()],  # 20 日动量需要更多历史数据
            label_type="forward_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
            nan_threshold=0.1,  # 降低阈值以触发警告
        )

        builder = DatasetBuilder(config)
        with caplog.at_level("WARNING"):
            builder.build()

        # TG-17: pin DatasetBuilder._quality_check warning copy (builder.py),
        # not a bare "NaN" substring that can match unrelated logs.
        log_text = caplog.text
        assert "以下列的 NaN 比例超过" in log_text


class TestDatasetBuilderEdgeCases:
    """测试数据集构建器的边界情况"""

    def test_empty_symbol_list(self, temp_cache_dir: Path, temp_output_dir: Path) -> None:
        """测试空股票列表"""
        config = DatasetConfig(
            name="test_empty",
            symbols=[],
            start_date="20240101",
            end_date="20240130",
            features=[Return1D()],
            label_type="forward_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            cache_dir=temp_cache_dir,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)

        # 应该能够处理（虽然没有数据）
        with pytest.raises(ValueError, match="数据集为空：没有加载到任何股票数据"):
            builder.build()

    def test_single_symbol(
        self,
        sample_stock_cache: Path,
        temp_output_dir: Path,
    ) -> None:
        """测试单只股票"""
        config = DatasetConfig(
            name="test_single",
            symbols=["600519"],
            start_date="20240101",
            end_date="20240130",
            features=[Return1D()],
            label_type="forward_return",
            train_end_date="20240121",
            valid_end_date="20240125",
            source="tushare",
            cache_dir=sample_stock_cache,
            output_dir=temp_output_dir,
        )

        builder = DatasetBuilder(config)
        output_path = builder.build()

        # 验证数据集生成成功
        train_df = pd.read_parquet(output_path / "train.parquet")
        assert len(train_df["symbol"].unique()) == 1
        assert train_df["symbol"].iloc[0] == "600519"


def test_builder_with_tushare_bare_symbol(
    sample_benchmark_cache: Path,
    temp_output_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TuShare source accepts bare 6-digit symbols via symbol_to_ts_code."""
    import ashare_infra.data.tushare_source as ts_src

    symbol = "600000"
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    fake_df = pd.DataFrame(
        {
            "open": [1, 1.1, 1.2, 1.3, 1.4],
            "high": [1.1, 1.2, 1.3, 1.4, 1.5],
            "low": [0.9, 1.0, 1.1, 1.2, 1.3],
            "close": [1.05, 1.15, 1.25, 1.35, 1.45],
            "volume": [100, 110, 120, 130, 140],
            "amount": [1000, 1100, 1200, 1300, 1400],
        },
        index=dates,
    )
    calls: list[str] = []

    def fake_loader(req, cache_dir, refresh=False):
        _ = cache_dir, refresh
        calls.append(req.symbol)
        return fake_df

    monkeypatch.setattr(ts_src, "load_or_fetch_daily_bars", fake_loader)

    config = DatasetConfig(
        name="test_tushare_bare_symbol",
        symbols=[symbol],
        start_date="20240101",
        end_date="20240105",
        features=[Return1D()],
        label_type="forward_return",
        train_end_date="20240103",
        valid_end_date="20240104",
        cache_dir=sample_benchmark_cache,
        output_dir=temp_output_dir,
        source="tushare",
    )

    builder = DatasetBuilder(config)
    output_path = builder.build()

    assert (output_path / "train.parquet").exists()
    assert calls == ["600000.SH"]


def test_builder_with_tushare_source(
    sample_benchmark_cache: Path,
    temp_output_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证数据源切换到 TuShare（经 DataLake；AO-O2）"""
    from ashare_infra.lake import DataLake

    symbol = "600000.SH"
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    fake_df = pd.DataFrame(
        {
            "open": [1, 1.1, 1.2, 1.3, 1.4],
            "high": [1.1, 1.2, 1.3, 1.4, 1.5],
            "low": [0.9, 1.0, 1.1, 1.2, 1.3],
            "close": [1.05, 1.15, 1.25, 1.35, 1.45],
            "volume": [100, 110, 120, 130, 140],
            "amount": [1000, 1100, 1200, 1300, 1400],
        },
        index=dates,
    )
    fake_df.index.name = "date"

    calls: list[str] = []

    def fake_load_daily_bars(
        self,
        sym,
        start,
        end,
        *,
        source=None,
        adjust="qfq",
        as_of=None,
    ):
        _ = self, start, end, source, adjust, as_of
        calls.append(sym)
        return fake_df.copy()

    monkeypatch.setattr(DataLake, "load_daily_bars", fake_load_daily_bars)

    config = DatasetConfig(
        name="test_tushare_source",
        symbols=[symbol],
        start_date="20240101",
        end_date="20240105",
        features=[Return1D()],
        label_type="forward_return",
        train_end_date="20240103",
        valid_end_date="20240104",
        cache_dir=sample_benchmark_cache,
        output_dir=temp_output_dir,
        source="tushare",
    )

    builder = DatasetBuilder(config)
    output_path = builder.build()

    assert (output_path / "train.parquet").exists()
    assert calls == [symbol_to_ts_code(symbol)]


def test_builder_with_odp_source(
    sample_benchmark_cache: Path,
    temp_output_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证数据源切换到 ODP（经 DataLake；AO-O2）"""
    from ashare_infra.lake import DataLake

    symbol = "600519"
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    fake_df = pd.DataFrame(
        {
            "open": [1, 1.1, 1.2, 1.3, 1.4],
            "high": [1.1, 1.2, 1.3, 1.4, 1.5],
            "low": [0.9, 1.0, 1.1, 1.2, 1.3],
            "close": [1.05, 1.15, 1.25, 1.35, 1.45],
            "volume": [100, 110, 120, 130, 140],
            "amount": [1000, 1100, 1200, 1300, 1400],
        },
        index=dates,
    )
    fake_df.index.name = "date"

    calls: list[str] = []

    def fake_load_daily_bars(
        self,
        sym,
        start,
        end,
        *,
        source=None,
        adjust="qfq",
        as_of=None,
    ):
        _ = self, start, end, source, adjust, as_of
        calls.append(sym)
        return fake_df.copy()

    monkeypatch.setattr(DataLake, "load_daily_bars", fake_load_daily_bars)

    config = DatasetConfig(
        name="test_odp_source",
        symbols=[symbol],
        start_date="20240101",
        end_date="20240105",
        features=[Return1D()],
        label_type="forward_return",
        train_end_date="20240103",
        valid_end_date="20240104",
        cache_dir=sample_benchmark_cache,
        output_dir=temp_output_dir,
        source="odp",
    )

    builder = DatasetBuilder(config)
    output_path = builder.build()

    assert (output_path / "train.parquet").exists()
    assert calls == [symbol_to_odp_equity_symbol(symbol)]
