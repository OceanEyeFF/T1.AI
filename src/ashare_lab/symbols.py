"""A-share symbol normalization helpers for lake adapters and builders."""

from __future__ import annotations


def symbol_to_ts_code(symbol: str) -> str:
    """Convert a bare 6-digit code to TuShare ``ts_code`` (e.g. ``600519.SH``)."""
    s = str(symbol).strip().upper()
    if not s:
        raise ValueError("symbol 不能为空")
    if "." in s:
        return s
    if len(s) != 6 or not s.isdigit():
        raise ValueError(f"不支持的股票代码格式: {symbol}")

    if s.startswith("6"):
        suffix = "SH"
    elif s.startswith(("0", "3")):
        suffix = "SZ"
    elif s.startswith(("8", "4")):
        suffix = "BJ"
    else:
        raise ValueError(f"无法识别交易所后缀: {symbol}")
    return f"{s}.{suffix}"


def symbol_to_odp_equity_symbol(symbol: str, provider: str = "yfinance") -> str:
    """Convert an A-share code to an ODP equity symbol (default yfinance)."""
    raw = str(symbol).strip().upper()
    if not raw:
        raise ValueError("symbol 不能为空")

    if "." in raw:
        code, suffix = raw.split(".", 1)
        suffix = suffix.upper()
        if str(provider).lower() == "yfinance":
            if suffix == "SH":
                return f"{code}.SS"
            if suffix in {"SZ", "SS", "BJ"}:
                return f"{code}.{suffix}"
        return raw

    if len(raw) != 6 or not raw.isdigit():
        raise ValueError(f"不支持的股票代码格式: {symbol}")

    if str(provider).lower() == "yfinance":
        if raw.startswith(("6", "9")):
            return f"{raw}.SS"
        if raw.startswith(("0", "3")):
            return f"{raw}.SZ"
        if raw.startswith(("8", "4")):
            return f"{raw}.BJ"
    return raw
