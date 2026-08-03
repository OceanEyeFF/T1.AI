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
from ashare_infra.lake.r4_contract import r4_derived_symbol_dir
from ashare_lab.derived.builder import (
    build_r4_derived_symbol,
    compute_r4_minimal_families,
)


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
    """TG-21: existing date replaced by lab-computed value on incremental rebuild."""
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

    expected = compute_r4_minimal_families(bars)["momentum"]
    expected_val = float(expected.loc[seed_idx[0], "return_5d"])

    result = build_r4_derived_symbol(
        ts_code, cache_dir=cache, derived_root=derived, rebuild="incremental"
    )
    assert result.status == "built"
    after = read_r4_derived_parts("momentum", ts_code, root=derived)
    # Date present once; value must match lab recompute (new wins).
    assert after.index.duplicated().sum() == 0
    assert seed_idx[0] in after.index
    assert float(after.loc[seed_idx[0], "return_5d"]) == pytest.approx(expected_val)


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


def test_incremental_rebuild_prunes_stale_year_outside_cache(tmp_path: Path) -> None:
    """TG-02: like full prune, but rebuild=incremental still drops stale years."""
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    ts_code = "600519.SH"

    bars_2024 = _make_bars(n=80, start="2024-01-02")
    ts_src._write_partitioned(bars_2024, cache / "tushare_qfq" / ts_code)

    stale_dates = pd.bdate_range("2023-03-01", periods=10)
    for fam, cols in (
        ("momentum", ["return_5d", "return_10d", "return_20d"]),
        ("technical", ["rsi_14"]),
    ):
        frame = pd.DataFrame({c: 0.5 for c in cols}, index=stale_dates)
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
        ts_code, cache_dir=cache, derived_root=derived, rebuild="incremental"
    )
    assert result.status == "built"
    assert list_r4_derived_years("momentum", ts_code, root=derived) == {2024}
    assert list_r4_derived_years("technical", ts_code, root=derived) == {2024}
    assert 2023 not in list_r4_derived_years("momentum", ts_code, root=derived)


def test_skipped_empty_features_still_prunes_stale_years(tmp_path: Path) -> None:
    """TG-03: short bars → skipped_empty_features; stale derived years still pruned."""
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    ts_code = "600519.SH"

    # n=3: all Return*/RSI warm-up → empty after dropna → skipped_empty_features.
    bars = _make_bars(n=3, start="2024-01-02")
    ts_src._write_partitioned(bars, cache / "tushare_qfq" / ts_code)

    stale_dates = pd.bdate_range("2022-03-01", periods=5)
    for fam, cols in (
        ("momentum", ["return_5d", "return_10d", "return_20d"]),
        ("technical", ["rsi_14"]),
    ):
        write_r4_derived_parts(
            pd.DataFrame({c: 0.5 for c in cols}, index=stale_dates),
            fam,
            ts_code,
            root=derived,
        )

    assert 2022 in list_r4_derived_years("momentum", ts_code, root=derived)

    result = build_r4_derived_symbol(
        ts_code, cache_dir=cache, derived_root=derived, rebuild="full"
    )
    assert result.status == "skipped_empty_features"
    mom_years = list_r4_derived_years("momentum", ts_code, root=derived)
    tech_years = list_r4_derived_years("technical", ts_code, root=derived)
    cache_years = list_r4_qfq_cache_years(ts_code, cache_dir=cache)
    assert 2022 not in mom_years
    assert 2022 not in tech_years
    assert mom_years <= cache_years
    assert tech_years <= cache_years


def test_read_r4_derived_parts_skips_corrupt_year(tmp_path: Path) -> None:
    """TG-04: fail-open — good year kept, garbage year skipped, no raise."""
    derived = tmp_path / "derived"
    ts_code = "600519.SH"
    good_dates = pd.bdate_range("2024-01-02", periods=5)
    write_r4_derived_parts(
        _momentum_frame(good_dates, 0.1), "momentum", ts_code, root=derived
    )

    bad_dir = (
        r4_derived_symbol_dir("momentum", ts_code, root=derived) / "year=2023"
    )
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "part.parquet").write_bytes(b"not-a-parquet-file")

    loaded = read_r4_derived_parts("momentum", ts_code, root=derived)
    assert not loaded.empty
    assert set(loaded.index.year) == {2024}
    assert 2023 not in set(loaded.index.year)


