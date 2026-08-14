"""MS-R4 / WT-R4-A2-T3: disk layout + schema contracts vs A1 inventory/schema.

Read-only against ``inputs/data/cache`` and the approved research pool.
Cache presence is a hard requirement (2.1): R4 湖已落盘，缺失即合同违约——不再 skip。
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
    """2.1: cache 缺失从 skip 改为硬失败（R4 湖合同，落盘后 skip 分支不可达）。"""
    assert CACHE_ROOT.is_dir(), (
        f"cache root missing: {CACHE_ROOT} — R4 湖合同违约（全池数据应已落盘）"
    )
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
    assert len(bare) == R4_SYMBOLS_COUNT == 60
    return [symbol_to_ts_code(s) for s in bare]


@pytest.mark.contract
def test_r4_pool_binding_constants() -> None:
    assert R4_STOCK_POOL_ID == "custom_research_liquidity_quality_v1"
    assert R4_STOCK_POOL_VERSION == "1"
    assert R4_SYMBOLS_COUNT == 60
    assert R4_HISTORY_START == "2023-01-01"
    bare = _load_pool_bare_symbols()
    assert len(bare) == 60
    # Soft80 formally accepted residual (WT-R4-A3-T4); do not require expand.
    assert R4_SOFT80_STATUS == "accepted_residual"
    assert len(bare) == R4_SYMBOLS_COUNT < R4_SOFT_TARGET


@pytest.mark.contract
def test_trial_subset_excludes_601989_by_default() -> None:
    bare = _load_pool_bare_symbols()
    assert "601989" not in bare  # 2026-08-13 停牌剔除（吸收合并）
    trial = filter_r4_trial_symbols([symbol_to_ts_code(s) for s in bare])
    assert "601989.SH" not in trial
    assert len(trial) == R4_SYMBOLS_COUNT  # 排除表对当前池无交集；函数保留为防御


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


# ---------------------------------------------------------------------------
# 2.2 深度增强（并入 D5）：全 parts 遍历 / 起点锁定 / 连续性 / 尾部新鲜度 / 目录双向一致
# ---------------------------------------------------------------------------

HISTORY_START_TS = pd.Timestamp(R4_HISTORY_START)
# 长假最长 ~11 自然日（春节/国庆+周末）；>15 即真实停牌或拉取缺陷
MAX_NATURAL_GAP_DAYS = 15
# 停牌豁免表（登记制，禁止放宽全局阈值）：
# - GAP_EXEMPTIONS: ts_code -> [(gap_prev, gap_next)] 精确匹配断档首尾交易日
# - TAIL_EXEMPTIONS: ts_code -> [断档后首个交易日]（尾部陈旧豁免，用于池内长期停牌）
GAP_EXEMPTIONS: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = {
    # 以下 4 处为全池仅有的 gap>15d 断档，逐条经 TuShare suspend_d 官方记录验证（S/R）。
    # 002554.SZ：2023-04-19~05-09 真实停牌
    "002554.SZ": [(pd.Timestamp("2023-04-19"), pd.Timestamp("2023-05-09"))],
    # 600150.SH：2024-09-03~09-18 停牌（中国船舶吸收合并中国重工）
    "600150.SH": [(pd.Timestamp("2024-09-02"), pd.Timestamp("2024-09-19"))],
    # 601088.SH：2025-08-01~08-18 真实停牌
    "601088.SH": [(pd.Timestamp("2025-08-01"), pd.Timestamp("2025-08-18"))],
    # 603019.SH：2025-05-26~06-09 真实停牌
    "603019.SH": [(pd.Timestamp("2025-05-23"), pd.Timestamp("2025-06-10"))],
}
TAIL_EXEMPTIONS: dict[str, list[pd.Timestamp]] = {}


def _all_dates(namespace: str, ts_code: str) -> pd.Series:
    frames = []
    for part in _part_paths(namespace, ts_code):
        df = pd.read_parquet(part, columns=["date"])
        frames.append(pd.to_datetime(df["date"]))
    assert frames, f"{namespace}/{ts_code} has no parts"
    return pd.concat(frames).sort_values().drop_duplicates().reset_index(drop=True)


def _is_gap_exempt(ts_code: str, prev: pd.Timestamp, date: pd.Timestamp) -> bool:
    for s, e in GAP_EXEMPTIONS.get(ts_code, []):
        if prev == s and date == e:
            return True
    return False


@pytest.mark.contract
@pytest.mark.parametrize(
    "namespace,required",
    [
        ("tushare_qfq", REQUIRED_QFQ),
        ("tushare_daily_basic", tuple(SUPPORTED_DAILY_BASIC_FIELDS)),
        ("tushare_moneyflow", tuple(SUPPORTED_MONEYFLOW_FIELDS)),
    ],
)
def test_all_parts_full_schema_and_year_alignment(
    pool_ts_codes: list[str], namespace: str, required: tuple[str, ...]
) -> None:
    """全池 × 全分区遍历：每块 part 非空、schema 齐全、日期与 year= 分区对齐。"""
    _require_cache()
    checked = 0
    for ts in pool_ts_codes:
        parts = _part_paths(namespace, ts)
        assert parts, f"{namespace}/{ts} has no parts"
        for part in parts:
            df = pd.read_parquet(part)
            assert not df.empty, f"{part} is empty"
            for col in required:
                assert col in df.columns, f"{part} missing column {col}"
            year = int(part.parent.name.split("=", 1)[1])
            dates = pd.to_datetime(df["date"])
            assert (dates.dt.year == year).all(), f"{part} has dates outside {year}"
            checked += 1
    assert checked >= R4_SYMBOLS_COUNT * 3, f"unexpectedly few partitions checked: {checked}"


@pytest.mark.contract
def test_pool_history_start_locked_full_pool(pool_ts_codes: list[str]) -> None:
    """全池起点锁定：每只最早日期 ∈ [history_start, history_start+31d]。"""
    _require_cache()
    upper = HISTORY_START_TS + pd.Timedelta(days=31)
    for ts in pool_ts_codes:
        dates = _all_dates("tushare_qfq", ts)
        date_min = dates.iloc[0]
        assert date_min >= HISTORY_START_TS, f"{ts} starts too early: {date_min}"
        assert date_min <= upper, f"{ts} starts too late: {date_min} (> {upper.date()})"


@pytest.mark.contract
def test_pool_continuity_no_abnormal_gaps(pool_ts_codes: list[str]) -> None:
    """全池连续性：相邻交易日断档 >15 自然日即失败（豁免表登记制）。"""
    _require_cache()
    for ts in pool_ts_codes:
        dates = _all_dates("tushare_qfq", ts)
        gap_days = dates.diff().dt.days
        for i in range(1, len(dates)):
            gap = gap_days.iloc[i]
            prev, date = dates.iloc[i - 1], dates.iloc[i]
            if gap > MAX_NATURAL_GAP_DAYS and not _is_gap_exempt(ts, prev, date):
                pytest.fail(
                    f"{ts} abnormal gap: {int(gap)} natural days "
                    f"({prev.date()} .. {date.date()})"
                )


@pytest.mark.contract
def test_pool_tail_recency_within_21d(pool_ts_codes: list[str]) -> None:
    """尾部新鲜度：每只最后交易日距全池最新交易日 ≤21 自然日（豁免表登记制）。"""
    _require_cache()
    ends: dict[str, pd.Timestamp] = {}
    for ts in pool_ts_codes:
        ends[ts] = _all_dates("tushare_qfq", ts).iloc[-1]
    global_max = max(ends.values())
    for ts, end in ends.items():
        stale_days = (global_max - end).days
        if stale_days > 21 and end not in TAIL_EXEMPTIONS.get(ts, []):
            pytest.fail(
                f"{ts} stale tail: ends {end.date()} "
                f"({stale_days}d behind pool max {global_max.date()})"
            )


@pytest.mark.contract
def test_pool_dirset_matches_symbols_bidirectional(pool_ts_codes: list[str]) -> None:
    """池 ↔ 分区目录双向一致：qfq=池∪{锚点}，basic/mf=池，无多余无缺失。"""
    _require_cache()
    expected_pool = set(pool_ts_codes)
    qfq_dirs = {d.name for d in (CACHE_ROOT / "tushare_qfq").iterdir() if d.is_dir()}
    assert qfq_dirs == expected_pool | {INDEX_ANCHOR}, (
        f"qfq dirs mismatch: extra={qfq_dirs - expected_pool - {INDEX_ANCHOR}}, "
        f"missing={expected_pool | {INDEX_ANCHOR} - qfq_dirs}"
    )
    for ns in ("tushare_daily_basic", "tushare_moneyflow"):
        dirs = {d.name for d in (CACHE_ROOT / ns).iterdir() if d.is_dir()}
        assert dirs == expected_pool, (
            f"{ns} dirs mismatch: extra={dirs - expected_pool}, missing={expected_pool - dirs}"
        )
