"""Tests for ashare_lab.symbols normalization helpers."""

from __future__ import annotations

import pytest

from ashare_lab.symbols import symbol_to_odp_equity_symbol, symbol_to_ts_code


def test_symbol_to_ts_code_bare_and_prefixed() -> None:
    assert symbol_to_ts_code("600519") == "600519.SH"
    assert symbol_to_ts_code("000001") == "000001.SZ"
    assert symbol_to_ts_code("600519.SH") == "600519.SH"


def test_symbol_to_odp_equity_symbol_yfinance() -> None:
    assert symbol_to_odp_equity_symbol("600519") == "600519.SS"
    assert symbol_to_odp_equity_symbol("000001") == "000001.SZ"
    assert symbol_to_odp_equity_symbol("600519.SH") == "600519.SS"


def test_symbol_to_ts_code_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        symbol_to_ts_code("ABC")
