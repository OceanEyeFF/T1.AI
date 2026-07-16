"""Smoke tests for DataLake façade (mocked fetch, no network)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.guard.scope import DataScope
from ashare_infra.lake import DataLake


def test_datalake_akshare_wrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ashare_infra.data.akshare_source as ak

    frames = pd.DataFrame(
        {
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000.0],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )
    frames.index.name = "date"

    def fake_load(req, cache_dir, refresh=False):
        _ = req, cache_dir, refresh
        return frames.copy()

    monkeypatch.setattr(ak, "load_or_fetch_daily_bars", fake_load)
    lake = DataLake(cache_dir=tmp_path, default_source="akshare")
    df = lake.load_daily_bars("000001", "20240101", "20240131")
    assert len(df) == 1
    assert float(df.iloc[0]["close"]) == 10.5


def test_datalake_scope_bars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ashare_infra.data.akshare_source as ak

    def fake_load(req, cache_dir, refresh=False):
        _ = cache_dir, refresh
        idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
        return pd.DataFrame(
            {"open": [1, 2], "high": [1, 2], "low": [1, 2], "close": [1, 2], "volume": [1, 2]},
            index=idx,
        )

    monkeypatch.setattr(ak, "load_or_fetch_daily_bars", fake_load)
    lake = DataLake(cache_dir=tmp_path, default_source="akshare")
    scope = DataScope(
        symbols=frozenset({"000001", "600519"}),
        window_start=date(2024, 1, 1),
        window_end=date(2024, 1, 31),
    )
    out = lake.load_scope_bars(scope)
    assert set(out) == {"000001", "600519"}


def test_datalake_as_of_truncates_future_bars(tmp_path: Path) -> None:
    """U-G7: cache may hold future bars; as_of must not leak them."""
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-10"])
    frame = pd.DataFrame(
        {"open": [1, 2, 9], "high": [1, 2, 9], "low": [1, 2, 9], "close": [1, 2, 9], "volume": [1, 2, 9]},
        index=idx,
    )

    def loader(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
        _ = symbol, start, end, adjust
        return frame.copy()

    lake = DataLake(cache_dir=tmp_path, default_source="smoke", loader=loader)
    df = lake.load_daily_bars("600000", "20240101", "20240131", as_of=date(2024, 1, 3))
    assert list(df.index.date) == [date(2024, 1, 2), date(2024, 1, 3)]
    assert date(2024, 1, 10) not in set(df.index.date)


def test_datalake_scope_bars_as_of(tmp_path: Path) -> None:
    idx = pd.to_datetime(["2024-01-02", "2024-01-05", "2024-01-15"])
    frame = pd.DataFrame(
        {"open": [1, 2, 3], "high": [1, 2, 3], "low": [1, 2, 3], "close": [1, 2, 3], "volume": [1, 2, 3]},
        index=idx,
    )

    def loader(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
        _ = symbol, start, end, adjust
        return frame.copy()

    lake = DataLake(cache_dir=tmp_path, default_source="smoke", loader=loader)
    scope = DataScope(
        symbols=frozenset({"600000"}),
        window_start=date(2024, 1, 1),
        window_end=date(2024, 1, 31),
    )
    out = lake.load_scope_bars(scope, as_of=date(2024, 1, 5))
    assert set(out) == {"600000"}
    assert list(out["600000"].index.date) == [date(2024, 1, 2), date(2024, 1, 5)]
