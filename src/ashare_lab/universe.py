from __future__ import annotations


def is_allowed_a_share_symbol(symbol: str) -> bool:
    s = symbol.strip()
    if not s.isdigit():
        return False
    if s.startswith("688"):
        return False  # 科创板
    if s.startswith(("300", "301")):
        return False  # 创业板
    if s.startswith(("8", "4")):
        return False  # 北交（常见号段）
    return True

