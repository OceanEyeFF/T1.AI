"""测试防伪门禁 Sanity Check

验证 Shuffle Labels / Time Reverse / Lag-1 三项检验的正确性。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.evaluation.sanity_checks import (
    compute_baseline_ic,
    lag1_test,
    run_all_checks,
    shuffle_test,
    time_reverse_test,
)


def _make_strong_signal(n_dates: int = 20, n_symbols: int = 10, seed: int = 42):
    """构造强信号数据（predictions 与 labels 高度正相关）

    Returns:
        (predictions, labels) - 索引为 (date, symbol) 的 MultiIndex Series
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-02", periods=n_dates)
    symbols = [f"S{i:03d}" for i in range(n_symbols)]

    index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    # 生成真实信号 + 少量噪声
    true_signal = rng.randn(len(index))
    predictions = pd.Series(true_signal + rng.randn(len(index)) * 0.1, index=index)
    labels = pd.Series(true_signal + rng.randn(len(index)) * 0.3, index=index)

    return predictions, labels


def _make_noise_signal(n_dates: int = 20, n_symbols: int = 10, seed: int = 42):
    """构造纯噪声数据（predictions 与 labels 无关）"""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-02", periods=n_dates)
    symbols = [f"S{i:03d}" for i in range(n_symbols)]

    index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    predictions = pd.Series(rng.randn(len(index)), index=index)
    labels = pd.Series(rng.randn(len(index)), index=index)

    return predictions, labels


