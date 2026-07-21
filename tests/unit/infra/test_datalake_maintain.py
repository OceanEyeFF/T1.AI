"""U-L2: incremental maintain semantics via tushare _date_ranges_to_fetch + DataLake."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.data.tushare_source import _date_ranges_to_fetch
from ashare_infra.lake import DataLake


def test_date_ranges_full_when_empty() -> None:
    start, end = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-10")
    ranges = _date_ranges_to_fetch(pd.DataFrame(), start, end)
    assert ranges == [(start, end)]


def test_date_ranges_only_extends_tail() -> None:
    existing = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-05"]),
    )
    start, end = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-10")
    ranges = _date_ranges_to_fetch(existing, start, end)
    assert len(ranges) == 1
    assert ranges[0][0] == pd.Timestamp("2024-01-06")
    assert ranges[0][1] == end


def test_date_ranges_extends_head_and_tail() -> None:
    existing = pd.DataFrame(
        {"close": [1.0]},
        index=pd.to_datetime(["2024-01-05"]),
    )
    start, end = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-10")
    ranges = _date_ranges_to_fetch(existing, start, end)
    assert ranges[0] == (pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-04"))
    assert ranges[1] == (pd.Timestamp("2024-01-06"), pd.Timestamp("2024-01-10"))


def test_datalake_two_fetch_rounds_second_only_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mock tushare fetch: first call fills [start,mid], second call only (mid+1,end]."""
    import ashare_infra.data.tushare_source as ts

    fetch_calls: list[tuple[str, str]] = []

    def fake_fetch(req):
        fetch_calls.append((req.start_date, req.end_date))
        start = pd.to_datetime(req.start_date)
        end = pd.to_datetime(req.end_date)
        idx = pd.bdate_range(start, end)
        return pd.DataFrame(
            {
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1.0,
                "amount": 1.0,
            },
            index=idx,
        )

    monkeypatch.setattr(ts, "fetch_tushare_daily_bars", fake_fetch)
    # avoid token / network path entirely
    monkeypatch.setattr(ts, "_retry_with_backoff", lambda fn, retries=3, base_delay=0.5: fn())

    lake = DataLake(cache_dir=tmp_path, default_source="tushare")
    # raw 模式保留增量维护语义；qfq/hfq 因复权基准一致性改为整段重取
    # （见 test_phase1_audit_fixes.test_h2_qfq_incremental_refetches_full_span）
    # Round 1: empty cache → full window
    df1 = lake.load_daily_bars("600000", date(2024, 1, 2), date(2024, 1, 5), adjust="raw")
    assert not df1.empty
    assert fetch_calls == [("20240102", "20240105")]

    # Round 2: extend end — only missing tail should be fetched
    fetch_calls.clear()
    df2 = lake.load_daily_bars("600000", date(2024, 1, 2), date(2024, 1, 10), adjust="raw")
    assert not df2.empty
    assert len(fetch_calls) == 1
    assert fetch_calls[0][0] == "20240106"
    assert fetch_calls[0][1] == "20240110"
    assert df2.index.min() == pd.Timestamp("2024-01-02")
    assert df2.index.max() >= pd.Timestamp("2024-01-10")
