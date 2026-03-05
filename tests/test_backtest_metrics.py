"""测试回测风险指标计算

验证 _calc_stats 和 _reconstruct_gross_equity 的正确性。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.backtest.engine import _calc_stats, _reconstruct_gross_equity


def _make_equity_curve(equities: list[float], dates: list[str]) -> pd.DataFrame:
    """构造 equity_curve DataFrame"""
    idx = pd.to_datetime(dates)
    return pd.DataFrame({"equity": equities, "cash": [0.0] * len(equities)}, index=idx)


def _make_fills(
    costs: list[float], turnovers: list[float], dates: list[str]
) -> pd.DataFrame:
    """构造 fills DataFrame"""
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "symbol": ["600519"] * len(costs),
        "side": ["BUY"] * len(costs),
        "shares": [100] * len(costs),
        "price": [10.0] * len(costs),
        "turnover": turnovers,
        "cost": costs,
    })


class TestCalcStatsBasic:
    """测试 _calc_stats 基本功能"""

    def test_empty_equity_curve(self) -> None:
        """空数据返回空字典"""
        result = _calc_stats(pd.DataFrame(columns=["equity", "cash"]), pd.DataFrame())
        assert result == {}

    def test_single_day_equity(self) -> None:
        """单日数据只返回 final_equity"""
        ec = _make_equity_curve([100_000.0], ["2024-01-02"])
        result = _calc_stats(ec, pd.DataFrame())
        assert "final_equity" in result
        assert result["final_equity"] == 100_000.0

    def test_basic_positive_return(self) -> None:
        """正收益场景验证"""
        # 4天，收益有波动但整体为正
        equities = [100_000.0, 101_000.0, 100_500.0, 102_000.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ec = _make_equity_curve(equities, dates)
        fills = pd.DataFrame()

        stats = _calc_stats(ec, fills)

        # 基础字段存在
        assert "final_equity" in stats
        assert "cagr" in stats
        assert "mdd" in stats

        # 新增字段存在
        assert "net_cagr" in stats
        assert "gross_cagr" in stats
        assert "ann_vol" in stats
        assert "sharpe" in stats
        assert "sortino" in stats
        assert "calmar" in stats
        assert "win_rate_daily" in stats
        assert "cost_drag_pct" in stats

        # 验证数值合理性
        assert stats["final_equity"] == pytest.approx(102_000.0)
        assert stats["net_cagr"] > 0  # 正收益
        assert stats["cagr"] == stats["net_cagr"]  # 向后兼容
        assert stats["mdd"] == stats["net_mdd"]  # 向后兼容
        assert stats["sharpe"] > 0  # 正收益 -> 正 Sharpe
        assert stats["win_rate_daily"] == pytest.approx(2 / 3)  # 3天中2天正收益
        assert stats["mdd"] <= 0  # 最大回撤非正


class TestCalcStatsRiskMetrics:
    """测试风险指标计算"""

    def test_sharpe_ratio_formula(self) -> None:
        """验证 Sharpe 比率公式：mean_daily_ret / std_daily_ret * sqrt(252)"""
        # 构造已知收益序列
        equities = [100.0, 101.0, 100.5, 101.5, 102.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        # 手动计算
        equity_s = pd.Series(equities)
        rets = equity_s.pct_change().dropna()
        expected_sharpe = float(rets.mean() / rets.std(ddof=1) * np.sqrt(252))

        assert stats["sharpe"] == pytest.approx(expected_sharpe, rel=1e-6)

    def test_sortino_uses_downside_deviation(self) -> None:
        """验证 Sortino 比率使用下行偏差而非全标准差"""
        # 有正有负的收益序列
        equities = [100.0, 102.0, 99.0, 101.0, 100.5]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        # 手动计算 Sortino
        equity_s = pd.Series(equities)
        rets = equity_s.pct_change().dropna()
        downside_sq = np.where(rets.values < 0, rets.values ** 2, 0.0)
        downside_dev = float(np.sqrt(np.mean(downside_sq)))
        expected_sortino = float(rets.mean() / downside_dev * np.sqrt(252))

        assert stats["sortino"] == pytest.approx(expected_sortino, rel=1e-6)

    def test_calmar_ratio_formula(self) -> None:
        """验证 Calmar = CAGR / |MaxDD|"""
        # 构造有回撤的序列
        equities = [100.0, 105.0, 95.0, 102.0, 110.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        # MaxDD = (95 - 105) / 105 ≈ -0.09524
        expected_mdd = (95.0 - 105.0) / 105.0
        assert stats["mdd"] == pytest.approx(expected_mdd, rel=1e-4)

        # Calmar = CAGR / |MDD|
        expected_calmar = stats["net_cagr"] / abs(stats["net_mdd"])
        assert stats["calmar"] == pytest.approx(expected_calmar, rel=1e-6)

    def test_win_rate_daily(self) -> None:
        """验证日胜率计算"""
        # 3天正, 1天负 -> 胜率 = 3/4 = 0.75
        equities = [100.0, 101.0, 102.0, 101.5, 103.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        assert stats["win_rate_daily"] == pytest.approx(0.75)

    def test_annualized_volatility(self) -> None:
        """验证年化波动率公式: daily_std * sqrt(252)"""
        equities = [100.0, 101.0, 99.0, 100.5, 101.5]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        equity_s = pd.Series(equities)
        rets = equity_s.pct_change().dropna()
        expected_vol = float(rets.std(ddof=1) * np.sqrt(252))

        assert stats["ann_vol"] == pytest.approx(expected_vol, rel=1e-6)


class TestGrossEquityReconstruction:
    """测试毛权益重建"""

    def test_no_fills_same_as_net(self) -> None:
        """无成交时毛权益 = 净权益"""
        equities = [100.0, 101.0, 102.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
        equity_s = pd.Series(equities, index=pd.to_datetime(dates))
        gross = _reconstruct_gross_equity(equity_s, pd.DataFrame())
        pd.testing.assert_series_equal(gross, equity_s)

    def test_adds_cumulative_costs(self) -> None:
        """毛权益 = 净权益 + 累计成本"""
        dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
        equities = [100.0, 99.0, 98.0]
        equity_s = pd.Series(equities, index=pd.to_datetime(dates))

        fills = _make_fills(
            costs=[5.0, 3.0],
            turnovers=[5000.0, 3000.0],
            dates=["2024-01-02", "2024-01-03"],
        )

        gross = _reconstruct_gross_equity(equity_s, fills)

        # 累计成本: day1=5, day2=8, day3=8
        assert gross.iloc[0] == pytest.approx(105.0)  # 100 + 5
        assert gross.iloc[1] == pytest.approx(107.0)  # 99 + 8
        assert gross.iloc[2] == pytest.approx(106.0)  # 98 + 8

    def test_gross_cagr_higher_than_net(self) -> None:
        """有成本时毛CAGR应该高于净CAGR"""
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        equities = [100_000.0, 100_500.0, 101_000.0, 101_200.0, 101_500.0]
        ec = _make_equity_curve(equities, dates)

        fills = _make_fills(
            costs=[50.0, 30.0, 20.0],
            turnovers=[50_000.0, 30_000.0, 20_000.0],
            dates=["2024-01-02", "2024-01-03", "2024-01-04"],
        )

        stats = _calc_stats(ec, fills)

        assert stats["gross_cagr"] > stats["net_cagr"]
        assert stats["cost_drag_pct"] > 0

    def test_cost_drag_pct(self) -> None:
        """成本拖累比例 = (gross_cagr - net_cagr) / |gross_cagr|"""
        dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
        equities = [100_000.0, 101_000.0, 102_000.0]
        ec = _make_equity_curve(equities, dates)

        fills = _make_fills(
            costs=[100.0],
            turnovers=[50_000.0],
            dates=["2024-01-02"],
        )

        stats = _calc_stats(ec, fills)

        expected_drag = (stats["gross_cagr"] - stats["net_cagr"]) / abs(stats["gross_cagr"])
        assert stats["cost_drag_pct"] == pytest.approx(expected_drag, rel=1e-6)


class TestEdgeCases:
    """边界情况测试"""

    def test_zero_volatility(self) -> None:
        """零波动率时 Sharpe/Sortino 应为 0"""
        equities = [100.0, 100.0, 100.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        assert stats["sharpe"] == 0.0
        assert stats["sortino"] == 0.0
        assert stats["ann_vol"] == 0.0

    def test_all_negative_returns(self) -> None:
        """全部负收益"""
        equities = [100.0, 98.0, 95.0, 92.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        assert stats["net_cagr"] < 0
        assert stats["sharpe"] < 0
        assert stats["win_rate_daily"] == 0.0
        assert stats["mdd"] < 0

    def test_no_drawdown(self) -> None:
        """无回撤（单调递增）时 Calmar 可能很大"""
        equities = [100.0, 101.0, 102.0, 103.0, 104.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        # MDD 可能非零（日内波动），但 Calmar 应该 > 0
        assert stats["calmar"] >= 0
        assert stats["win_rate_daily"] == 1.0

    def test_backward_compatible_keys(self) -> None:
        """向后兼容：cagr/mdd 字段仍存在且等于 net 版本"""
        equities = [100.0, 105.0, 95.0, 100.0]
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ec = _make_equity_curve(equities, dates)
        stats = _calc_stats(ec, pd.DataFrame())

        assert stats["cagr"] == stats["net_cagr"]
        assert stats["mdd"] == stats["net_mdd"]
