"""
信号生成器单元测试
"""

import numpy as np
import pandas as pd

from ashare_lab.strategy.signal import MomentumSignalGenerator


class TestSignalGenerator:
    """测试 SignalGenerator 基类"""

    def test_rank_stocks_basic(self) -> None:
        """测试基础排序功能"""
        # 创建一个简单的信号生成器实例（使用 MomentumSignalGenerator）
        signal_gen = MomentumSignalGenerator()

        scores = {
            "600519": 0.15,
            "000333": 0.10,
            "601318": 0.20,
            "600036": 0.05,
        }

        # 测试无限制排序
        ranked = signal_gen.rank_stocks(scores)
        assert len(ranked) == 4
        assert ranked[0] == ("601318", 0.20)
        assert ranked[1] == ("600519", 0.15)
        assert ranked[2] == ("000333", 0.10)
        assert ranked[3] == ("600036", 0.05)

    def test_rank_stocks_with_top_n(self) -> None:
        """测试 top_n 限制"""
        signal_gen = MomentumSignalGenerator()

        scores = {
            "600519": 0.15,
            "000333": 0.10,
            "601318": 0.20,
            "600036": 0.05,
        }

        # 测试 top_n=2
        ranked = signal_gen.rank_stocks(scores, top_n=2)
        assert len(ranked) == 2
        assert ranked[0] == ("601318", 0.20)
        assert ranked[1] == ("600519", 0.15)

    def test_rank_stocks_empty(self) -> None:
        """测试空分数字典"""
        signal_gen = MomentumSignalGenerator()
        ranked = signal_gen.rank_stocks({})
        assert ranked == []


class TestMomentumSignalGenerator:
    """测试 MomentumSignalGenerator"""

    def test_compute_scores_basic(self) -> None:
        """测试基础动量计算"""
        signal_gen = MomentumSignalGenerator(lookback=5, min_history=10)

        # 构造测试数据
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        history = {
            "600519": pd.DataFrame(
                {
                    "close": [100.0 + i for i in range(20)],  # 线性上涨
                },
                index=dates,
            ),
            "000333": pd.DataFrame(
                {
                    "close": [100.0 - i * 0.5 for i in range(20)],  # 线性下跌
                },
                index=dates,
            ),
        }

        today = dates[-1]
        scores = signal_gen.compute_scores(today, history)

        # 验证：600519 应该有正动量，000333 应该有负动量
        assert "600519" in scores
        assert "000333" in scores
        assert scores["600519"] > 0  # 上涨股票，正动量
        assert scores["000333"] < 0  # 下跌股票，负动量

        # 验证动量计算公式：(close[-1] / close[-1-lookback]) - 1
        expected_600519 = (119.0 / 114.0) - 1.0  # (100+19) / (100+14) - 1
        expected_000333 = (90.5 / 93.0) - 1.0  # (100-9.5) / (100-7) - 1

        assert abs(scores["600519"] - expected_600519) < 1e-6
        assert abs(scores["000333"] - expected_000333) < 1e-6

    def test_compute_scores_insufficient_history(self) -> None:
        """测试历史数据不足的情况"""
        signal_gen = MomentumSignalGenerator(lookback=20, min_history=60)

        # 只有 30 天数据，不满足 min_history=60
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        history = {
            "600519": pd.DataFrame(
                {
                    "close": [100.0 + i for i in range(30)],
                },
                index=dates,
            ),
        }

        today = dates[-1]
        scores = signal_gen.compute_scores(today, history)

        # 应该返回空字典（数据不足）
        assert scores == {}

    def test_compute_scores_missing_close_column(self) -> None:
        """测试缺少 close 列的情况"""
        signal_gen = MomentumSignalGenerator()

        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        history = {
            "600519": pd.DataFrame(
                {
                    "open": [100.0 + i for i in range(100)],  # 只有 open，没有 close
                },
                index=dates,
            ),
        }

        today = dates[-1]
        scores = signal_gen.compute_scores(today, history)

        # 应该返回空字典（缺少必需列）
        assert scores == {}

    def test_compute_scores_with_nan_values(self) -> None:
        """测试包含 NaN 值的情况"""
        signal_gen = MomentumSignalGenerator(lookback=5, min_history=10)

        dates = pd.date_range("2024-01-01", periods=20, freq="D")

        # 构造包含 NaN 的数据
        close_data = [100.0 + i for i in range(20)]
        close_data[15] = np.nan  # 在关键位置插入 NaN

        history = {
            "600519": pd.DataFrame(
                {
                    "close": close_data,
                },
                index=dates,
            ),
        }

        today = dates[-1]
        scores = signal_gen.compute_scores(today, history)

        # dropna() 后数据长度可能不足，或者计算结果为 NaN
        # 应该被过滤掉
        if "600519" in scores:
            assert np.isfinite(scores["600519"])

    def test_compute_scores_multiple_stocks(self) -> None:
        """测试多只股票的情况"""
        signal_gen = MomentumSignalGenerator(lookback=10, min_history=30)

        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        history = {
            "600519": pd.DataFrame(
                {"close": [100.0 * (1.01**i) for i in range(50)]},  # 每天上涨1%
                index=dates,
            ),
            "000333": pd.DataFrame(
                {"close": [100.0] * 50},  # 横盘
                index=dates,
            ),
            "601318": pd.DataFrame(
                {"close": [100.0 * (0.99**i) for i in range(50)]},  # 每天下跌1%
                index=dates,
            ),
        }

        today = dates[-1]
        scores = signal_gen.compute_scores(today, history)

        # 验证：应该有3只股票的分数
        assert len(scores) == 3
        assert "600519" in scores
        assert "000333" in scores
        assert "601318" in scores

        # 验证相对大小：上涨 > 横盘 > 下跌
        assert scores["600519"] > scores["000333"]
        assert scores["000333"] > scores["601318"]
        assert scores["600519"] > 0
        assert abs(scores["000333"]) < 1e-6  # 横盘应该接近0
        assert scores["601318"] < 0
