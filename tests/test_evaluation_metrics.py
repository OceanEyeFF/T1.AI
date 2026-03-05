"""测试评估指标

验证 Daily-CS IC 计算、汇总和月度聚合的正确性。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.evaluation import metrics


class TestDailyCSIC:
    """测试 Daily-CS IC 计算"""

    def test_calculate_daily_cs_ic_basic(self) -> None:
        """测试基本的 Daily-CS IC 计算"""
        # 创建测试数据：2个日期，每个日期3只股票
        dates = ["2024-01-02", "2024-01-03"]
        symbols = ["A", "B", "C"]

        index = pd.MultiIndex.from_product(
            [pd.to_datetime(dates), symbols],
            names=["date", "symbol"]
        )

        # 完美正相关的数据
        predictions = pd.Series([0.1, 0.2, 0.3, 0.05, 0.15, 0.25], index=index)
        labels = pd.Series([0.12, 0.22, 0.32, 0.06, 0.16, 0.26], index=index)

        daily_ic = metrics.calculate_daily_cs_ic(predictions, labels, method="pearson")

        # 验证结果
        assert len(daily_ic) == 2
        assert daily_ic.index.name == "date"
        # 完美正相关，IC 应该接近 1.0
        assert all(daily_ic > 0.99)

    def test_calculate_daily_cs_ic_negative_correlation(self) -> None:
        """测试负相关情况"""
        dates = ["2024-01-02"]
        symbols = ["A", "B", "C"]

        index = pd.MultiIndex.from_product(
            [pd.to_datetime(dates), symbols],
            names=["date", "symbol"]
        )

        # 完美负相关
        predictions = pd.Series([0.1, 0.2, 0.3], index=index)
        labels = pd.Series([-0.1, -0.2, -0.3], index=index)

        daily_ic = metrics.calculate_daily_cs_ic(predictions, labels)

        # IC 应该接近 -1.0
        assert len(daily_ic) == 1
        assert daily_ic.iloc[0] < -0.99

    def test_calculate_daily_cs_ic_spearman(self) -> None:
        """测试 Spearman 方法"""
        dates = ["2024-01-02"]
        symbols = ["A", "B", "C"]

        index = pd.MultiIndex.from_product(
            [pd.to_datetime(dates), symbols],
            names=["date", "symbol"]
        )

        # 单调但非线性关系
        predictions = pd.Series([1, 4, 9], index=index)
        labels = pd.Series([1, 2, 3], index=index)

        rank_ic = metrics.calculate_daily_cs_ic(predictions, labels, method="spearman")

        # Spearman 应该是完美正相关（都是单调递增）
        assert len(rank_ic) == 1
        assert rank_ic.iloc[0] > 0.99

    def test_calculate_daily_cs_ic_with_nan(self) -> None:
        """测试包含 NaN 值的情况"""
        dates = ["2024-01-02"]
        symbols = ["A", "B", "C", "D"]

        index = pd.MultiIndex.from_product(
            [pd.to_datetime(dates), symbols],
            names=["date", "symbol"]
        )

        predictions = pd.Series([0.1, 0.2, np.nan, 0.4], index=index)
        labels = pd.Series([0.12, np.nan, 0.32, 0.42], index=index)

        daily_ic = metrics.calculate_daily_cs_ic(predictions, labels)

        # 应该只使用有效的数据点（A 和 D）
        assert len(daily_ic) == 1
        # 两个点之间的相关系数是 1.0（完美正相关）
        assert abs(daily_ic.iloc[0] - 1.0) < 0.01

    def test_calculate_daily_cs_ic_empty_data(self) -> None:
        """测试空数据"""
        empty_series = pd.Series(
            dtype=float,
            index=pd.MultiIndex.from_tuples([], names=["date", "symbol"])
        )

        daily_ic = metrics.calculate_daily_cs_ic(empty_series, empty_series)

        assert daily_ic.empty

    def test_calculate_daily_cs_ic_invalid_index(self) -> None:
        """测试无效的索引类型"""
        # 单层索引应该报错
        simple_series = pd.Series([0.1, 0.2, 0.3])

        with pytest.raises(ValueError, match="必须有 .* MultiIndex"):
            metrics.calculate_daily_cs_ic(simple_series, simple_series)

    def test_calculate_daily_cs_ic_misaligned_data(self) -> None:
        """测试数据不对齐的情况"""
        # predictions 有 A, B, C
        pred_index = pd.MultiIndex.from_product(
            [pd.to_datetime(["2024-01-02"]), ["A", "B", "C"]],
            names=["date", "symbol"]
        )
        predictions = pd.Series([0.1, 0.2, 0.3], index=pred_index)

        # labels 只有 B, C, D
        label_index = pd.MultiIndex.from_product(
            [pd.to_datetime(["2024-01-02"]), ["B", "C", "D"]],
            names=["date", "symbol"]
        )
        labels = pd.Series([0.2, 0.3, 0.4], index=label_index)

        daily_ic = metrics.calculate_daily_cs_ic(predictions, labels)

        # 应该只计算交集（B 和 C）
        assert len(daily_ic) == 1
        # 两个点的相关系数是 1.0
        assert abs(daily_ic.iloc[0] - 1.0) < 0.01


class TestSummarizeDailyCS:
    """测试 Daily-CS 统计汇总"""

    def test_summarize_daily_cs_basic(self) -> None:
        """测试基本汇总功能"""
        # 5 天的 IC 数据
        daily_ic = pd.Series([0.05, 0.03, 0.08, -0.02, 0.06])

        stats = metrics.summarize_daily_cs(daily_ic)

        assert "mean_ic" in stats
        assert "std_ic" in stats
        assert "icir" in stats
        assert "t_stat" in stats
        assert "n_days" in stats

        # 验证计算结果
        assert stats["n_days"] == 5
        assert abs(stats["mean_ic"] - 0.04) < 0.001  # 平均值
        assert stats["std_ic"] > 0  # 标准差应该 > 0
        assert stats["icir"] > 0  # ICIR = mean / std
        assert stats["t_stat"] > 0  # t 统计量

    def test_summarize_daily_cs_high_icir(self) -> None:
        """测试高 ICIR 情况（稳定的 IC）"""
        # 非常稳定的 IC（小标准差）
        daily_ic = pd.Series([0.05, 0.051, 0.049, 0.050, 0.052])

        stats = metrics.summarize_daily_cs(daily_ic)

        # ICIR 应该很高（因为标准差很小）
        assert stats["icir"] > 10.0
        assert stats["mean_ic"] > 0.049
        assert stats["std_ic"] < 0.002

    def test_summarize_daily_cs_with_nan(self) -> None:
        """测试包含 NaN 的情况"""
        daily_ic = pd.Series([0.05, np.nan, 0.08, -0.02, np.nan, 0.06])

        stats = metrics.summarize_daily_cs(daily_ic)

        # 应该只计算非 NaN 值（4 个）
        assert stats["n_days"] == 4
        assert abs(stats["mean_ic"] - np.mean([0.05, 0.08, -0.02, 0.06])) < 0.001

    def test_summarize_daily_cs_empty(self) -> None:
        """测试空数据"""
        empty_ic = pd.Series(dtype=float)

        stats = metrics.summarize_daily_cs(empty_ic)

        assert stats["n_days"] == 0
        assert stats["mean_ic"] == 0.0
        assert stats["std_ic"] == 0.0
        assert stats["icir"] == 0.0
        assert stats["t_stat"] == 0.0

    def test_summarize_daily_cs_single_day(self) -> None:
        """测试单日数据"""
        single_ic = pd.Series([0.05])

        stats = metrics.summarize_daily_cs(single_ic)

        assert stats["n_days"] == 1
        assert stats["mean_ic"] == 0.05
        assert stats["std_ic"] == 0.0  # 单个值的标准差是 0
        assert stats["icir"] == 0.0  # 除以 0


class TestAggregateDailyToMonthly:
    """测试月度聚合"""

    def test_aggregate_daily_to_monthly_basic(self) -> None:
        """测试基本月度聚合"""
        # 3 个月的数据
        dates = pd.to_datetime([
            "2024-01-02", "2024-01-03", "2024-01-04",  # 1月
            "2024-02-01", "2024-02-02",                # 2月
            "2024-03-01", "2024-03-04", "2024-03-05",  # 3月
        ])
        daily_ic = pd.Series([0.05, 0.03, 0.08, 0.06, 0.07, 0.04, 0.05, 0.06], index=dates)

        monthly = metrics.aggregate_daily_to_monthly(daily_ic)

        assert len(monthly) == 3
        assert list(monthly.columns) == ["year_month", "mean_ic", "std_ic", "n_days"]

        # 验证第一个月
        jan_row = monthly[monthly["year_month"] == "2024-01"].iloc[0]
        assert jan_row["n_days"] == 3
        assert abs(jan_row["mean_ic"] - np.mean([0.05, 0.03, 0.08])) < 0.001

        # 验证第二个月
        feb_row = monthly[monthly["year_month"] == "2024-02"].iloc[0]
        assert feb_row["n_days"] == 2

    def test_aggregate_daily_to_monthly_with_nan(self) -> None:
        """测试包含 NaN 的月度聚合"""
        dates = pd.to_datetime([
            "2024-01-02", "2024-01-03", "2024-01-04",
            "2024-02-01", "2024-02-02",
        ])
        daily_ic = pd.Series([0.05, np.nan, 0.08, 0.06, np.nan], index=dates)

        monthly = metrics.aggregate_daily_to_monthly(daily_ic)

        # 1月应该有 2 个有效值，2月应该有 1 个
        jan_row = monthly[monthly["year_month"] == "2024-01"].iloc[0]
        assert jan_row["n_days"] == 2

        feb_row = monthly[monthly["year_month"] == "2024-02"].iloc[0]
        assert feb_row["n_days"] == 1

    def test_aggregate_daily_to_monthly_empty(self) -> None:
        """测试空数据"""
        empty_ic = pd.Series(dtype=float)

        monthly = metrics.aggregate_daily_to_monthly(empty_ic)

        assert monthly.empty
        assert list(monthly.columns) == ["year_month", "mean_ic", "std_ic", "n_days"]

    def test_aggregate_daily_to_monthly_single_month(self) -> None:
        """测试单月数据"""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        daily_ic = pd.Series([0.05, 0.03, 0.08], index=dates)

        monthly = metrics.aggregate_daily_to_monthly(daily_ic)

        assert len(monthly) == 1
        assert monthly.iloc[0]["year_month"] == "2024-01"
        assert monthly.iloc[0]["n_days"] == 3
