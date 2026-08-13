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
