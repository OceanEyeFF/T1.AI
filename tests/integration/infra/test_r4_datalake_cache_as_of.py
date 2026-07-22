"""WT-R4-A2-T4: cache-hit + as_of via make_r4_datalake (no live)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts_src
from ashare_infra.lake.r4_contract import (
    R4_ADJUST_DEFAULT,
    make_r4_datalake,
    r4_approved_daily_per_api,
    r4_approved_rpm,
)


def _seed_qfq_cache(cache_dir: Path, ts_code: str) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            ),
            "open": [10.0, 11.0, 12.0, 13.0],
            "high": [10.5, 11.5, 12.5, 13.5],
            "low": [9.5, 10.5, 11.5, 12.5],
            "close": [10.2, 11.2, 12.2, 13.2],
            "volume": [1000.0, 1100.0, 1200.0, 1300.0],
            "amount": [1.0e6, 1.1e6, 1.2e6, 1.3e6],
        }
    ).set_index("date")
    ts_src._write_partitioned(frame, cache_dir / "tushare_qfq" / ts_code)
    return frame


@pytest.mark.integration
def test_r4_datalake_cache_hit_skips_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ts_code = "601318.SH"
    cache_dir = tmp_path / "cache"
    _seed_qfq_cache(cache_dir, ts_code)

    def fail_fetch(_req):  # pragma: no cover - must not run
        raise AssertionError("fetch must not run on R4 cache hit")

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", fail_fetch)

    lake = make_r4_datalake(cache_dir=cache_dir, refresh=False)
    df = lake.load_daily_bars(
        ts_code,
        "20240102",
        "20240105",
        source="tushare",
        adjust=R4_ADJUST_DEFAULT,
    )
    assert len(df) == 4
    assert df.index.min() == pd.Timestamp("2024-01-02")
    assert df.index.max() == pd.Timestamp("2024-01-05")


@pytest.mark.integration
def test_r4_datalake_as_of_truncates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ts_code = "601318.SH"
    cache_dir = tmp_path / "cache"
    _seed_qfq_cache(cache_dir, ts_code)
    monkeypatch.setattr(
        ts_src,
        "fetch_tushare_daily_bars",
        lambda _req: (_ for _ in ()).throw(AssertionError("no fetch")),
    )

    lake = make_r4_datalake(cache_dir=cache_dir)
    df = lake.load_daily_bars(
        ts_code,
        "20240102",
        "20240105",
        source="tushare",
        adjust=R4_ADJUST_DEFAULT,
        as_of=date(2024, 1, 3),
    )
    assert len(df) == 2
    assert df.index.max() == pd.Timestamp("2024-01-03")


@pytest.mark.integration
def test_r4_approved_caps_promoted_config() -> None:
    assert r4_approved_rpm() == 180
    assert r4_approved_daily_per_api() == 80000