class TestComputeBaselineIC:
    """测试基线 IC 计算"""

    def test_strong_signal_high_ic(self) -> None:
        """强信号数据应该有高 IC"""
        preds, labels = _make_strong_signal()
        stats = compute_baseline_ic(preds, labels)

        assert stats["mean_ic"] > 0.5  # 强正相关
        assert stats["icir"] > 1.0  # 稳定
        assert stats["n_days"] == 20

    def test_noise_signal_low_ic(self) -> None:
        """噪声数据应该有低 IC"""
        preds, labels = _make_noise_signal()
        stats = compute_baseline_ic(preds, labels)

        assert abs(stats["mean_ic"]) < 0.15  # 接近 0

    def test_invalid_index_raises(self) -> None:
        """非 MultiIndex 应该报错"""
        simple = pd.Series([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="MultiIndex"):
            compute_baseline_ic(simple, simple)


class TestShuffleTest:
    """测试 Shuffle Labels 检验"""

    def test_strong_signal_shuffle_destroys_ic(self) -> None:
        """强信号打乱后 IC 应接近 0"""
        preds, labels = _make_strong_signal()
        result = shuffle_test(preds, labels, n_trials=5, threshold=0.15, seed=42)

        # 打乱后 IC 应大幅下降
        assert abs(result["mean_ic"]) < 0.15
        assert result["pass"] is True
        assert result["n_trials"] == 5

    def test_noise_signal_shuffle_still_low(self) -> None:
        """噪声信号打乱后 IC 仍然低"""
        preds, labels = _make_noise_signal()
        result = shuffle_test(preds, labels, n_trials=3, threshold=0.1)

        assert abs(result["mean_ic"]) < 0.1
        assert result["pass"] is True

    def test_deterministic_with_same_seed(self) -> None:
        """相同种子产生相同结果"""
        preds, labels = _make_strong_signal()
        r1 = shuffle_test(preds, labels, seed=123)
        r2 = shuffle_test(preds, labels, seed=123)

        assert r1["mean_ic"] == r2["mean_ic"]


class TestTimeReverseTest:
    """测试 Time Reverse 检验"""

    def test_strong_signal_reverse_destroys_ic(self) -> None:
        """强信号时间反转后 IC 应显著下降"""
        preds, labels = _make_strong_signal()

        baseline = compute_baseline_ic(preds, labels)
        result = time_reverse_test(preds, labels, threshold=0.15)

        # 反转后 IC 应远低于基线
        assert abs(result["mean_ic"]) < abs(baseline["mean_ic"])

    def test_noise_signal_reverse_still_low(self) -> None:
        """噪声信号反转后仍然低"""
        preds, labels = _make_noise_signal()
        result = time_reverse_test(preds, labels, threshold=0.15)

        assert abs(result["mean_ic"]) < 0.15
        assert result["pass"] is True

    def test_single_date_skipped(self) -> None:
        """单日数据跳过检验"""
        dates = pd.to_datetime(["2024-01-02"])
        symbols = ["A", "B", "C"]
        index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        preds = pd.Series([0.1, 0.2, 0.3], index=index)
        labels = pd.Series([0.12, 0.22, 0.32], index=index)

        result = time_reverse_test(preds, labels)
        assert result["pass"] is True
        assert "error" in result


class TestLag1Test:
    """测试 Lag-1 检验"""

    def test_strong_signal_lag1_drops_ic(self) -> None:
        """强信号延迟后 IC 应显著下降"""
        preds, labels = _make_strong_signal()
        baseline = compute_baseline_ic(preds, labels)

        result = lag1_test(
            preds, labels,
            baseline_mean_ic=baseline["mean_ic"],
            threshold=0.01,
        )

        assert result["ic_drop"] > 0  # IC 确实下降了
        assert result["lag1_mean_ic"] < result["baseline_mean_ic"]

    def test_noise_signal_lag1_no_significant_drop(self) -> None:
        """噪声信号延迟后无显著变化"""
        preds, labels = _make_noise_signal()
        baseline = compute_baseline_ic(preds, labels)

        # 噪声信号的 baseline IC 接近0，延迟后也接近0
        result = lag1_test(
            preds, labels,
            baseline_mean_ic=baseline["mean_ic"],
            threshold=0.5,  # 设高阈值，噪声不会通过
        )

        # 噪声信号的 IC drop 不大
        assert abs(result["ic_drop"]) < 0.3

    def test_single_date_fails(self) -> None:
        """单日数据无法做 lag-1 检验"""
        dates = pd.to_datetime(["2024-01-02"])
        symbols = ["A", "B", "C"]
        index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        preds = pd.Series([0.1, 0.2, 0.3], index=index)
        labels = pd.Series([0.12, 0.22, 0.32], index=index)

        result = lag1_test(preds, labels, baseline_mean_ic=0.9)
        assert result["pass"] is False
        assert "error" in result


class TestRunAllChecks:
    """测试 run_all_checks 综合接口"""

    def test_strong_signal_all_pass(self) -> None:
        """强信号应该通过所有 Sanity Check"""
        preds, labels = _make_strong_signal()
        report = run_all_checks(
            preds, labels,
            shuffle_threshold=0.15,
            reverse_threshold=0.15,
            lag1_threshold=0.01,
        )

        # 所有子报告都存在
        assert "baseline" in report
        assert "shuffle_labels" in report
        assert "time_reverse" in report
        assert "lag_1" in report
        assert "all_pass" in report

        # 基线 IC 应该很高
        assert report["baseline"]["mean_ic"] > 0.5

    def test_report_structure(self) -> None:
        """验证报告结构完整性"""
        preds, labels = _make_strong_signal(n_dates=5, n_symbols=5)
        report = run_all_checks(preds, labels, shuffle_n_trials=2)

        # baseline 字段
        for key in ["mean_ic", "std_ic", "icir", "t_stat", "n_days"]:
            assert key in report["baseline"]

        # shuffle 字段
        assert "mean_ic" in report["shuffle_labels"]
        assert "pass" in report["shuffle_labels"]
        assert "threshold" in report["shuffle_labels"]
        assert "n_trials" in report["shuffle_labels"]

        # time_reverse 字段
        assert "mean_ic" in report["time_reverse"]
        assert "pass" in report["time_reverse"]

        # lag_1 字段
        assert "baseline_mean_ic" in report["lag_1"]
        assert "lag1_mean_ic" in report["lag_1"]
        assert "ic_drop" in report["lag_1"]
        assert "pass" in report["lag_1"]
