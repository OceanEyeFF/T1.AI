"""MS-R4 / WT-R4-A2-T3: disk layout + schema contracts vs A1 inventory/schema.

Read-only against ``inputs/data/cache`` and the approved research pool.
Skips when the local cache root is absent (CI without lake fixtures).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ashare_infra.data.tushare_source import (
    SUPPORTED_DAILY_BASIC_FIELDS,
    SUPPORTED_FIELDS,
    SUPPORTED_MONEYFLOW_FIELDS,
)
from ashare_infra.lake.r4_contract import (
    R4_CACHE_ROOT,
    R4_HISTORY_START,
    R4_INDEX_ANCHOR,
    R4_SOFT80_STATUS,
    R4_SOFT_TARGET,
    R4_STOCK_POOL_ID,
    R4_STOCK_POOL_VERSION,
    R4_SYMBOLS_COUNT,
    filter_r4_trial_symbols,
)
from ashare_lab.symbols import symbol_to_ts_code

REPO_ROOT = Path(__file__).resolve().parents[3]
CACHE_ROOT = REPO_ROOT / R4_CACHE_ROOT
POOL_SYMBOLS_CSV = (
    REPO_ROOT
    / "inputs"
    / "pools"
    / "research_liquidity_quality"
    / "symbols.csv"
)
NAMESPACES = ("tushare_qfq", "tushare_daily_basic", "tushare_moneyflow")
REQUIRED_QFQ = ("date",) + tuple(SUPPORTED_FIELDS)
REQUIRED_BASIC_MIN = ("date", "turnover_rate", "total_mv", "circ_mv")
REQUIRED_MONEYFLOW_MIN = ("date", "net_mf_vol", "net_mf_amount")
INDEX_ANCHOR = R4_INDEX_ANCHOR


def _require_cache() -> Path:
    if not CACHE_ROOT.is_dir():
        pytest.skip(f"cache root missing: {CACHE_ROOT} (local lake required)")
    return CACHE_ROOT


def _load_pool_bare_symbols() -> list[str]:
    assert POOL_SYMBOLS_CSV.is_file(), f"missing pool csv: {POOL_SYMBOLS_CSV}"
    df = pd.read_csv(POOL_SYMBOLS_CSV, dtype=str)
    col = "symbol" if "symbol" in df.columns else df.columns[0]
    symbols = [str(s).strip().zfill(6) for s in df[col].tolist() if str(s).strip()]
    return symbols


def _part_paths(namespace: str, ts_code: str) -> list[Path]:
    symbol_dir = CACHE_ROOT / namespace / ts_code
    if not symbol_dir.is_dir():
        return []
    return sorted(symbol_dir.glob("year=*/part.parquet"))


def _has_parts(namespace: str, ts_code: str) -> bool:
    return bool(_part_paths(namespace, ts_code))


@pytest.fixture(scope="module")
def pool_ts_codes() -> list[str]:
    _require_cache()
    bare = _load_pool_bare_symbols()
    assert len(bare) == R4_SYMBOLS_COUNT == 61
    return [symbol_to_ts_code(s) for s in bare]


@pytest.mark.contract
def test_r4_pool_binding_constants() -> None:
    assert R4_STOCK_POOL_ID == "custom_research_liquidity_quality_v1"
    assert R4_STOCK_POOL_VERSION == "1"
    assert R4_SYMBOLS_COUNT == 61
    assert R4_HISTORY_START == "2023-01-01"
    bare = _load_pool_bare_symbols()
    assert len(bare) == 61
    # Soft80 formally accepted residual (WT-R4-A3-T4); do not require expand.
    assert R4_SOFT80_STATUS == "accepted_residual"
    assert len(bare) == R4_SYMBOLS_COUNT < R4_SOFT_TARGET


@pytest.mark.contract
def test_trial_subset_excludes_601989_by_default() -> None:
    bare = _load_pool_bare_symbols()
    assert "601989" in bare  # still in registry v1@1
    trial = filter_r4_trial_symbols([symbol_to_ts_code(s) for s in bare])
    assert "601989.SH" not in trial
    assert len(trial) == R4_SYMBOLS_COUNT - 1


@pytest.mark.contract
@pytest.mark.parametrize("namespace", NAMESPACES)
def test_pool_full_coverage_per_namespace(pool_ts_codes: list[str], namespace: str) -> None:
    _require_cache()
    missing = [ts for ts in pool_ts_codes if not _has_parts(namespace, ts)]
    assert missing == [], f"{namespace} missing parquet for pool symbols: {missing}"


@pytest.mark.contract
def test_index_510300_qfq_available_after_a3() -> None:
    """A1 G2 → A3 fill: 510300.SH must have qfq parts (fund_daily)."""
    _require_cache()
    anchor_dir = CACHE_ROOT / "tushare_qfq" / INDEX_ANCHOR
    parts = list(anchor_dir.glob("year=*/part.parquet")) if anchor_dir.is_dir() else []
    assert parts, f"{INDEX_ANCHOR} still has no qfq parts after A3 fill"
    df = pd.read_parquet(parts[0])
    for col in REQUIRED_QFQ:
        assert col in df.columns, f"{INDEX_ANCHOR} missing column {col}"


@pytest.mark.contract
def test_index_510300_basic_mf_accepted_empty() -> None:
    """T4 D6: ETF index basic/moneyflow may remain empty (stock APIs N/A)."""
    _require_cache()
    for ns in ("tushare_daily_basic", "tushare_moneyflow"):
        parts = _part_paths(ns, INDEX_ANCHOR)
        # Accepted residual: empty is OK; if parts appear later, schema still readable.
        if parts:
            df = pd.read_parquet(parts[0])
            assert "date" in df.columns


@pytest.mark.contract
def test_qfq_on_disk_required_columns(pool_ts_codes: list[str]) -> None:
    _require_cache()
    sample = pool_ts_codes[0]
    parts = _part_paths("tushare_qfq", sample)
    assert parts, f"no qfq parts for sample {sample}"
    df = pd.read_parquet(parts[0])
    for col in REQUIRED_QFQ:
        assert col in df.columns, f"{sample} {parts[0].name} missing column {col}"
    assert str(df["date"].dtype).startswith("datetime64")


@pytest.mark.contract
def test_daily_basic_on_disk_required_columns(pool_ts_codes: list[str]) -> None:
    _require_cache()
    sample = pool_ts_codes[0]
    parts = _part_paths("tushare_daily_basic", sample)
    assert parts
    df = pd.read_parquet(parts[0])
    for col in REQUIRED_BASIC_MIN:
        assert col in df.columns, f"missing {col}"
    for col in SUPPORTED_DAILY_BASIC_FIELDS:
        assert col in df.columns, f"missing full basic field {col}"


@pytest.mark.contract
def test_moneyflow_on_disk_required_columns(pool_ts_codes: list[str]) -> None:
    _require_cache()
    sample = pool_ts_codes[0]
    parts = _part_paths("tushare_moneyflow", sample)
    assert parts
    df = pd.read_parquet(parts[0])
    for col in REQUIRED_MONEYFLOW_MIN:
        assert col in df.columns, f"missing {col}"
    for col in SUPPORTED_MONEYFLOW_FIELDS:
        assert col in df.columns, f"missing full moneyflow field {col}"


@pytest.mark.contract
def test_year_partition_matches_row_dates(pool_ts_codes: list[str]) -> None:
    _require_cache()
    sample = pool_ts_codes[0]
    for part in _part_paths("tushare_qfq", sample):
        year_token = part.parent.name  # year=YYYY
        assert year_token.startswith("year=")
        year = int(year_token.split("=", 1)[1])
        df = pd.read_parquet(part)
        dates = pd.to_datetime(df["date"])
        assert (dates.dt.year == year).all(), f"{part} has dates outside {year}"


@pytest.mark.contract
def test_pool_qfq_history_starts_on_or_after_contract(pool_ts_codes: list[str]) -> None:
    """Spot-check: earliest observed dates should be ≥ history_start (trading-day lag OK)."""
    _require_cache()
    history_start = pd.Timestamp(R4_HISTORY_START)
    # Sample up to 5 symbols for speed; coverage already asserted for all 61.
    for ts in pool_ts_codes[:5]:
        frames = []
        for part in _part_paths("tushare_qfq", ts):
            df = pd.read_parquet(part, columns=["date"])
            frames.append(pd.to_datetime(df["date"]))
        assert frames, ts
        date_min = pd.concat(frames).min()
        assert date_min >= history_start, f"{ts} date_min {date_min} before {history_start}"


@pytest.mark.contract
def test_bare_to_ts_code_join_key() -> None:
    assert symbol_to_ts_code("000001") == "000001.SZ"
    assert symbol_to_ts_code("600519") == "600519.SH"
    assert symbol_to_ts_code("000001.SZ") == "000001.SZ"
