"""committed seeded-cache fixture 的 R4 schema 合同（永不 skip）。

真实湖合同（test_r4_cache_schema_contract.py）依赖 ``inputs/data/cache``，
cache 缺失时全部 skip——fixture 漂移不会有任何 CI 变红。本文件对
tests/fixtures/infra_a/seeded_cache 直接断言，锁定：
- 分区布局 {ts_code}/year=YYYY/part.parquet
- 列集合 = date + SUPPORTED_FIELDS
- date dtype datetime64、年份与分区一致、唯一、升序、无 NaN
- 旧 akshare 目录 / 裸代码目录 / flat CSV 不得存在
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.data.tushare_source import SUPPORTED_FIELDS
from tests.support.paths import REPO_ROOT

SEEDED_ROOT = REPO_ROOT / "tests/fixtures/infra_a/seeded_cache"


@pytest.mark.contract
@pytest.mark.parametrize("ts_code", ["000001.SZ", "600000.SH"])
def test_seeded_qfq_fixture_matches_r4_contract(ts_code: str) -> None:
    root = SEEDED_ROOT / "tushare_qfq" / ts_code
    parts = sorted(root.glob("year=*/part.parquet"))
    assert parts, f"{ts_code} 无分区文件"
    for part in parts:
        df = pd.read_parquet(part)
        assert set(df.columns) == {"date", *SUPPORTED_FIELDS}, f"{part} 列集合不符"
        dtype_name = str(df["date"].dtype)
        assert dtype_name.startswith("datetime64"), f"{part} date dtype={dtype_name}"
        dates = pd.to_datetime(df["date"])
        year = int(part.parent.name.split("=", 1)[1])
        assert (dates.dt.year == year).all(), f"{part} 存在跨年份行"
        assert dates.is_unique, f"{part} date 重复"
        assert dates.is_monotonic_increasing, f"{part} date 未升序"
        assert not df.isna().any().any(), f"{part} 存在 NaN"


@pytest.mark.contract
def test_seeded_cache_has_no_legacy_layouts() -> None:
    assert not (SEEDED_ROOT / "akshare").exists(), "旧 akshare fixture 目录不应存在"
    # 裸代码目录（旧无后缀布局）不应存在
    bare = SEEDED_ROOT / "tushare_qfq" / "600000"
    assert not bare.exists(), "旧裸代码分区目录不应存在"
    assert list(SEEDED_ROOT.rglob("*.csv")) == [], "seeded_cache 不应再有 flat CSV"


# ---------------------------------------------------------------------------
# 2.3 / D5: 真实 loader 链路离线 round-trip（不手工拼 parquet）
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_real_loader_write_read_roundtrip_offline(tmp_path, monkeypatch) -> None:
    """fixture 与真实湖同链路：fetch(offline seam)→_write_partitioned→读回。

    D5 补强：seeded fixture 文件是手工落盘的历史产物，本测试锁定写入/读取
    链路本身（分区、schema、日期 dtype、去重），防止 loader 行为漂移而
    fixture 合同测试却照常通过。
    """
    import numpy as np

    from ashare_infra.data import tushare_source as ts_src
    from ashare_infra.data.tushare_source import SUPPORTED_FIELDS, TushareDailyBarsRequest

    idx = pd.date_range("2023-12-26", "2024-01-31", freq="B")  # 跨年 → 两个分区
    rng = np.random.default_rng(0)
    synthetic = pd.DataFrame(
        {col: rng.uniform(1, 100, len(idx)) for col in SUPPORTED_FIELDS}, index=idx
    )
    calls: list[tuple[str, str, str]] = []

    def fake_fetch(req: TushareDailyBarsRequest) -> pd.DataFrame:
        calls.append((req.symbol, req.start_date, req.end_date))
        lo, hi = pd.to_datetime(req.start_date), pd.to_datetime(req.end_date)
        return synthetic.loc[lo:hi].copy()

    monkeypatch.setattr(ts_src, "fetch_tushare_daily_bars", fake_fetch)

    req = TushareDailyBarsRequest("600000.SH", "20231226", "20240110", adjust="raw")
    first = ts_src.load_or_fetch_daily_bars(req, tmp_path)
    assert len(first) == len(pd.date_range("2023-12-26", "2024-01-10", freq="B"))
    assert first.index.is_monotonic_increasing and first.index.is_unique

    # 增量重叠窗口：验证缺区计算 + 去重合并 + 分区补齐
    second = ts_src.load_or_fetch_daily_bars(
        TushareDailyBarsRequest("600000.SH", "20240102", "20240115", adjust="raw"),
        tmp_path,
    )
    assert second.index.is_unique, "重叠区间未去重"
    assert second.index.max() >= pd.Timestamp("2024-01-15")

    cached_dir = tmp_path / "tushare" / "600000.SH"
    parts = sorted(cached_dir.glob("year=*/part.parquet"))
    assert {p.parent.name for p in parts} == {"year=2023", "year=2024"}, "分区跨年切分不符"

    merged = ts_src._read_cached_partitions(cached_dir)
    assert set(merged.columns) == set(SUPPORTED_FIELDS), "读回列集合漂移"
    assert str(merged.index.dtype).startswith("datetime64")
    assert len(merged) >= len(first)
    for part in parts:
        df = pd.read_parquet(part)
        year = int(part.parent.name.split("=", 1)[1])
        assert (pd.to_datetime(df["date"]).dt.year == year).all(), f"{part} 跨年份行"
