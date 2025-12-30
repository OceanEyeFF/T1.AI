"""测试量价特征

验证量价特征计算的正确性和时间对齐规则。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.features.volume import AmountChange, VolumeChange, VolumeRatio


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
            "volume": np.arange(1000000, 1030000, 1000, dtype=float),  # 递增的成交量
            "amount": close_prices * 1000000,  # 成交额 = 价格 * 固定量
        },
        index=dates,
    )


class TestVolumeRatio:
    """测试量比特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        feature = VolumeRatio(window=5)
        result = feature.compute(sample_data)

        # 验证特征名称
        assert feature.name == "volume_ratio_5d"

        # 验证索引对齐
        assert len(result) == len(sample_data)
        assert (result.index == sample_data.index).all()

        # 验证第 1 个值为 NaN（shift(1) 导致）
        assert pd.isna(result.iloc[0])

        # 验证第 6 个值（索引 5）的计算
        # volume_ratio[2024-01-06] = volume[2024-01-05] / mean(volume[2024-01-01:2024-01-05])
        volume_t_minus_1 = sample_data["volume"].iloc[4]  # 2024-01-05
        rolling_mean = sample_data["volume"].iloc[0:5].mean()  # 2024-01-01 到 2024-01-05
        expected = volume_t_minus_1 / rolling_mean
        assert np.isclose(result.iloc[5], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        """测试时间对齐（t 日特征不使用 t 日数据）"""
        feature = VolumeRatio(window=5)
        result = feature.compute(sample_data)

        # 验证 2024-01-10 的特征值（索引 9）
        # 应该使用 2024-01-09 的成交量和 2024-01-05 到 2024-01-09 的均值
        date_idx = 9
        volume_t_minus_1 = sample_data["volume"].iloc[8]  # 2024-01-09
        rolling_mean = sample_data["volume"].iloc[4:9].mean()  # 2024-01-05 到 2024-01-09
        expected = volume_t_minus_1 / rolling_mean
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日（2024-01-10）的数据
        volume_t = sample_data["volume"].iloc[9]  # 2024-01-10
        rolling_mean_wrong = sample_data["volume"].iloc[5:10].mean()  # 包含当日
        wrong_value = volume_t / rolling_mean_wrong
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)

    def test_different_windows(self, sample_data: pd.DataFrame) -> None:
        """测试不同窗口期"""
        # 测试窗口 = 3
        feature_3d = VolumeRatio(window=3)
        result_3d = feature_3d.compute(sample_data)
        assert feature_3d.name == "volume_ratio_3d"
        assert pd.isna(result_3d.iloc[0])  # shift(1)
        assert pd.notna(result_3d.iloc[3])  # 3 日窗口 + shift(1)

        # 测试窗口 = 10
        feature_10d = VolumeRatio(window=10)
        result_10d = feature_10d.compute(sample_data)
        assert feature_10d.name == "volume_ratio_10d"
        assert pd.notna(result_10d.iloc[10])  # 10 日窗口 + shift(1)