def test_write_r4_derived_parts_no_tmp_leftover_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TG-09 (downgraded): success uses part.parquet.tmp→replace; no leftover.

    Does not claim crash-atomic / kill-9 safety — only happy-path tmp+replace.
    """
    replace_srcs: list[Path] = []
    orig_replace = Path.replace

    def _tracking_replace(self: Path, target: Path | str) -> Path:  # noqa: ANN001
        replace_srcs.append(Path(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _tracking_replace)

    derived = tmp_path / "derived"
    ts_code = "600519.SH"
    dates_a = pd.bdate_range("2024-01-02", periods=5)
    dates_b = pd.bdate_range("2024-01-02", periods=8)
    write_r4_derived_parts(_momentum_frame(dates_a, 0.1), "momentum", ts_code, root=derived)
    written = write_r4_derived_parts(
        _momentum_frame(dates_b, 0.2), "momentum", ts_code, root=derived
    )
    assert written
    symbol_dir = r4_derived_symbol_dir("momentum", ts_code, root=derived)
    assert any(p.name.endswith(".tmp") for p in replace_srcs), replace_srcs
    assert list(symbol_dir.glob("year=*/part.parquet.tmp")) == []
    loaded = read_r4_derived_parts("momentum", ts_code, root=derived)
    assert len(loaded) == 8
    assert float(loaded.iloc[0]["return_5d"]) == pytest.approx(0.2)


def test_write_r4_derived_parts_empty_and_missing_column(tmp_path: Path) -> None:
    """TG-10: empty DF → []; missing return_5d → ValueError."""
    derived = tmp_path / "derived"
    empty = pd.DataFrame(
        columns=["return_5d", "return_10d", "return_20d"],
        index=pd.DatetimeIndex([], name="date"),
    )
    assert write_r4_derived_parts(empty, "momentum", "600519.SH", root=derived) == []

    bad = pd.DataFrame(
        {"return_10d": [0.1], "return_20d": [0.2]},
        index=pd.to_datetime(["2024-01-02"]),
    )
    with pytest.raises(ValueError, match="missing columns"):
        write_r4_derived_parts(bad, "momentum", "600519.SH", root=derived)


def test_prune_empty_keep_years_removes_symbol_dir(tmp_path: Path) -> None:
    """TG-11: keep_years=set() removes the symbol dir under the family."""
    derived = tmp_path / "derived"
    ts_code = "600519.SH"
    write_r4_derived_parts(
        _momentum_frame(pd.bdate_range("2024-01-02", periods=3), 0.1),
        "momentum",
        ts_code,
        root=derived,
    )
    symbol_dir = r4_derived_symbol_dir("momentum", ts_code, root=derived)
    assert symbol_dir.is_dir()
    prune_r4_derived_years("momentum", ts_code, keep_years=set(), root=derived)
    assert not symbol_dir.exists()


def test_merge_r4_derived_empty_edges_and_invalid() -> None:
    """TG-12: empty left/right passthrough; invalid frame raises."""
    idx = pd.to_datetime(["2024-01-02"])
    right = _momentum_frame(idx, 2.0)
    left = _momentum_frame(idx, 1.0)

    merged_empty_left = merge_r4_derived_by_date(pd.DataFrame(), right)
    assert list(merged_empty_left.index.astype(str)) == ["2024-01-02"]
    assert float(merged_empty_left.loc["2024-01-02", "return_5d"]) == 2.0

    merged_empty_right = merge_r4_derived_by_date(left, pd.DataFrame())
    assert list(merged_empty_right.index.astype(str)) == ["2024-01-02"]
    assert float(merged_empty_right.loc["2024-01-02", "return_5d"]) == 1.0

    invalid = pd.DataFrame({"return_5d": [0.1]})
    with pytest.raises(ValueError, match="date"):
        merge_r4_derived_by_date(invalid, left)
