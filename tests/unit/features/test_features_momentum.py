"""测试价格动量特征

验证特征计算的正确性和时间对齐规则。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.features.momentum import (
    Return1D,
    Return5D,
    Return10D,
    Return20D,
    Return60D,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """创建测试用的样本数据

    生成 30 天的模拟行情数据，便于测试不同窗口的特征。
    """
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    # 创建简单的价格序列：100, 101, 102, ..., 129
    close_prices = np.arange(100, 130, dtype=float)

    return pd.DataFrame(
        {
            "open": close_prices - 0.5,
            "high": close_prices + 1.0,
            "low": close_prices - 1.0,
            "close": close_prices,
            "volume": 1000000,
            "amount": close_prices * 1000000,
        },
        index=dates,
    )


@pytest.fixture
def long_sample_data() -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=120, freq="D")
    close_prices = np.linspace(50, 170, num=120)
    return pd.DataFrame(
        {
            "open": close_prices - 0.5,
            "high": close_prices + 1.0,
            "low": close_prices - 1.0,
            "close": close_prices,
            "volume": 1000000,
            "amount": close_prices * 1000000,
        },
        index=dates,
    )


class TestReturn1D:
    """测试 1 日收益率特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        feature = Return1D()
        result = feature.compute(sample_data)

        # 验证特征名称
        assert feature.name == "return_1d"

        # 验证索引对齐
        assert len(result) == len(sample_data)
        assert (result.index == sample_data.index).all()

        # 验证前 2 个值为 NaN（窗口期不足 + shift(1)）
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # 验证第 3 个值（索引 2）的计算
        # return_1d[2024-01-03] = (close[2024-01-02] / close[2024-01-01]) - 1
        # = (101 / 100) - 1 = 0.01
        expected = (sample_data["close"].iloc[1] / sample_data["close"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[2], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        """测试时间对齐（t 日特征不使用 t 日数据）"""
        feature = Return1D()
        result = feature.compute(sample_data)

        # 验证 2024-01-05 的特征值
        # 应该使用 2024-01-04 和 2024-01-03 的收盘价
        date_idx = 4  # 2024-01-05 是第 5 个交易日（索引 4）
        expected = (sample_data["close"].iloc[3] / sample_data["close"].iloc[2]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日（2024-01-05）的数据
        # 如果使用了当日数据，结果会是 (104 / 103) - 1
        wrong_value = (sample_data["close"].iloc[4] / sample_data["close"].iloc[3]) - 1.0
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)


class TestReturn5D:
    """测试 5 日收益率特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        feature = Return5D()
        result = feature.compute(sample_data)

        # 验证特征名称
        assert feature.name == "return_5d"

        # 验证索引对齐
        assert len(result) == len(sample_data)

        # 验证前 6 个值为 NaN（5 日窗口 + shift(1)）
        for i in range(6):
            assert pd.isna(result.iloc[i])

        # 验证第 7 个值（索引 6）的计算
        # return_5d[2024-01-07] = (close[2024-01-06] / close[2024-01-01]) - 1
        # = (105 / 100) - 1 = 0.05
        expected = (sample_data["close"].iloc[5] / sample_data["close"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[6], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        """测试时间对齐（t 日特征不使用 t 日数据）"""
        feature = Return5D()
        result = feature.compute(sample_data)

        # 验证 2024-01-10 的特征值（索引 9）
        # 应该使用 2024-01-09 和 2024-01-04 的收盘价
        date_idx = 9
        expected = (sample_data["close"].iloc[8] / sample_data["close"].iloc[3]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日数据
        wrong_value = (sample_data["close"].iloc[9] / sample_data["close"].iloc[4]) - 1.0
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)


class TestReturn20D:
    """测试 20 日收益率特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        feature = Return20D()
        result = feature.compute(sample_data)

        # 验证特征名称
        assert feature.name == "return_20d"

        # 验证索引对齐
        assert len(result) == len(sample_data)

        # 验证前 21 个值为 NaN（20 日窗口 + shift(1)）
        for i in range(21):
            assert pd.isna(result.iloc[i])

        # 验证第 22 个值（索引 21）的计算
        # return_20d[2024-01-22] = (close[2024-01-21] / close[2024-01-01]) - 1
        # = (120 / 100) - 1 = 0.20
        expected = (sample_data["close"].iloc[20] / sample_data["close"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[21], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        """测试时间对齐（t 日特征不使用 t 日数据）"""
        feature = Return20D()
        result = feature.compute(sample_data)

        # 验证 2024-01-25 的特征值（索引 24）
        # 应该使用 2024-01-24 和 2024-01-04 的收盘价
        date_idx = 24
        expected = (sample_data["close"].iloc[23] / sample_data["close"].iloc[3]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日数据
        wrong_value = (sample_data["close"].iloc[24] / sample_data["close"].iloc[4]) - 1.0
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)


class TestReturn10D:
    """测试 10 日收益率特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        feature = Return10D()
        result = feature.compute(sample_data)

        assert feature.name == "return_10d"
        for i in range(11):
            assert pd.isna(result.iloc[i])

        expected = (sample_data["close"].iloc[10] / sample_data["close"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[11], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        feature = Return10D()
        result = feature.compute(sample_data)
        date_idx = 15
        expected = (sample_data["close"].iloc[14] / sample_data["close"].iloc[4]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)


class TestReturn60D:
    """测试 60 日收益率特征"""

    def test_compute_correctness(self, long_sample_data: pd.DataFrame) -> None:
        feature = Return60D()
        result = feature.compute(long_sample_data)

        assert feature.name == "return_60d"
        # 前 61 个值应为 NaN（60 日窗口 + shift）
        assert result.iloc[:61].isna().all()

        idx = 70
        expected = (long_sample_data["close"].iloc[69] / long_sample_data["close"].iloc[9]) - 1.0
        assert np.isclose(result.iloc[idx], expected, rtol=1e-9)


class TestFeatureEdgeCases:
    """测试特征的边界情况"""

    def test_empty_dataframe(self) -> None:
        """测试空 DataFrame"""
        empty_df = pd.DataFrame(columns=["close"])
        feature = Return1D()
        result = feature.compute(empty_df)
        assert len(result) == 0

    def test_insufficient_data(self) -> None:
        """测试数据不足的情况"""
        # 只有 3 天数据
        short_df = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0]},
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )

        # Return1D 应该只有最后一个值有效
        feature1d = Return1D()
        result1d = feature1d.compute(short_df)
        assert pd.isna(result1d.iloc[0])
        assert pd.isna(result1d.iloc[1])
        assert pd.notna(result1d.iloc[2])

        # Return5D 应该全部为 NaN（数据不足 5 日）
        feature5d = Return5D()
        result5d = feature5d.compute(short_df)
        assert result5d.isna().all()

    def test_with_nan_values(self) -> None:
        """测试包含 NaN 值的数据"""
        df_with_nan = pd.DataFrame(
            {"close": [100.0, np.nan, 102.0, 103.0, 104.0]},
            index=pd.date_range("2024-01-01", periods=5, freq="D"),
        )

        feature = Return1D()
        result = feature.compute(df_with_nan)

        # NaN 会传播到计算结果中
        # index 0, 1: 窗口不足（pct_change + shift）
        # index 2: NaN（102 / NaN - 1）
        # index 3: NaN（shift 后来自 index 2 的 NaN）
        # index 4: 有效值（103 / 102 - 1，shift 后来自 index 3）
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])
        assert pd.isna(result.iloc[3])
        assert pd.notna(result.iloc[4])  # 应该有有效值
