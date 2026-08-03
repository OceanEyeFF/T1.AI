"""Cache partition IO resilience (F-03: corrupt skip + atomic write)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts_src


def _make_bars(n: int = 20, start: str = "2023-01-03") -> pd.DataFrame:
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


def test_read_cached_partitions_skips_corrupt_year(tmp_path: Path) -> None:
    """TG-01: one good + one garbage year part → only good dates, no raise."""
    symbol_dir = tmp_path / "tushare_qfq" / "600519.SH"
    bars_2023 = _make_bars(n=15, start="2023-01-03")
    ts_src._write_partitioned(bars_2023, symbol_dir)

    bad_dir = symbol_dir / "year=2024"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "part.parquet").write_bytes(b"not-a-parquet-file")

    loaded = ts_src._read_cached_partitions(symbol_dir)
    assert not loaded.empty
    assert set(loaded.index.year) == {2023}
    assert 2024 not in set(loaded.index.year)


def test_write_partitioned_no_tmp_leftover_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TG-08 (downgraded): success uses part.parquet.tmp→replace; no leftover.

    Does not claim crash-atomic / kill-9 safety — only happy-path tmp+replace.
    """
    replace_srcs: list[Path] = []
    orig_replace = Path.replace

    def _tracking_replace(self: Path, target: Path | str) -> Path:  # noqa: ANN001
        replace_srcs.append(Path(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _tracking_replace)

    symbol_dir = tmp_path / "tushare_qfq" / "000001.SZ"
    bars_a = _make_bars(n=10, start="2024-01-02")
    bars_b = _make_bars(n=12, start="2024-01-02")
    ts_src._write_partitioned(bars_a, symbol_dir)
    ts_src._write_partitioned(bars_b, symbol_dir)

    part = symbol_dir / "year=2024" / "part.parquet"
    assert part.is_file()
    roundtrip = pd.read_parquet(part)
    assert "date" in roundtrip.columns
    assert len(roundtrip) == 12

    assert any(p.name.endswith(".tmp") for p in replace_srcs), replace_srcs
    leftovers = list(symbol_dir.glob("year=*/part.parquet.tmp"))
    assert leftovers == []
