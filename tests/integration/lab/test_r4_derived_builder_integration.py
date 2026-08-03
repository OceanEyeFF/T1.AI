"""WT-R4-A4-T2: derived builder integration (seeded cache → derived parts)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts_src
from ashare_infra.lake.r4_derived_io import read_r4_derived_parts
from ashare_lab.derived import build_r4_derived_batch


def _seed(cache: Path, ts_code: str, n: int = 70) -> None:
    dates = pd.bdate_range("2023-01-03", periods=n)
    close = pd.Series([10.0 + i * 0.1 for i in range(n)], index=dates)
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": 1.0e5,
            "amount": 1.0e6,
        },
        index=dates,
    )
    ts_src._write_partitioned(frame, cache / "tushare_qfq" / ts_code)


@pytest.mark.integration
def test_batch_build_two_symbols_cache_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    _seed(cache, "600519.SH")
    _seed(cache, "000001.SZ")

    monkeypatch.setattr(
        ts_src,
        "fetch_tushare_daily_bars",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no live")),
    )

    summary = build_r4_derived_batch(
        ["600519", "000001.SZ", "300750.SZ"],  # last missing
        cache_dir=cache,
        derived_root=derived,
        start="20230101",
    )
    assert summary["n_symbols"] == 3
    assert summary["n_built"] == 2
    assert summary["n_skipped"] == 1

    for code in ("600519.SH", "000001.SZ"):
        mom = read_r4_derived_parts("momentum", code, root=derived)
        tech = read_r4_derived_parts("technical", code, root=derived)
        assert not mom.empty
        assert not tech.empty
        assert "return_20d" in mom.columns
        assert "rsi_14" in tech.columns
        # year partition exists
        assert list((derived / "momentum" / code).glob("year=*/part.parquet"))
