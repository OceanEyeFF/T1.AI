"""D5 尾项：validator adapter kwargs 锁定合同（双路 CodeReview P2 残余）。

锁定点：
1. TushareSourceAdapter 构造参数经 ``make_r4_datalake`` 原样透传
   （cache_dir→cache_dir、refresh→refresh、token→tushare_token），无静默吞参。
2. ``fetch_daily_bars`` 调 ``lake.load_daily_bars`` 时 source/adjust/日期规范化正确。
3. ODPSourceAdapter 构造参数原样到达 DataLake 的 odp_* 字段。
4. 三个 adapter 构造签名无 ``**kwargs`` —— 未知参数必须 TypeError（拒绝吞参）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from ashare_lab.recommendation import validator as v

REQUIRED_COLS = list(v._REQUIRED_DAILY_COLS)


def _df_with_close(dates: list[str], closes: list[float]) -> pd.DataFrame:
    idx = pd.to_datetime(dates)
    out = pd.DataFrame({"date": idx, "close": closes})
    return out.set_index("date")


@pytest.mark.contract
def test_tushare_adapter_ctor_passes_kwargs_to_make_r4_datalake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    class FakeLake:
        def load_daily_bars(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
            return pd.DataFrame()

    def fake_make(cache_dir: Any, *, refresh: bool = False, tushare_token: Any = None, **rest: Any) -> FakeLake:
        captured.update(cache_dir=cache_dir, refresh=refresh, tushare_token=tushare_token, rest=rest)
        return FakeLake()

    import ashare_infra.lake.r4_contract as r4c

    monkeypatch.setattr(r4c, "make_r4_datalake", fake_make)

    adapter = v.TushareSourceAdapter(
        cache_dir=tmp_path, adjust="hfq", refresh=True, token="secret-token"
    )
    assert captured["cache_dir"] == tmp_path
    assert captured["refresh"] is True
    assert captured["tushare_token"] == "secret-token"
    assert adapter.adjust == "hfq", "adjust 是 adapter 侧调用参数，非构造透传项"


@pytest.mark.contract
def test_tushare_adapter_defaults_cache_dir_and_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeLake:
        def load_daily_bars(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
            return pd.DataFrame()

    def fake_make(cache_dir: Any, *, refresh: bool = False, tushare_token: Any = None, **rest: Any) -> FakeLake:
        captured.update(cache_dir=cache_dir, refresh=refresh, tushare_token=tushare_token, rest=rest)
        return FakeLake()

    import ashare_infra.lake.r4_contract as r4c

    monkeypatch.setattr(r4c, "make_r4_datalake", fake_make)
    adapter = v.TushareSourceAdapter()
    assert adapter.cache_dir == Path("inputs/data/cache")
    assert captured["refresh"] is False
    assert captured["tushare_token"] is None


@pytest.mark.contract
def test_tushare_fetch_passes_source_adjust_and_normalized_dates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Any, ...]] = []

    class FakeLake:
        def load_daily_bars(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
            calls.append((args, kwargs))
            return _df_with_close(["2025-01-02", "2025-01-03"], [10.0, 10.5])

    def fake_make(cache_dir: Any, *, refresh: bool = False, tushare_token: Any = None, **rest: Any) -> FakeLake:
        return FakeLake()

    import ashare_infra.lake.r4_contract as r4c

    monkeypatch.setattr(r4c, "make_r4_datalake", fake_make)
    adapter = v.TushareSourceAdapter(cache_dir=tmp_path, adjust="hfq")
    bars = adapter.fetch_daily_bars(["600519"], start_date="2025-01-02", end_date="2025-01-03")
    assert len(calls) == 1
    (args, kwargs), = calls
    assert args == ("600519.SH", "20250102", "20250103")
    assert kwargs == {"source": "tushare", "adjust": "hfq"}
    assert list(bars["600519"].columns) == REQUIRED_COLS


@pytest.mark.contract
def test_odp_adapter_ctor_passes_odp_kwargs(tmp_path: Path) -> None:
    adapter = v.ODPSourceAdapter(
        cache_dir=tmp_path,
        provider="eodhd",
        interval="1wk",
        refresh=True,
        base_url="http://127.0.0.1:8000",
        prefer_rest=True,
    )
    lake = adapter._lake
    assert lake.cache_dir == tmp_path
    assert lake.default_source == "odp"
    assert lake.refresh is True
    assert lake.odp_provider == "eodhd"
    assert lake.odp_interval == "1wk"
    assert lake.odp_base_url == "http://127.0.0.1:8000"
    assert lake.odp_prefer_rest is True


@pytest.mark.contract
def test_odp_fetch_passes_odp_symbol_and_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Any, ...]] = []

    class FakeLake:
        cache_dir = tmp_path
        default_source = "odp"
        refresh = False
        odp_provider = "yfinance"
        odp_interval = "1d"
        odp_base_url = None
        odp_prefer_rest = False

        def load_daily_bars(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
            calls.append((args, kwargs))
            return _df_with_close(["2025-01-02"], [10.0])

    def fake_datalake(**kwargs: Any) -> FakeLake:
        return FakeLake()

    import ashare_infra.lake as lake_mod

    monkeypatch.setattr(lake_mod, "DataLake", fake_datalake)
    adapter = v.ODPSourceAdapter(cache_dir=tmp_path)
    adapter.fetch_daily_bars(["600519"], start_date="2025-01-02", end_date="2025-01-02")
    assert len(calls) == 1
    (args, kwargs), = calls
    assert args == ("600519.SS", "20250102", "20250102")
    assert kwargs == {"source": "odp"}


@pytest.mark.contract
def test_hs300_calendar_normalizes_symbol_and_dates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cal = v.HS300IndexCalendarSource(cache_dir=tmp_path)
    calls: list[tuple[Any, ...]] = []

    def fake_index(symbol: str, start: str, end: str, **rest: Any) -> pd.DataFrame:
        calls.append((symbol, start, end, rest))
        return _df_with_close(["2025-01-02", "2025-01-03"], [1.0, 1.1])

    monkeypatch.setattr(cal._lake, "load_index_daily", fake_index)
    cal.fetch_hs300_daily("2025-01-02", "2025-01-03")
    assert calls == [("000300", "20250102", "20250103", {})]


@pytest.mark.contract
@pytest.mark.parametrize(
    "adapter_cls",
    [v.TushareSourceAdapter, v.ODPSourceAdapter, v.HS300IndexCalendarSource],
)
def test_adapter_ctors_reject_unknown_kwargs(
    adapter_cls: type, tmp_path: Path
) -> None:
    """无 **kwargs 吞参：未知参数必须 TypeError（签名显式）。"""
    with pytest.raises(TypeError):
        adapter_cls(cache_dir=tmp_path, unexpected_kwarg=123)
