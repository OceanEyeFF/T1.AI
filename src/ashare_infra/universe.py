from __future__ import annotations


def is_allowed_a_share_symbol(symbol: str) -> bool:
    """判断股票代码是否为允许的 A 股代码

    过滤规则（与 docs/constraints.md 一致）：
    - 必须是 6 位数字
    - 排除代码前缀 688*（科创板）
    - 排除代码前缀 300*/301*（创业板）
    - 排除代码前缀 8*/4*（北交所）

    Args:
        symbol: 股票代码

    Returns:
        True 如果是允许的 A 股代码，否则 False
    """
    s = symbol.strip()
    # 必须是纯数字
    if not s.isdigit():
        return False
    # 必须是 6 位
    if len(s) != 6:
        return False
    # 排除科创板
    if s.startswith("688"):
        return False
    # 排除创业板
    if s.startswith(("300", "301")):
        return False
    # 排除北交所（常见号段）
    if s.startswith(("8", "4")):
        return False
    return True
