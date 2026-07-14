from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ashare_lab.data import tushare_source as ts_src
from ashare_lab.data.tushare_source import (
    SUPPORTED_DAILY_BASIC_FIELDS,
    SUPPORTED_FIELDS,
    SUPPORTED_MONEYFLOW_FIELDS,
    TushareDailyBarsRequest,
    TushareDailyBasicRequest,
    TushareMoneyflowRequest,
    _apply_price_adjustment,
    _normalize_tushare_daily,
    _normalize_tushare_table,
    load_or_fetch_daily_bars,
    load_or_fetch_daily_basic,
    load_or_fetch_moneyflow,
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


def test_normalize_daily_basic_mapping() -> None:
    raw = pd.DataFrame(
        {
            "trade_date": ["20240103", "20240102"],
            "turnover_rate": [3.2, 2.8],
            "turnover_rate_f": [4.1, 3.7],
            "volume_ratio": [1.2, 0.9],
            "total_mv": [100000, 101000],
        }
    )
    df = _normalize_tushare_table(raw, SUPPORTED_DAILY_BASIC_FIELDS)
    assert list(df.columns) == list(SUPPORTED_DAILY_BASIC_FIELDS)
    assert df.index[0] == pd.Timestamp("2024-01-02")
    assert pd.api.types.is_numeric_dtype(df["turnover_rate"])
    assert pd.isna(df.iloc[0]["pe_ttm"])


def test_normalize_moneyflow_mapping() -> None:
    raw = pd.DataFrame(
        {
            "trade_date": ["20240103", "20240102"],
            "buy_sm_amount": [100.0, 120.0],
            "sell_sm_amount": [95.0, 110.0],
            "buy_lg_amount": [80.0, 70.0],
            "sell_lg_amount": [60.0, 65.0],
            "net_mf_amount": [25.0, 15.0],
        }
    )
    df = _normalize_tushare_table(raw, SUPPORTED_MONEYFLOW_FIELDS)
    assert list(df.columns) == list(SUPPORTED_MONEYFLOW_FIELDS)
    assert df.index[-1] == pd.Timestamp("2024-01-03")
    assert pd.api.types.is_numeric_dtype(df["net_mf_amount"])
    assert pd.isna(df.iloc[0]["buy_sm_vol"])


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
    assert (cache_dir / "tushare_qfq" / symbol / "year=2024" / "part.parquet").exists()

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
    ts_src._write_partitioned(base_df, cache_dir / "tushare_qfq" / symbol)

    def fail_fetch(_: TushareDailyBarsRequest) -> pd.DataFrame:  # pragma: no cover - should not run
        raise AssertionError("fetch should not be called when cache hits")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", fail_fetch)

    req = TushareDailyBarsRequest(symbol=symbol, start_date="20240201", end_date="20240202")
    df = load_or_fetch_daily_bars(req, cache_dir=cache_dir)
    assert len(df) == 2
    assert df.iloc[0]["close"] == 1.05


def test_apply_price_adjustment_qfq() -> None:
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "open": [10.0, 20.0, 30.0],
            "high": [11.0, 21.0, 31.0],
            "low": [9.0, 19.0, 29.0],
            "close": [10.5, 20.5, 30.5],
            "volume": [100, 100, 100],
            "amount": [1000, 1000, 1000],
        }
    ).set_index("date")
    adj = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "adj_factor": [1.0, 2.0, 4.0],
        }
    ).set_index("date")

    out = _apply_price_adjustment(daily, adj, "qfq")
    # qfq 使用最后一个因子做基准，前两日价格按 1/4、2/4 缩放
    assert out.loc[pd.Timestamp("2024-01-01"), "close"] == pytest.approx(10.5 * 0.25)
    assert out.loc[pd.Timestamp("2024-01-02"), "close"] == pytest.approx(20.5 * 0.5)
    assert out.loc[pd.Timestamp("2024-01-03"), "close"] == pytest.approx(30.5)


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


def test_daily_basic_partition_cache_and_incremental(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "600519.SH"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    first_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "turnover_rate": [1.0, 1.2],
            "turnover_rate_f": [1.5, 1.6],
        }
    ).set_index("date")
    second_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-03", "2024-01-04"]),
            "turnover_rate": [1.1, 1.0],
            "turnover_rate_f": [1.4, 1.3],
        }
    ).set_index("date")

    def fake_fetch(req: TushareDailyBasicRequest) -> pd.DataFrame:
        if req.end_date == "20240102":
            return first_df
        return second_df

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_basic", fake_fetch)

    req = TushareDailyBasicRequest(symbol=symbol, start_date="20240101", end_date="20240102")
    df1 = load_or_fetch_daily_basic(req, cache_dir=cache_dir)
    assert len(df1) == 2
    assert (cache_dir / "tushare_daily_basic" / symbol / "year=2024" / "part.parquet").exists()

    req2 = TushareDailyBasicRequest(symbol=symbol, start_date="20240101", end_date="20240104")
    df2 = load_or_fetch_daily_basic(req2, cache_dir=cache_dir)
    assert len(df2) == 4
    assert df2.index.is_unique
    assert list(df2.columns) == list(SUPPORTED_DAILY_BASIC_FIELDS)


def test_moneyflow_cache_hit_skip_fetch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol = "000001.SZ"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    base_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-01", "2024-02-02"]),
            "buy_sm_amount": [100.0, 110.0],
            "sell_sm_amount": [95.0, 105.0],
            "buy_lg_amount": [50.0, 51.0],
            "sell_lg_amount": [45.0, 49.0],
            "net_mf_amount": [10.0, 7.0],
        }
    ).set_index("date")
    ts_src._write_partitioned(base_df, cache_dir / "tushare_moneyflow" / symbol)

    def fail_fetch(_: TushareMoneyflowRequest) -> pd.DataFrame:  # pragma: no cover
        raise AssertionError("fetch should not be called when cache hits")

    monkeypatch.setattr(ts_src, "fetch_tushare_moneyflow", fail_fetch)

    req = TushareMoneyflowRequest(symbol=symbol, start_date="20240201", end_date="20240202")
    df = load_or_fetch_moneyflow(req, cache_dir=cache_dir)
    assert len(df) == 2
    assert list(df.columns) == list(SUPPORTED_MONEYFLOW_FIELDS)
    assert df.iloc[0]["buy_sm_amount"] == 100.0