class TestAmountChange:
    """测试成交额变化特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        feature = AmountChange()
        result = feature.compute(sample_data)

        # 验证特征名称
        assert feature.name == "amount_change"

        # 验证索引对齐
        assert len(result) == len(sample_data)

        # 验证前 2 个值为 NaN（窗口期不足 + shift(1)）
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # 验证第 3 个值（索引 2）的计算
        # amount_change[2024-01-03] = (amount[2024-01-02] / amount[2024-01-01]) - 1
        expected = (sample_data["amount"].iloc[1] / sample_data["amount"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[2], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        """测试时间对齐（t 日特征不使用 t 日数据）"""
        feature = AmountChange()
        result = feature.compute(sample_data)

        # 验证 2024-01-05 的特征值（索引 4）
        # 应该使用 2024-01-04 和 2024-01-03 的成交额
        date_idx = 4
        expected = (sample_data["amount"].iloc[3] / sample_data["amount"].iloc[2]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日数据
        wrong_value = (sample_data["amount"].iloc[4] / sample_data["amount"].iloc[3]) - 1.0
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)


class TestVolumeChange:
    """测试成交量变化特征"""

    def test_compute_correctness(self, sample_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        feature = VolumeChange()
        result = feature.compute(sample_data)

        # 验证特征名称
        assert feature.name == "volume_change"

        # 验证索引对齐
        assert len(result) == len(sample_data)

        # 验证前 2 个值为 NaN
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # 验证第 3 个值的计算
        expected = (sample_data["volume"].iloc[1] / sample_data["volume"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[2], expected, rtol=1e-9)

    def test_time_alignment(self, sample_data: pd.DataFrame) -> None:
        """测试时间对齐"""
        feature = VolumeChange()
        result = feature.compute(sample_data)

        # 验证 2024-01-05 的特征值
        date_idx = 4
        expected = (sample_data["volume"].iloc[3] / sample_data["volume"].iloc[2]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日数据
        wrong_value = (sample_data["volume"].iloc[4] / sample_data["volume"].iloc[3]) - 1.0
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)


class TestVolumeFeatureEdgeCases:
    """测试量价特征的边界情况"""

    def test_empty_dataframe(self) -> None:
        """测试空 DataFrame"""
        empty_df = pd.DataFrame(columns=["volume", "amount"])

        feature_ratio = VolumeRatio(window=5)
        result_ratio = feature_ratio.compute(empty_df)
        assert len(result_ratio) == 0

        feature_change = VolumeChange()
        result_change = feature_change.compute(empty_df)
        assert len(result_change) == 0

    def test_insufficient_data(self) -> None:
        """测试数据不足的情况"""
        # 只有 3 天数据
        short_df = pd.DataFrame(
            {
                "volume": [1000000.0, 1001000.0, 1002000.0],
                "amount": [100000000.0, 101000000.0, 102000000.0],
            },
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )

        # VolumeChange 应该只有最后一个值有效
        feature_change = VolumeChange()
        result_change = feature_change.compute(short_df)
        assert pd.isna(result_change.iloc[0])
        assert pd.isna(result_change.iloc[1])
        assert pd.notna(result_change.iloc[2])

        # VolumeRatio(window=5) 因为窗口不足，会使用 min_periods=1
        feature_ratio = VolumeRatio(window=5)
        result_ratio = feature_ratio.compute(short_df)
        assert pd.isna(result_ratio.iloc[0])  # shift(1)
        assert pd.notna(result_ratio.iloc[1])  # min_periods=1 允许计算

    def test_with_nan_values(self) -> None:
        """测试包含 NaN 值的数据"""
        df_with_nan = pd.DataFrame(
            {
                "volume": [1000000.0, np.nan, 1002000.0, 1003000.0, 1004000.0],
                "amount": [100000000.0, np.nan, 102000000.0, 103000000.0, 104000000.0],
            },
            index=pd.date_range("2024-01-01", periods=5, freq="D"),
        )

        # VolumeChange 测试
        feature_change = VolumeChange()
        result_change = feature_change.compute(df_with_nan)

        # NaN 会传播
        assert pd.isna(result_change.iloc[0])
        assert pd.isna(result_change.iloc[1])
        assert pd.isna(result_change.iloc[2])
        assert pd.isna(result_change.iloc[3])
        assert pd.notna(result_change.iloc[4])  # 有效值

    def test_zero_volume(self) -> None:
        """测试成交量为零的情况"""
        df_with_zero = pd.DataFrame(
            {
                "volume": [1000000.0, 0.0, 1002000.0, 1003000.0],
                "amount": [100000000.0, 0.0, 102000000.0, 103000000.0],
            },
            index=pd.date_range("2024-01-01", periods=4, freq="D"),
        )

        feature_change = VolumeChange()
        result_change = feature_change.compute(df_with_zero)

        # 除以零会产生 inf
        assert pd.isna(result_change.iloc[0])
        assert pd.isna(result_change.iloc[1])
        # iloc[2] 应该是 inf (0 / 1000000 - 1 = -1, shift后是 0/0-1)
        # 实际上 iloc[2] 是 (0 / 1000000 - 1) shift 到这里，所以是 -1
        assert np.isclose(result_change.iloc[2], -1.0, rtol=1e-9)
