from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from ashare_lab.data import tushare_source as ts_src
from ashare_lab.data.tushare_source import (
    SUPPORTED_FIELDS,
    TushareDailyBarsRequest,
    _normalize_tushare_daily,
    load_or_fetch_daily_bars,
)


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": ["20240103", "20240102", "20240101"],
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
            "vol": [1000, 2000, 3000],
            "amount": [1_000_000, 2_000_000, 3_000_000],
        }
    )


def test_normalize_mapping(sample_raw_df: pd.DataFrame) -> None:
    df = _normalize_tushare_daily(sample_raw_df)
    assert list(df.columns) == list(SUPPORTED_FIELDS)
    # 索引为升序日期
    assert df.index[0] == pd.Timestamp("2024-01-01")
    assert df.index[-1] == pd.Timestamp("2024-01-03")
    # 数值型字段
    assert pd.api.types.is_numeric_dtype(df["volume"])
    assert pd.api.types.is_numeric_dtype(df["amount"])


def test_partition_cache_and_incremental(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "600519.SH"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    first_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "open": [10, 11],
            "high": [11, 12],
            "low": [9, 10],
            "close": [10.5, 11.5],
            "volume": [1000, 2000],
            "amount": [1_000_000, 2_000_000],
        }
    ).set_index("date")

    second_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-03", "2024-01-04"]),
            "open": [12, 13],
            "high": [13, 14],
            "low": [11, 12],
            "close": [12.5, 13.5],
            "volume": [2500, 2600],
            "amount": [2_500_000, 2_600_000],
        }
    ).set_index("date")

    calls: list[pd.DataFrame] = []

    def fake_fetch(req: TushareDailyBarsRequest) -> pd.DataFrame:
        if req.end_date == "20240102":
            calls.append(first_df)
            return first_df
        calls.append(second_df)
        return second_df

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", fake_fetch)
    # 第一次：写入缓存
    req = TushareDailyBarsRequest(symbol=symbol, start_date="20240101", end_date="20240102")
    df1 = load_or_fetch_daily_bars(req, cache_dir=cache_dir)
    assert len(df1) == 2
    assert (cache_dir / "tushare" / symbol / "year=2024" / "part.parquet").exists()

    # 第二次：增量追加并去重
    req2 = TushareDailyBarsRequest(symbol=symbol, start_date="20240101", end_date="20240104")
    df2 = load_or_fetch_daily_bars(req2, cache_dir=cache_dir)
    assert len(df2) == 4
    assert df2.index.min() == pd.Timestamp("2024-01-01")
    assert df2.index.max() == pd.Timestamp("2024-01-04")
    assert df2.index.is_unique
    # fetch 被调用两次
    assert len(calls) == 2


def test_cache_hit_skip_fetch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "000001.SZ"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    base_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-01", "2024-02-02"]),
            "open": [1, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.05, 1.15],
            "volume": [100, 120],
            "amount": [1000, 1200],
        }
    ).set_index("date")
    # 直接写入缓存
    ts_src._write_partitioned(base_df, cache_dir / "tushare" / symbol)

    def fail_fetch(_: TushareDailyBarsRequest) -> pd.DataFrame:  # pragma: no cover - should not run
        raise AssertionError("fetch should not be called when cache hits")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", fail_fetch)

    req = TushareDailyBarsRequest(symbol=symbol, start_date="20240201", end_date="20240202")
    df = load_or_fetch_daily_bars(req, cache_dir=cache_dir)
    assert len(df) == 2
    assert df.iloc[0]["close"] == 1.05


def test_retry_with_backoff(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    symbol = "600000.SH"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    attempts: list[int] = []

    def flaky_fetch(_: TushareDailyBarsRequest) -> pd.DataFrame:
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise TimeoutError("network issue")
        return pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-03-01"]),
                "open": [10],
                "high": [11],
                "low": [9],
                "close": [10.5],
                "volume": [1000],
                "amount": [1_000_000],
            }
        ).set_index("date")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", flaky_fetch)

    # 避免真实 sleep
    monkeypatch.setattr(ts_src.time, "sleep", lambda *_: None)

    req = TushareDailyBarsRequest(symbol=symbol, start_date="20240301", end_date="20240301")
    df = load_or_fetch_daily_bars(req, cache_dir=cache_dir, retries=3, backoff_base=0.01)
    assert len(df) == 1
    assert len(attempts) == 3

