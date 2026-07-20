"""测试股票池过滤规则"""

from __future__ import annotations

import pandas as pd

from ashare_lab.universe import is_allowed_a_share_symbol


class TestIsAllowedAShareSymbol:
    """测试 is_allowed_a_share_symbol 函数"""

    def test_valid_symbols(self) -> None:
        """测试有效的 A 股代码"""
        valid_symbols = [
            "600000",  # 上交所主板
            "601318",  # 上交所主板
            "000001",  # 深交所主板
            "000333",  # 深交所主板
            "002594",  # 深交所中小板
        ]
        for symbol in valid_symbols:
            assert is_allowed_a_share_symbol(symbol), f"应该允许: {symbol}"

    def test_sci_tech_board(self) -> None:
        """测试科创板代码（688*）应被排除"""
        sci_tech_symbols = [
            "688001",
            "688012",
            "688520",
        ]
        for symbol in sci_tech_symbols:
            assert not is_allowed_a_share_symbol(symbol), f"应该排除科创板: {symbol}"

    def test_chinext_board(self) -> None:
        """测试创业板代码（300*/301*）应被排除"""
        chinext_symbols = [
            "300001",
            "300750",
            "301012",
            "301520",
        ]
        for symbol in chinext_symbols:
            assert not is_allowed_a_share_symbol(symbol), f"应该排除创业板: {symbol}"

    def test_beijing_exchange(self) -> None:
        """测试北交所代码（8*/4*）应被排除"""
        beijing_symbols = [
            "830799",
            "835185",
            "430047",
            "400037",
        ]
        for symbol in beijing_symbols:
            assert not is_allowed_a_share_symbol(symbol), f"应该排除北交所: {symbol}"

    def test_b_share_board(self) -> None:
        """测试沪市 B 股代码（9*）应被排除（非 A 股）"""
        b_share_symbols = [
            "900901",
            "900948",
        ]
        for symbol in b_share_symbols:
            assert not is_allowed_a_share_symbol(symbol), f"应该排除 B 股: {symbol}"

    def test_invalid_format(self) -> None:
        """测试无效格式应被排除"""
        invalid_symbols = [
            "SH600000",  # 包含非数字字符
            "60000",  # 长度不足
            "",  # 空字符串
            "   ",  # 空白字符
            "ABC123",  # 包含字母
        ]
        for symbol in invalid_symbols:
            assert not is_allowed_a_share_symbol(symbol), f"应该排除无效格式: {symbol}"

    def test_whitespace_handling(self) -> None:
        """测试空白字符处理"""
        # 前后有空白的有效代码应被接受
        assert is_allowed_a_share_symbol("  600000  ")
        # 前后有空白的无效代码应被排除
        assert not is_allowed_a_share_symbol("  688001  ")


class TestUniverseFilter:
    """测试股票池过滤功能"""

    def test_filter_by_code(self) -> None:
        """测试按代码过滤"""
        # 创建测试数据
        df = pd.DataFrame(
            {
                "symbol": [
                    "600000",  # 有效
                    "688001",  # 科创板
                    "300001",  # 创业板
                    "000001",  # 有效
                    "830799",  # 北交所
                    "601318",  # 有效
                ],
                "name": [
                    "浦发银行",
                    "科创股票",
                    "创业股票",
                    "平安银行",
                    "北交股票",
                    "中国平安",
                ],
            }
        )

        # 按代码过滤
        mask = df["symbol"].apply(is_allowed_a_share_symbol)
        df_filtered = df[mask]

        # 验证结果
        assert len(df_filtered) == 3
        assert set(df_filtered["symbol"].tolist()) == {"600000", "000001", "601318"}

    def test_filter_by_name_st(self) -> None:
        """测试按名称过滤 ST 股票"""
        # 创建测试数据
        df = pd.DataFrame(
            {
                "symbol": ["600000", "600001", "600002", "600003"],
                "name": ["浦发银行", "ST股票", "*ST风险", "正常股票"],
            }
        )

        # 过滤 ST 股票
        mask_st = ~df["name"].str.contains("ST", na=False)
        df_filtered = df[mask_st]

        # 验证结果
        assert len(df_filtered) == 2
        assert set(df_filtered["name"].tolist()) == {"浦发银行", "正常股票"}

    def test_combined_filter(self) -> None:
        """测试综合过滤（代码 + ST）"""
        # 创建测试数据
        df = pd.DataFrame(
            {
                "symbol": [
                    "600000",  # 有效
                    "688001",  # 科创板
                    "600001",  # 有效但 ST
                    "300001",  # 创业板
                    "000001",  # 有效
                    "600002",  # 有效但 *ST
                ],
                "name": [
                    "浦发银行",
                    "科创股票",
                    "ST股票",
                    "创业股票",
                    "平安银行",
                    "*ST风险",
                ],
            }
        )

        # 综合过滤
        mask_code = df["symbol"].apply(is_allowed_a_share_symbol)
        df_filtered = df[mask_code]
        mask_st = ~df_filtered["name"].str.contains("ST", na=False)
        df_final = df_filtered[mask_st]

        # 验证结果
        assert len(df_final) == 2
        assert set(df_final["symbol"].tolist()) == {"600000", "000001"}
        assert set(df_final["name"].tolist()) == {"浦发银行", "平安银行"}
