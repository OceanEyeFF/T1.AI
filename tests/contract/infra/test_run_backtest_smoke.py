"""run_backtest 行为级冒烟（双路 CodeReview P1：该脚本此前零行为测试）。

用 FakeLake 替换 make_r4_datalake，验证：
- tushare 单一信源 + qfq 口径 + symbol→ts_code 转换
- 违规 symbol（创业/科创/ST 等）→ SystemExit
- 输出落盘 outputs/reports（默认路径由三区契约测试另锁）
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts import run_backtest as rb


def _bars(periods: int = 40) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=periods)
    df = pd.DataFrame(
        {
            "open": 10.0,
            "high": 10.3,
            "low": 9.7,
            "close": [10.0 + i * 0.02 for i in range(periods)],
            "volume": 10000.0,
            "amount": 100000.0,
        },
        index=idx,
    )
    df.index.name = "date"
    return df


class _FakeLake:
    def __init__(self, bars: pd.DataFrame) -> None:
        self._bars = bars
        self.calls: list[tuple[str, str, str, dict]] = []

    def load_daily_bars(self, symbol: str, start: str, end: str, **kwargs) -> pd.DataFrame:
        self.calls.append((symbol, start, end, kwargs))
        return self._bars.copy()

    def load_index_daily(self, *args, **kwargs) -> pd.DataFrame:
        return self._bars.copy()


@pytest.mark.contract
def test_run_backtest_tushare_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lake = _FakeLake(_bars())
    monkeypatch.setattr(rb, "make_r4_datalake", lambda **kwargs: lake)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_backtest.py",
            "--symbols", "600000",
            "--start", "20240102",
            "--end", "20240229",
            "--out-dir", str(tmp_path / "reports"),
        ],
    )

    rb.main()

    assert lake.calls, "load_daily_bars 未被调用"
    symbol, start, end, kwargs = lake.calls[0]
    assert symbol == "600000.SH"  # bare → ts_code 转换
    assert start == "20240102" and end == "20240229"
    assert kwargs["source"] == "tushare"
    assert kwargs["adjust"] == "qfq"

    saved = list((tmp_path / "reports").glob("*"))
    assert saved, "无输出产物"
    for name in ("equity.csv", "fills.csv", "stats.csv", "benchmark.csv"):
        assert any(p.name == name for p in (tmp_path / "reports").glob("*/" + name)), name


@pytest.mark.contract
def test_run_backtest_rejects_disallowed_symbol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_backtest.py",
            "--symbols", "300001",  # 创业板：universe 约束外
            "--start", "20240102",
            "--end", "20240229",
        ],
    )

    with pytest.raises(SystemExit, match="symbols not allowed"):
        rb.main()
