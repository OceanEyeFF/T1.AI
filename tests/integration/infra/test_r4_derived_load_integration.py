"""WT-R4-A4-T3: derived build→load integration (cache-only; zero live)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts_src
from ashare_infra.lake.r4_contract import (
    R4_DERIVED_MOMENTUM_COLUMNS,
    R4_DERIVED_TECHNICAL_COLUMNS,
    make_r4_datalake,
)
from ashare_lab.derived.builder import build_r4_derived_batch


def _seed_qfq(cache_dir: Path, ts_code: str, n: int = 40) -> None:
    idx = pd.bdate_range("2024-01-02", periods=n)
    close = pd.Series(range(100, 100 + n), index=idx, dtype=float)
    frame = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "amount": 1.0e6,
        },
        index=idx,
    )
    frame.index.name = "date"
    ts_src._write_partitioned(frame, cache_dir / "tushare_qfq" / ts_code)


@pytest.mark.integration
def test_build_then_load_roundtrip_zero_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    derived = tmp_path / "derived"
    symbols = ["600519.SH", "000001.SZ"]
    for sym in symbols:
        _seed_qfq(cache, sym)

    monkeypatch.setattr(
        ts_src,
        "fetch_tushare_daily_bars",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no live")),
    )

    summary = build_r4_derived_batch(
        symbols, cache_dir=cache, derived_root=derived
    )
    assert summary["n_built"] == 2
    assert summary["n_skipped"] == 0

    lake = make_r4_datalake(cache_dir=cache, derived_root=derived)
    for sym in symbols:
        families = lake.load_derived_minimal(sym)
        assert set(families) == {"momentum", "technical"}
        mom = families["momentum"]
        tech = families["technical"]
        assert list(mom.columns) == [
            c for c in R4_DERIVED_MOMENTUM_COLUMNS if c != "date"
        ]
        assert list(tech.columns) == [
            c for c in R4_DERIVED_TECHNICAL_COLUMNS if c != "date"
        ]
        assert len(mom) > 0
        assert len(tech) > 0
        # reproducible
        pd.testing.assert_frame_equal(mom, lake.load_derived(sym, "momentum"))

    # as_of does not leak later rows
    sliced = lake.load_derived(
        "600519.SH", "momentum", as_of=date(2024, 1, 15)
    )
    if not sliced.empty:
        assert sliced.index.max() <= pd.Timestamp("2024-01-15")
