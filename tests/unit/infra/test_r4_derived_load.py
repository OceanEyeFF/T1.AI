"""WT-R4-A4-T3: derived load API unit tests (filesystem only; zero live)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.guard.scope import DataScope
from ashare_infra.lake import DataLake
from ashare_infra.lake.r4_contract import (
    R4_DERIVED_MOMENTUM_COLUMNS,
    R4_DERIVED_TECHNICAL_COLUMNS,
    make_r4_datalake,
)
from ashare_infra.lake.r4_derived_io import write_r4_derived_parts


def _seed_momentum(root: Path, ts_code: str = "600519.SH") -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            ),
            "return_5d": [0.01, 0.02, 0.03, 0.04],
            "return_10d": [0.011, 0.021, 0.031, 0.041],
            "return_20d": [0.012, 0.022, 0.032, 0.042],
        }
    )
    write_r4_derived_parts(frame, "momentum", ts_code, root=root)
    return frame


def _seed_technical(root: Path, ts_code: str = "600519.SH") -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "rsi_14": [40.0, 50.0, 60.0],
        }
    )
    write_r4_derived_parts(frame, "technical", ts_code, root=root)


def test_load_derived_schema_and_as_of(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    _seed_momentum(derived)
    lake = DataLake(cache_dir=tmp_path / "cache", derived_root=derived)
    df = lake.load_derived("600519.SH", "momentum", as_of=date(2024, 1, 3))
    assert list(df.columns) == [c for c in R4_DERIVED_MOMENTUM_COLUMNS if c != "date"]
    assert list(df.index.date) == [date(2024, 1, 2), date(2024, 1, 3)]
    assert date(2024, 1, 5) not in set(df.index.date)


def test_load_derived_start_end_slice(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    _seed_momentum(derived)
    lake = DataLake(cache_dir=tmp_path / "cache", derived_root=derived)
    df = lake.load_derived("600519", "momentum", start="20240103", end="20240104")
    assert list(df.index.date) == [date(2024, 1, 3), date(2024, 1, 4)]


def test_load_derived_minimal_both_families(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    _seed_momentum(derived)
    _seed_technical(derived)
    lake = make_r4_datalake(cache_dir=tmp_path / "cache", derived_root=derived)
    out = lake.load_derived_minimal("600519.SH")
    assert set(out) == {"momentum", "technical"}
    assert list(out["technical"].columns) == [
        c for c in R4_DERIVED_TECHNICAL_COLUMNS if c != "date"
    ]
    assert len(out["momentum"]) == 4
    assert len(out["technical"]) == 3


def test_load_derived_reproducible(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    _seed_momentum(derived)
    lake = make_r4_datalake(cache_dir=tmp_path / "cache", derived_root=derived)
    a = lake.load_derived("600519.SH", "momentum")
    b = lake.load_derived("600519.SH", "momentum")
    pd.testing.assert_frame_equal(a, b)


def test_load_derived_missing_returns_empty_schema(tmp_path: Path) -> None:
    lake = DataLake(cache_dir=tmp_path / "cache", derived_root=tmp_path / "derived")
    df = lake.load_derived("000001.SZ", "momentum")
    assert df.empty
    assert list(df.columns) == [c for c in R4_DERIVED_MOMENTUM_COLUMNS if c != "date"]
    assert df.index.name == "date"


def test_load_derived_rejects_unknown_family(tmp_path: Path) -> None:
    lake = DataLake(cache_dir=tmp_path / "cache", derived_root=tmp_path / "derived")
    with pytest.raises(ValueError, match="not in minimal set"):
        lake.load_derived("600519.SH", "macd")


def test_load_scope_derived(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    _seed_momentum(derived, "600519.SH")
    _seed_momentum(derived, "000001.SZ")
    lake = DataLake(cache_dir=tmp_path / "cache", derived_root=derived)
    scope = DataScope(
        symbols=frozenset({"600519.SH", "000001.SZ", "601318.SH"}),
        window_start=date(2024, 1, 2),
        window_end=date(2024, 1, 5),
    )
    out = lake.load_scope_derived(scope, "momentum")
    assert set(out) == {"600519.SH", "000001.SZ"}  # missing 601318 skipped
    assert len(out["600519.SH"]) == 4


def test_load_derived_zero_live(tmp_path: Path) -> None:
    # Filesystem-only: load_derived reads derived parts; no fetch call site
    # (do not monkeypatch fetch_tushare_daily_bars — that gave false zero-live comfort).
    derived = tmp_path / "derived"
    _seed_momentum(derived)
    lake = make_r4_datalake(cache_dir=tmp_path / "cache", derived_root=derived)
    df = lake.load_derived("600519.SH", "momentum")
    assert len(df) == 4


def test_load_derived_raises_on_missing_required_columns(tmp_path: Path) -> None:
    """TG-05: on-disk parquet missing required cols → ValueError from load_derived."""
    from ashare_infra.lake.r4_contract import (
        R4_DERIVED_PART_FILENAME,
        r4_derived_symbol_dir,
    )

    derived = tmp_path / "derived"
    ts_code = "600519.SH"
    year_dir = r4_derived_symbol_dir("momentum", ts_code, root=derived) / "year=2024"
    year_dir.mkdir(parents=True, exist_ok=True)
    bad = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "junk": [1.0, 2.0],
        }
    )
    bad.to_parquet(year_dir / R4_DERIVED_PART_FILENAME, index=False)

    lake = DataLake(cache_dir=tmp_path / "cache", derived_root=derived)
    with pytest.raises(ValueError, match="missing columns"):
        lake.load_derived(ts_code, "momentum")
