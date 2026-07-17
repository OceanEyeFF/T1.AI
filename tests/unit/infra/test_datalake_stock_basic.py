"""U-L3: DataLake.load_stock_basic + lifecycle → tradable parity with U-G1."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from ashare_infra.lake import DataLake
from tests.support import infra_a as fx


def _seed_stock_basic(cache_dir: Path, *, as_parquet: bool = False) -> Path:
    src = fx.FIXTURE_ROOT / "meta" / "stock_basic.csv"
    dest_dir = cache_dir / "meta"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if as_parquet:
        import pandas as pd

        dest = dest_dir / "stock_basic.parquet"
        pd.read_csv(src, dtype=str).fillna("").to_parquet(dest, index=False)
        return dest
    dest = dest_dir / "stock_basic.csv"
    shutil.copy(src, dest)
    return dest


def test_load_stock_basic_from_cache_csv(tmp_path: Path) -> None:
    _seed_stock_basic(tmp_path)
    lake = DataLake(cache_dir=tmp_path)
    df = lake.load_stock_basic()
    assert set(df.columns) == {"symbol", "list_date", "delist_date"}
    assert "600001" in set(df["symbol"])
    row = df.loc[df["symbol"] == "600001"].iloc[0]
    assert row["list_date"] == date(2024, 1, 8)
    assert row["delist_date"] is None


def test_load_stock_basic_parquet(tmp_path: Path) -> None:
    _seed_stock_basic(tmp_path, as_parquet=True)
    lake = DataLake(cache_dir=tmp_path)
    df = lake.load_stock_basic()
    assert "600002" in set(df["symbol"])
    row = df.loc[df["symbol"] == "600002"].iloc[0]
    assert row["delist_date"] == date(2024, 1, 10)


def test_load_stock_basic_missing_raises(tmp_path: Path) -> None:
    lake = DataLake(cache_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="stock_basic not found"):
        lake.load_stock_basic()


def test_with_stock_basic_meta_tradable_matches_ug1(tmp_path: Path) -> None:
    """Fixture CSV via DataLake → lifecycle → tradable matrix == U-G1 expected."""
    _seed_stock_basic(tmp_path)
    lake = DataLake(cache_dir=tmp_path)

    bare = fx.make_scope(include_meta=False)
    assert bare.symbol_meta == {}

    scoped = lake.with_stock_basic_meta(bare)
    assert set(scoped.symbol_meta) == set(bare.symbols)

    checks = {
        date(2024, 1, 5): set(fx.expected("tradable_on_2024-01-05")),
        date(2024, 1, 8): set(fx.expected("tradable_on_2024-01-08")),
        date(2024, 1, 10): set(fx.expected("tradable_on_2024-01-10")),
    }
    for day, want in checks.items():
        got = {s for s in scoped.symbols if scoped.is_tradable(s, day)}
        assert got == want, f"{day}: got={sorted(got)} want={sorted(want)}"


def test_with_stock_basic_meta_fill_missing_only(tmp_path: Path) -> None:
    _seed_stock_basic(tmp_path)
    lake = DataLake(cache_dir=tmp_path)
    override_scope = fx.make_scope(symbols={"600001"}, include_meta=True)
    # Strip to one override then fill peers from lake
    from ashare_infra.guard.scope import MetaSource, SymbolLifecycle

    custom = SymbolLifecycle(
        list_date=date(2099, 1, 1),
        delist_date=None,
        source=MetaSource(kind="scope_override", evidence_ref="test"),
    )
    partial = override_scope.with_meta({"600001": custom}).with_symbols(
        frozenset({"600001", "600000"})
    )
    filled = lake.with_stock_basic_meta(partial, fill_missing_only=True)
    assert filled.symbol_meta["600001"].list_date == date(2099, 1, 1)
    assert filled.symbol_meta["600000"].list_date == date(2020, 1, 1)
