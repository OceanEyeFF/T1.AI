"""
仓位管理器单元测试
"""

from ashare_lab.strategy.portfolio import PortfolioManager


class TestPortfolioManager:
    """测试 PortfolioManager"""

    def test_compute_target_weights_basic(self) -> None:
        """测试基础权重计算"""
        portfolio_mgr = PortfolioManager(top_n=3)

        # 构造排序后的信号
        ranked_signals = [
            ("601318", 0.20),
            ("600519", 0.15),
            ("000333", 0.10),
            ("600036", 0.05),
        ]

        weights = portfolio_mgr.compute_target_weights(ranked_signals)

        # 验证：应该选择前3只股票，每只权重 1/3
        assert len(weights) == 3
        assert "601318" in weights
        assert "600519" in weights
        assert "000333" in weights
        assert "600036" not in weights

        # 验证等权重
        expected_weight = 1.0 / 3.0
        assert abs(weights["601318"] - expected_weight) < 1e-6
        assert abs(weights["600519"] - expected_weight) < 1e-6
        assert abs(weights["000333"] - expected_weight) < 1e-6

        # 验证权重和 ≤ 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 1e-6

    def test_compute_target_weights_fewer_than_top_n(self) -> None:
        """测试候选股票数量少于 top_n 的情况"""
        portfolio_mgr = PortfolioManager(top_n=5)

        # 只有2只股票
        ranked_signals = [
            ("601318", 0.20),
            ("600519", 0.15),
        ]

        weights = portfolio_mgr.compute_target_weights(ranked_signals)

        # 验证：应该全选，每只权重 1/2
        assert len(weights) == 2
        assert "601318" in weights
        assert "600519" in weights

        expected_weight = 1.0 / 2.0
        assert abs(weights["601318"] - expected_weight) < 1e-6
        assert abs(weights["600519"] - expected_weight) < 1e-6

    def test_compute_target_weights_empty(self) -> None:
        """测试空信号列表"""
        portfolio_mgr = PortfolioManager(top_n=3)

        weights = portfolio_mgr.compute_target_weights([])

        # 应该返回空字典
        assert weights == {}

    def test_compute_target_weights_single_stock(self) -> None:
        """测试单只股票的情况"""
        portfolio_mgr = PortfolioManager(top_n=3)

        ranked_signals = [
            ("600519", 0.15),
        ]

        weights = portfolio_mgr.compute_target_weights(ranked_signals)

        # 验证：单只股票权重为 1.0
        assert len(weights) == 1
        assert "600519" in weights
        assert abs(weights["600519"] - 1.0) < 1e-6

    def test_compute_target_weights_different_top_n(self) -> None:
        """测试不同的 top_n 参数"""
        ranked_signals = [
            ("A", 0.5),
            ("B", 0.4),
            ("C", 0.3),
            ("D", 0.2),
            ("E", 0.1),
        ]

        # top_n = 1
        portfolio_mgr = PortfolioManager(top_n=1)
        weights = portfolio_mgr.compute_target_weights(ranked_signals)
        assert len(weights) == 1
        assert "A" in weights
        assert abs(weights["A"] - 1.0) < 1e-6

        # top_n = 2
        portfolio_mgr = PortfolioManager(top_n=2)
        weights = portfolio_mgr.compute_target_weights(ranked_signals)
        assert len(weights) == 2
        assert "A" in weights
        assert "B" in weights
        assert abs(weights["A"] - 0.5) < 1e-6
        assert abs(weights["B"] - 0.5) < 1e-6

        # top_n = 5
        portfolio_mgr = PortfolioManager(top_n=5)
        weights = portfolio_mgr.compute_target_weights(ranked_signals)
        assert len(weights) == 5
        assert all(symbol in weights for symbol in ["A", "B", "C", "D", "E"])
        assert all(abs(w - 0.2) < 1e-6 for w in weights.values())

    def test_compute_target_weights_preserves_order(self) -> None:
        """测试权重计算不改变信号顺序依赖"""
        portfolio_mgr = PortfolioManager(top_n=3)

        ranked_signals = [
            ("Z", 0.01),  # 低分但排第一
            ("A", 0.99),  # 高分但排第二
            ("M", 0.50),  # 中等分数排第三
        ]

        weights = portfolio_mgr.compute_target_weights(ranked_signals)

        # 验证：应该严格按照输入顺序选择前3只（不管分数高低）
        assert len(weights) == 3
        assert "Z" in weights
        assert "A" in weights
        assert "M" in weights

    def test_should_rebalance_placeholder(self) -> None:
        """测试换仓判断方法（阶段2功能，暂不测试逻辑）"""
        portfolio_mgr = PortfolioManager(rebalance_threshold=0.05)

        # 测试方法存在性
        result = portfolio_mgr._should_rebalance(
            new_candidate="600519",
            new_score=0.20,
            current_holding="000333",
            current_score=0.10,
        )

        # 阶段1：仅验证方法可调用（不验证具体逻辑）
        assert isinstance(result, bool)

    def test_estimate_cost_placeholder(self) -> None:
        """测试成本估算方法（阶段2功能，暂不测试逻辑）"""
        portfolio_mgr = PortfolioManager()

        # 测试方法存在性
        cost = portfolio_mgr._estimate_cost(turnover_value=10000.0)

        # 阶段1：仅验证方法可调用（不验证具体逻辑）
        assert isinstance(cost, float)
        assert cost > 0
