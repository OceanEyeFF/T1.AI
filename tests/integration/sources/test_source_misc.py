from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from ashare_lab.data import index_source as idx_src
from ashare_lab.data import tushare_source as ts_src
from ashare_lab.data.tushare_source import _date_ranges_to_fetch, TushareDailyBarsRequest


def test_index_source_cache_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_file = tmp_path / "index_000300_daily_20240101_20240103.csv"
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    pd.DataFrame(
        {
            "date": dates,
            "open": [1, 2, 3],
            "high": [1.1, 2.1, 3.1],
            "low": [0.9, 1.9, 2.9],
            "close": [1, 2, 3],
            "volume": [100, 200, 300],
            "amount": [1000, 2000, 3000],
        }
    ).to_csv(cache_file, index=False)

    def fail_fetch(req):  # pragma: no cover - should not be called
        raise AssertionError("fetch should not run")

    monkeypatch.setattr(idx_src, "fetch_index_daily", fail_fetch)
    req = idx_src.IndexDailyRequest("000300", "20240101", "20240103")
    df = idx_src.load_or_fetch_index_daily(req, cache_dir=tmp_path)
    assert len(df) == 3
    assert df.index[0] == pd.Timestamp("2024-01-01")


def test_index_source_fetch_and_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(req):
        dates = pd.date_range("2024-02-01", periods=2, freq="D")
        return pd.DataFrame(
            {
                "trade_date": dates.strftime("%Y%m%d"),
                "open": [1, 1.1],
                "high": [1.2, 1.3],
                "low": [0.9, 1.0],
                "close": [1.0, 1.1],
                "vol": [100, 110],
                "amount": [1000, 1100],
            }
        )

    monkeypatch.setattr(idx_src, "fetch_index_daily", fake_fetch)
    req = idx_src.IndexDailyRequest("000300", "20240201", "20240202")
    df = idx_src.load_or_fetch_index_daily(req, cache_dir=tmp_path, refresh=True)
    assert len(df) == 2
    assert (tmp_path / "index_000300_daily_20240201_20240202.csv").exists()


def test_date_ranges_to_fetch_both_sides() -> None:
    existing = pd.DataFrame(
        {"close": [1, 2, 3]},
        index=pd.to_datetime(["2024-01-05", "2024-01-06", "2024-01-07"]),
    )
    ranges = _date_ranges_to_fetch(existing, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-10"))
    assert ranges == [
        (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-04")),
        (pd.Timestamp("2024-01-08"), pd.Timestamp("2024-01-10")),
    ]


def test_tushare_refresh_ignores_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "600519.SH"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # 先写入旧数据
    old_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01"]),
            "open": [10],
            "high": [11],
            "low": [9],
            "close": [10.5],
            "volume": [1000],
            "amount": [1_000_000],
        }
    ).set_index("date")
    ts_src._write_partitioned(old_df, cache_dir / "tushare" / symbol)

    new_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-01"]),
            "open": [20],
            "high": [21],
            "low": [19],
            "close": [20.5],
            "volume": [2000],
            "amount": [2_000_000],
        }
    ).set_index("date")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", lambda req: new_df)
    req = TushareDailyBarsRequest(symbol=symbol, start_date="20240201", end_date="20240201")
    df = ts_src.load_or_fetch_daily_bars(req, cache_dir=cache_dir, refresh=True)
    assert df.index.min() == pd.Timestamp("2024-02-01")
    # 旧数据应被忽略
    assert len(df) == 1


def test_retry_with_backoff_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "600000.SH"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    def always_fail(_: TushareDailyBarsRequest):
        raise TimeoutError("fail")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", always_fail)
    monkeypatch.setattr(ts_src.time, "sleep", lambda *_: None)

    req = TushareDailyBarsRequest(symbol=symbol, start_date="20240301", end_date="20240301")
    with pytest.raises(TimeoutError):
        ts_src.load_or_fetch_daily_bars(req, cache_dir=cache_dir, retries=2, backoff_base=0.01)
