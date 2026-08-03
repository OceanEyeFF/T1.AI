"""Post-A4: derived prune-to-cache + incremental merge semantics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts_src
from ashare_infra.lake.r4_derived_io import (
    list_r4_derived_years,
    list_r4_qfq_cache_years,
    merge_r4_derived_by_date,
    prune_r4_derived_years,
    read_r4_derived_parts,
    write_r4_derived_parts,
)
from ashare_lab.derived.builder import build_r4_derived_symbol


def _make_bars(n: int = 60, start: str = "2024-01-02") -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=n)
    close = pd.Series(range(100, 100 + n), index=dates, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "amount": 1.0e6,
        },
        index=dates,
    )


def _momentum_frame(dates: pd.DatetimeIndex, value: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "return_5d": value,
            "return_10d": value,
            "return_20d": value,
        },
        index=dates,
    )


def test_list_qfq_cache_years(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    bars_2024 = _make_bars(n=20, start="2024-01-02")
    ts_src._write_partitioned(bars_2024, cache / "tushare_qfq" / "600519.SH")
    assert list_r4_qfq_cache_years("600519.SH", cache_dir=cache) == {2024}


def test_prune_removes_years_outside_keep_set(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    dates_23 = pd.bdate_range("2023-06-01", periods=5)
    dates_24 = pd.bdate_range("2024-01-02", periods=5)
    write_r4_derived_parts(
        _momentum_frame(dates_23.union(dates_24), 0.1),
        "momentum",
        "600519.SH",
        root=derived,
    )
    assert list_r4_derived_years("momentum", "600519.SH", root=derived) == {
        2023,
        2024,
    }
    removed = prune_r4_derived_years(
        "momentum", "600519.SH", keep_years={2024}, root=derived
    )
    assert any(p.name == "year=2023" for p in removed)
    assert list_r4_derived_years("momentum", "600519.SH", root=derived) == {2024}


def test_merge_r4_derived_by_date_new_wins() -> None:
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    existing = _momentum_frame(idx, 1.0)
    new = _momentum_frame(pd.to_datetime(["2024-01-03", "2024-01-04"]), 2.0)
    merged = merge_r4_derived_by_date(existing, new)
    assert list(merged.index.astype(str)) == [
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
    ]
    assert float(merged.loc["2024-01-02", "return_5d"]) == 1.0
    assert float(merged.loc["2024-01-03", "return_5d"]) == 2.0
    assert float(merged.loc["2024-01-04", "return_5d"]) == 2.0


def test_full_rebuild_prunes_stale_year_outside_cache(tmp_path: Path) -> None:
    """Write derived 2023+2024; cache only 2024 → full build prunes 2023."""
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    ts_code = "600519.SH"

    bars_2024 = _make_bars(n=80, start="2024-01-02")
    ts_src._write_partitioned(bars_2024, cache / "tushare_qfq" / ts_code)

    # Stale derived year not present in cache.
    stale_dates = pd.bdate_range("2023-03-01", periods=10)
    for fam, cols in (
        ("momentum", ["return_5d", "return_10d", "return_20d"]),
        ("technical", ["rsi_14"]),
    ):
        frame = pd.DataFrame({c: 0.5 for c in cols}, index=stale_dates)
        # Also seed 2024 so write path is realistic before rebuild.
        frame = pd.concat(
            [
                frame,
                pd.DataFrame({c: 0.1 for c in cols}, index=bars_2024.index[:5]),
            ]
        )
        write_r4_derived_parts(frame, fam, ts_code, root=derived)

    assert 2023 in list_r4_derived_years("momentum", ts_code, root=derived)
    assert list_r4_qfq_cache_years(ts_code, cache_dir=cache) == {2024}

    result = build_r4_derived_symbol(
        ts_code, cache_dir=cache, derived_root=derived, rebuild="full"
    )
    assert result.status == "built"
    assert list_r4_derived_years("momentum", ts_code, root=derived) == {2024}
    assert list_r4_derived_years("technical", ts_code, root=derived) == {2024}
    assert 2023 not in list_r4_derived_years("momentum", ts_code, root=derived)


def test_incremental_merge_new_wins_on_shared_date(tmp_path: Path) -> None:
    """Existing date value replaced by newly computed value on incremental rebuild."""
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    ts_code = "600519.SH"
    bars = _make_bars(n=80, start="2024-01-02")
    ts_src._write_partitioned(bars, cache / "tushare_qfq" / ts_code)

    # Seed wrong existing values for a date that will be recomputed.
    seed_idx = bars.index[30:35]
    write_r4_derived_parts(
        _momentum_frame(seed_idx, 99.0),
        "momentum",
        ts_code,
        root=derived,
    )
    before = read_r4_derived_parts("momentum", ts_code, root=derived)
    assert float(before.loc[seed_idx[0], "return_5d"]) == 99.0

    result = build_r4_derived_symbol(
        ts_code, cache_dir=cache, derived_root=derived, rebuild="incremental"
    )
    assert result.status == "built"
    after = read_r4_derived_parts("momentum", ts_code, root=derived)
    # Date present once; value must not remain the seeded 99.0.
    assert after.index.duplicated().sum() == 0
    assert seed_idx[0] in after.index
    assert float(after.loc[seed_idx[0], "return_5d"]) != 99.0


def test_full_rebuild_does_not_leave_stale_years_outside_cache(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    ts_code = "000001.SZ"
    bars = _make_bars(n=40, start="2024-06-03")
    ts_src._write_partitioned(bars, cache / "tushare_qfq" / ts_code)

    write_r4_derived_parts(
        _momentum_frame(pd.bdate_range("2022-01-03", periods=5), 0.0),
        "momentum",
        ts_code,
        root=derived,
    )
    build_r4_derived_symbol(
        ts_code, cache_dir=cache, derived_root=derived, rebuild="full"
    )
    years = list_r4_derived_years("momentum", ts_code, root=derived)
    cache_years = list_r4_qfq_cache_years(ts_code, cache_dir=cache)
    assert years <= cache_years
    assert 2022 not in years
