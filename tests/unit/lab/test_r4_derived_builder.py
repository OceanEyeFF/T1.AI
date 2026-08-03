"""WT-R4-A4-T2: derived builder unit tests (cache-only; zero live)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts_src
from ashare_infra.lake.r4_contract import (
    R4_DERIVED_MOMENTUM_COLUMNS,
    R4_DERIVED_TECHNICAL_COLUMNS,
)
from ashare_infra.lake.r4_derived_io import (
    read_r4_derived_parts,
    write_r4_derived_parts,
)
from ashare_lab.derived.builder import (
    build_r4_derived_symbol,
    compute_r4_minimal_families,
)
from ashare_lab.features.momentum import Return5D, Return10D, Return20D
from ashare_lab.features.technical import RSI


def _make_bars(n: int = 60, start: str = "2024-01-02") -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=n)
    close = pd.Series(range(100, 100 + n), index=dates, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 0.5,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "amount": 1.0e6,
        },
        index=dates,
    )


def test_compute_uses_lab_features_not_second_formula() -> None:
    bars = _make_bars()
    families = compute_r4_minimal_families(bars)
    mom = families["momentum"]
    tech = families["technical"]
    assert list(mom.columns) == ["return_5d", "return_10d", "return_20d"]
    assert list(tech.columns) == ["rsi_14"]
    pd.testing.assert_series_equal(
        mom["return_5d"], Return5D().compute(bars), check_names=False
    )
    pd.testing.assert_series_equal(
        mom["return_10d"], Return10D().compute(bars), check_names=False
    )
    pd.testing.assert_series_equal(
        mom["return_20d"], Return20D().compute(bars), check_names=False
    )
    pd.testing.assert_series_equal(
        tech["rsi_14"], RSI(period=14).compute(bars), check_names=False
    )


def test_write_read_derived_roundtrip(tmp_path: Path) -> None:
    bars = _make_bars()
    families = compute_r4_minimal_families(bars)
    written = write_r4_derived_parts(
        families["momentum"], "momentum", "600519.SH", root=tmp_path
    )
    assert written
    assert all(p.name == "part.parquet" for p in written)
    loaded = read_r4_derived_parts("momentum", "600519.SH", root=tmp_path)
    assert not loaded.empty
    for col in R4_DERIVED_MOMENTUM_COLUMNS:
        if col == "date":
            continue
        assert col in loaded.columns


def test_write_rejects_unknown_family(tmp_path: Path) -> None:
    bars = _make_bars()
    families = compute_r4_minimal_families(bars)
    with pytest.raises(ValueError, match="not in minimal set"):
        write_r4_derived_parts(families["momentum"], "macd", "600519.SH", root=tmp_path)


def test_build_symbol_from_cache_zero_live(tmp_path: Path) -> None:
    # Cache-only path: build reads qfq partitions via read_r4_qfq_cache;
    # fetch_tushare_daily_bars is not on this call path (no fetch monkeypatch).
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    bars = _make_bars(n=80)
    ts_src._write_partitioned(bars, cache / "tushare_qfq" / "600519.SH")

    result = build_r4_derived_symbol(
        "600519.SH", cache_dir=cache, derived_root=derived
    )
    assert result.status == "built"
    assert result.rows_by_family["momentum"] > 0
    assert result.rows_by_family["technical"] > 0
    assert result.parts_written

    mom = read_r4_derived_parts("momentum", "600519.SH", root=derived)
    tech = read_r4_derived_parts("technical", "600519.SH", root=derived)
    assert set(mom.columns) >= set(c for c in R4_DERIVED_MOMENTUM_COLUMNS if c != "date")
    assert set(tech.columns) >= set(c for c in R4_DERIVED_TECHNICAL_COLUMNS if c != "date")


def test_build_skips_missing_cache(tmp_path: Path) -> None:
    result = build_r4_derived_symbol(
        "000001.SZ",
        cache_dir=tmp_path / "cache",
        derived_root=tmp_path / "derived",
    )
    assert result.status == "skipped_empty_cache"
    assert result.parts_written == []


def test_full_rebuild_with_mid_year_start_truncates_year_part(tmp_path: Path) -> None:
    """TG-06: full rebuild with mid-year start overwrites year part to dates >= start."""
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    ts_code = "600519.SH"
    bars = _make_bars(n=120, start="2024-01-02")
    ts_src._write_partitioned(bars, cache / "tushare_qfq" / ts_code)

    first = build_r4_derived_symbol(
        ts_code, cache_dir=cache, derived_root=derived, rebuild="full"
    )
    assert first.status == "built"
    mom_full = read_r4_derived_parts("momentum", ts_code, root=derived)
    full_rows = len(mom_full)
    mid = bars.index[len(bars) // 2]
    start = mid.strftime("%Y%m%d")

    second = build_r4_derived_symbol(
        ts_code,
        cache_dir=cache,
        derived_root=derived,
        start=start,
        rebuild="full",
    )
    assert second.status == "built"
    mom = read_r4_derived_parts("momentum", ts_code, root=derived)
    assert not mom.empty
    assert mom.index.min() >= mid
    assert (mom.index < mid).sum() == 0
    assert len(mom) < full_rows


def test_start_after_cache_range_skips_empty_cache(tmp_path: Path) -> None:
    """TG-13: cache only 2024; start in 2025 → skipped_empty_cache after slice."""
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    bars = _make_bars(n=40, start="2024-01-02")
    ts_src._write_partitioned(bars, cache / "tushare_qfq" / "600519.SH")

    result = build_r4_derived_symbol(
        "600519.SH",
        cache_dir=cache,
        derived_root=derived,
        start="20250101",
    )
    assert result.status == "skipped_empty_cache"
    assert result.parts_written == []


def test_invalid_rebuild_raises(tmp_path: Path) -> None:
    """TG-23: rebuild='partial' → ValueError."""
    with pytest.raises(ValueError, match="rebuild must be"):
        build_r4_derived_symbol(
            "600519.SH",
            cache_dir=tmp_path / "cache",
            derived_root=tmp_path / "derived",
            rebuild="partial",  # type: ignore[arg-type]
        )
