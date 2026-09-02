"""测试标签定义

验证标签计算的正确性和时间对齐规则。
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
import pandas as pd
import pytest

from ashare_lab.labels.excess_return import ExcessReturnLabel, ForwardReturnLabel
from ashare_lab.labels.multi_horizon import MultiHorizonLabel


@pytest.fixture
def sample_stock_data() -> pd.DataFrame:
    """创建测试用的股票样本数据"""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    # 股票价格：100, 102, 101, 105, 103, 108, 107, 110, 112, 115
    close_prices = np.array([100, 102, 101, 105, 103, 108, 107, 110, 112, 115], dtype=float)

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
def sample_benchmark_data() -> pd.DataFrame:
    """创建测试用的基准样本数据（沪深300）"""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    # 基准价格：3000, 3010, 3005, 3020, 3015, 3030, 3025, 3040, 3045, 3050
    close_prices = np.array(
        [3000, 3010, 3005, 3020, 3015, 3030, 3025, 3040, 3045, 3050], dtype=float
    )

    return pd.DataFrame(
        {
            "open": close_prices - 5,
            "high": close_prices + 10,
            "low": close_prices - 10,
            "close": close_prices,
            "volume": 100000000,
            "amount": close_prices * 100000000,
        },
        index=dates,
    )


class TestForwardReturnLabel:
    """测试前向收益率标签"""

    def test_compute_correctness(self, sample_stock_data: pd.DataFrame) -> None:
        """测试计算正确性"""
        label = ForwardReturnLabel()
        result = label.compute(sample_stock_data)

        # 验证标签名称
        assert label.name == "forward_return"

        # 验证索引对齐
        assert len(result) == len(sample_stock_data)
        assert (result.index == sample_stock_data.index).all()

        # 验证最后一个值为 NaN（无未来数据）
        assert pd.isna(result.iloc[-1])

        # 验证第 1 个值（索引 0）的计算
        # label[2024-01-01] = (close[2024-01-02] / close[2024-01-01]) - 1
        # = (102 / 100) - 1 = 0.02
        expected = (sample_stock_data["close"].iloc[1] / sample_stock_data["close"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[0], expected, rtol=1e-9)

    def test_time_alignment(self, sample_stock_data: pd.DataFrame) -> None:
        """测试时间对齐（label[t] 使用 t+1 的收益）"""
        label = ForwardReturnLabel()
        result = label.compute(sample_stock_data)

        # 验证 2024-01-05 的标签值（索引 4）
        # 应该使用 2024-01-06 和 2024-01-05 的收盘价
        date_idx = 4
        expected = (sample_stock_data["close"].iloc[5] / sample_stock_data["close"].iloc[4]) - 1.0
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

        # 确保没有使用当日（2024-01-05）的收益
        # 如果使用了当日收益，结果会是 (103 / 105) - 1
        wrong_value = (
            sample_stock_data["close"].iloc[4] / sample_stock_data["close"].iloc[3]
        ) - 1.0
        assert not np.isclose(result.iloc[date_idx], wrong_value, rtol=1e-9)

    def test_forward_return_values(self, sample_stock_data: pd.DataFrame) -> None:
        """测试前几个标签值的正确性"""
        label = ForwardReturnLabel()
        result = label.compute(sample_stock_data)

        # label[0] = (102 / 100) - 1 = 0.02
        assert np.isclose(result.iloc[0], 0.02, rtol=1e-9)

        # label[1] = (101 / 102) - 1 ≈ -0.0098039
        expected_1 = (101.0 / 102.0) - 1.0
        assert np.isclose(result.iloc[1], expected_1, rtol=1e-9)

        # label[2] = (105 / 101) - 1 ≈ 0.0396039
        expected_2 = (105.0 / 101.0) - 1.0
        assert np.isclose(result.iloc[2], expected_2, rtol=1e-9)


class TestExcessReturnLabel:
    """测试超额收益标签"""

    def test_compute_correctness(
        self,
        sample_stock_data: pd.DataFrame,
        sample_benchmark_data: pd.DataFrame,
    ) -> None:
        """测试计算正确性"""
        label = ExcessReturnLabel()
        result = label.compute(sample_stock_data, sample_benchmark_data)

        # 验证标签名称
        assert label.name == "excess_return"

        # 验证索引对齐
        assert len(result) == len(sample_stock_data)
        assert (result.index == sample_stock_data.index).all()

        # 验证最后一个值为 NaN
        assert pd.isna(result.iloc[-1])

        # 验证第 1 个值（索引 0）的计算
        # stock_return[2024-01-02] = (102 / 100) - 1 = 0.02
        # benchmark_return[2024-01-02] = (3010 / 3000) - 1 ≈ 0.00333
        # excess_return = 0.02 - 0.00333 ≈ 0.01667
        stock_return = (
            sample_stock_data["close"].iloc[1] / sample_stock_data["close"].iloc[0]
        ) - 1.0
        benchmark_return = (
            sample_benchmark_data["close"].iloc[1] / sample_benchmark_data["close"].iloc[0]
        ) - 1.0
        expected = stock_return - benchmark_return
        assert np.isclose(result.iloc[0], expected, rtol=1e-9)

    def test_time_alignment(
        self,
        sample_stock_data: pd.DataFrame,
        sample_benchmark_data: pd.DataFrame,
    ) -> None:
        """测试时间对齐（label[t] 使用 t+1 的超额收益）"""
        label = ExcessReturnLabel()
        result = label.compute(sample_stock_data, sample_benchmark_data)

        # 验证 2024-01-05 的标签值（索引 4）
        # 应该使用 2024-01-06 和 2024-01-05 的数据
        date_idx = 4
        stock_return = (
            sample_stock_data["close"].iloc[5] / sample_stock_data["close"].iloc[4]
        ) - 1.0
        benchmark_return = (
            sample_benchmark_data["close"].iloc[5] / sample_benchmark_data["close"].iloc[4]
        ) - 1.0
        expected = stock_return - benchmark_return
        assert np.isclose(result.iloc[date_idx], expected, rtol=1e-9)

    def test_excess_return_calculation(
        self,
        sample_stock_data: pd.DataFrame,
        sample_benchmark_data: pd.DataFrame,
    ) -> None:
        """测试超额收益计算逻辑"""
        label = ExcessReturnLabel()
        result = label.compute(sample_stock_data, sample_benchmark_data)

        # 验证前几个标签值
        # label[0]: stock (102/100-1=0.02) - benchmark (3010/3000-1≈0.00333) ≈ 0.01667
        stock_ret_0 = (102.0 / 100.0) - 1.0
        bench_ret_0 = (3010.0 / 3000.0) - 1.0
        expected_0 = stock_ret_0 - bench_ret_0
        assert np.isclose(result.iloc[0], expected_0, rtol=1e-9)

        # label[1]: stock (101/102-1) - benchmark (3005/3010-1)
        stock_ret_1 = (101.0 / 102.0) - 1.0
        bench_ret_1 = (3005.0 / 3010.0) - 1.0
        expected_1 = stock_ret_1 - bench_ret_1
        assert np.isclose(result.iloc[1], expected_1, rtol=1e-9)


class TestLabelEdgeCases:
    """测试标签的边界情况"""

    def test_empty_dataframe(self) -> None:
        """测试空 DataFrame"""
        empty_df = pd.DataFrame(columns=["close"])

        # ForwardReturnLabel
        label_forward = ForwardReturnLabel()
        result_forward = label_forward.compute(empty_df)
        assert len(result_forward) == 0

        # ExcessReturnLabel
        label_excess = ExcessReturnLabel()
        result_excess = label_excess.compute(empty_df, empty_df)
        assert len(result_excess) == 0

    def test_single_day_data(self) -> None:
        """测试只有一天数据的情况"""
        single_df = pd.DataFrame(
            {"close": [100.0]},
            index=pd.date_range("2024-01-01", periods=1, freq="D"),
        )

        # ForwardReturnLabel 应该返回 NaN（无未来数据）
        label_forward = ForwardReturnLabel()
        result_forward = label_forward.compute(single_df)
        assert len(result_forward) == 1
        assert pd.isna(result_forward.iloc[0])

        # ExcessReturnLabel 也应该返回 NaN
        label_excess = ExcessReturnLabel()
        result_excess = label_excess.compute(single_df, single_df)
        assert len(result_excess) == 1
        assert pd.isna(result_excess.iloc[0])


@pytest.fixture
def sample_multi_data() -> pd.DataFrame:
    """跨年且包含停牌/缺价的样本数据"""
    dates = pd.date_range("2023-12-25", periods=20, freq="D")
    close = pd.Series(np.linspace(100, 119, num=20), index=dates)
    close.iloc[12] = np.nan  # 缺价

    volume = pd.Series(1_000_000, index=dates, dtype=float)
    volume.iloc[5] = 0  # 停牌

    return pd.DataFrame({"close": close, "volume": volume}, index=dates)


class TestMultiHorizonLabel:
    """测试多跨度标签"""

    def test_basic_computation(self, sample_multi_data: pd.DataFrame) -> None:
        label = MultiHorizonLabel()
        result = label.compute(sample_multi_data)

        assert list(result.columns) == ["label_3d", "label_5d", "label_10d"]
        # 正常窗口
        expected_3d_0 = (sample_multi_data["close"].iloc[3] / sample_multi_data["close"].iloc[0]) - 1
        assert np.isclose(result.iloc[0]["label_3d"], expected_3d_0, rtol=1e-9)

    def test_suspend_or_nan_window(self, sample_multi_data: pd.DataFrame) -> None:
        label = MultiHorizonLabel()
        result = label.compute(sample_multi_data)

        # index 4 的 3 日窗口包含停牌日 (index 5)
        assert pd.isna(result.loc[result.index[4], "label_3d"])

        # index 3 的 10 日窗口包含缺价 (index 12)
        assert pd.isna(result.loc[result.index[3], "label_10d"])

    def test_cross_year_alignment(self, sample_multi_data: pd.DataFrame) -> None:
        label = MultiHorizonLabel()
        result = label.compute(sample_multi_data)

        # 2023-12-31 对应索引 6
        idx = pd.Timestamp("2023-12-31")
        # 窗口不含停牌/缺价，应该有值
        assert pd.notna(result.loc[idx, "label_5d"])

    def test_compute_and_save(self, sample_multi_data: pd.DataFrame, tmp_path: Path) -> None:
        label = MultiHorizonLabel()
        out_path = tmp_path / "labels.parquet"
        written = label.compute_and_save(sample_multi_data, out_path)

        assert written.exists()
        loaded = pd.read_parquet(written)
        assert list(loaded.columns) == ["label_3d", "label_5d", "label_10d"]

    def test_with_nan_values(self) -> None:
        """测试包含 NaN 值的数据"""
        df_with_nan = pd.DataFrame(
            {"close": [100.0, np.nan, 102.0, 103.0]},
            index=pd.date_range("2024-01-01", periods=4, freq="D"),
        )

        label = ForwardReturnLabel()
        result = label.compute(df_with_nan)

        # NaN 传播分析：
        # pct_change(1): [NaN, (NaN/100-1)=NaN, (102/NaN-1)=NaN, (103/102-1)=有效值]
        # shift(-1): [NaN, NaN, 有效值, NaN]

        # label[0] 应该是 NaN（shift 后来自 index 1 的 NaN）
        assert pd.isna(result.iloc[0])

        # label[1] 应该是 NaN（shift 后来自 index 2 的 NaN）
        assert pd.isna(result.iloc[1])

        # label[2] 应该是有效值（shift 后来自 index 3）
        # = (103 / 102 - 1)
        expected_2 = (103.0 / 102.0) - 1.0
        assert np.isclose(result.iloc[2], expected_2, rtol=1e-9)

        # label[3] 应该是 NaN（无未来数据）
        assert pd.isna(result.iloc[3])

    def test_misaligned_benchmark(self, sample_stock_data: pd.DataFrame) -> None:
        """测试基准数据与股票数据日期不完全对齐的情况"""
        # 创建一个日期范围不同的基准数据
        benchmark_dates = pd.date_range("2024-01-02", periods=8, freq="D")  # 缺少第一天
        benchmark_df = pd.DataFrame(
            {"close": np.arange(3010, 3090, 10, dtype=float)},
            index=benchmark_dates,
        )

        label = ExcessReturnLabel()
        result = label.compute(sample_stock_data, benchmark_df)

        # 第一天的标签应该是 NaN（基准数据缺失前一天）
        assert pd.isna(result.iloc[0])

        # 后续有对齐数据的日期应该有有效值
        # 需要验证 reindex 后是否正确对齐
        assert len(result) == len(sample_stock_data)

    def test_label_mode_close_to_close(self, sample_stock_data: pd.DataFrame) -> None:
        """测试 close_to_close 模式（旧默认行为）"""
        label = MultiHorizonLabel(horizons=(1,), label_mode="close_to_close")
        result = label.compute(sample_stock_data)

        # label[0] = close[1] / close[0] - 1 = 102/100 - 1 = 0.02
        expected = (sample_stock_data["close"].iloc[1] / sample_stock_data["close"].iloc[0]) - 1.0
        assert np.isclose(result.iloc[0]["label_1d"], expected, rtol=1e-9)

        # label[4] = close[5] / close[4] - 1 = 108/103 - 1
        expected_4 = (sample_stock_data["close"].iloc[5] / sample_stock_data["close"].iloc[4]) - 1.0
        assert np.isclose(result.iloc[4]["label_1d"], expected_4, rtol=1e-9)

    def test_label_mode_next_open_to_open(self, sample_stock_data: pd.DataFrame) -> None:
        """测试 next_open_to_open 模式（新推荐，与交易协议一致）"""
        label = MultiHorizonLabel(horizons=(1,), label_mode="next_open_to_open")
        result = label.compute(sample_stock_data)

        # label[0] = open[2] / open[1] - 1
        # open[1] = 101.5, open[2] = 100.5
        # 这里 sample_stock_data 的 open = close - 0.5
        open_prices = sample_stock_data["close"] - 0.5
        expected = (open_prices.iloc[2] / open_prices.iloc[1]) - 1.0
        assert np.isclose(result.iloc[0]["label_1d"], expected, rtol=1e-9)

        # label[4] = open[6] / open[5] - 1
        # open[5] = 107.5, open[6] = 106.5
        expected_4 = (open_prices.iloc[6] / open_prices.iloc[5]) - 1.0
        assert np.isclose(result.iloc[4]["label_1d"], expected_4, rtol=1e-9)

    def test_label_mode_comparison(self, sample_stock_data: pd.DataFrame) -> None:
        """测试两种模式的结果应该不同（验证模式切换生效）"""
        label_close = MultiHorizonLabel(horizons=(5,), label_mode="close_to_close")
        label_open = MultiHorizonLabel(horizons=(5,), label_mode="next_open_to_open")

        result_close = label_close.compute(sample_stock_data)
        result_open = label_open.compute(sample_stock_data)

        # 验证 close_to_close 的第一个值
        # label[0] = close[5] / close[0] - 1 = 108/100 - 1 = 0.08
        expected_close = (sample_stock_data["close"].iloc[5] / sample_stock_data["close"].iloc[0]) - 1.0
        assert np.isclose(result_close.iloc[0]["label_5d"], expected_close, rtol=1e-9)

        # 验证 next_open_to_open 的第一个值
        # label[0] = open[6] / open[1] - 1
        open_prices = sample_stock_data["close"] - 0.5
        expected_open = (open_prices.iloc[6] / open_prices.iloc[1]) - 1.0
        assert np.isclose(result_open.iloc[0]["label_5d"], expected_open, rtol=1e-9)

        # 两种模式的第一个值应该不同（因为用的价格列不同）
        assert not np.isclose(
            result_close.iloc[0]["label_5d"],
            result_open.iloc[0]["label_5d"],
            rtol=1e-6,
        )

    def test_label_mode_requires_open_column(self) -> None:
        """测试 next_open_to_open 模式需要 open 列"""
        df_without_open = pd.DataFrame(
            {"close": [100, 102, 101], "volume": [1000, 1000, 1000]},
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )

        label = MultiHorizonLabel(horizons=(1,), label_mode="next_open_to_open")

        # 应该抛出 KeyError，因为缺少 open 列
        with pytest.raises(KeyError, match="next_open_to_open mode requires 'open' column"):
            label.compute(df_without_open)

    def test_label_mode_invalid_value(self, sample_stock_data: pd.DataFrame) -> None:
        """测试无效的 label_mode 值"""
        label = MultiHorizonLabel(horizons=(1,), label_mode="invalid_mode")

        with pytest.raises(ValueError, match="不支持的 label_mode"):
            label.compute(sample_stock_data)


class TestSuspensionGapMask:
    """4.3：行间停牌（无行断档）标签应置 NaN。"""

    def test_gap_detected_and_label_nan(self) -> None:
        # 构造含真实停牌（行间断档 18 天）的序列：2024-01-01 起每日一行，
        # 在 index 3 之后断档 18 天（停牌），复牌日为 index 4。
        dates = list(pd.date_range("2024-01-01", periods=4, freq="D")) + [
            pd.Timestamp("2024-01-05") + pd.Timedelta(days=18)
        ] + list(pd.date_range("2024-01-24", periods=6, freq="D"))
        n = len(dates)
        df = pd.DataFrame(
            {
                "open": np.arange(n, dtype=float) + 10,
                "high": np.arange(n, dtype=float) + 11,
                "low": np.arange(n, dtype=float) + 9,
                "close": np.arange(n, dtype=float) + 10,
                "volume": np.full(n, 1_000_000.0),
            },
            index=pd.DatetimeIndex(dates),
        )
        label = MultiHorizonLabel(horizons=[3, 5])  # 只用 3/5 待 3d 窗口跨停牌
        result = label.compute(df)
        # index 2（停牌前最后一天）：3 日窗口跨 18 天断档 → NaN
        assert pd.isna(result.iloc[2]["label_3d"]), "跨停牌标签应为 NaN"
        # index 4（复牌日）之前的标签不跨停牌（index 0 的 3 日窗口 = 0,1,2 无断档）
        assert pd.notna(result.iloc[0]["label_3d"]), "无停牌窗口标签应有效"

    def test_normal_gap_under_threshold_kept(self) -> None:
        # 正常 1 周缺口（<15 天）不应误杀
        dates = list(pd.date_range("2024-01-01", periods=3, freq="D")) + [
            pd.Timestamp("2024-01-04") + pd.Timedelta(days=7)
        ] + list(pd.date_range("2024-01-12", periods=5, freq="D"))
        n = len(dates)
        df = pd.DataFrame(
            {
                "close": np.arange(n, dtype=float) + 10,
                "volume": np.full(n, 1_000_000.0),
            },
            index=pd.DatetimeIndex(dates),
        )
        label = MultiHorizonLabel(horizons=[3])
        result = label.compute(df)
        assert pd.notna(result.iloc[0]["label_3d"]), "7 天缺口不应触发停牌标记"
