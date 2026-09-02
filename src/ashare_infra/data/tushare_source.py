from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Sequence
import time

import pandas as pd

from ashare_infra.data.tushare_batch import is_frequency_wall_error
from ashare_infra.data.tushare_rate_limit import acquire_tushare_call

# Public constants
SUPPORTED_FIELDS: Sequence[str] = ("open", "high", "low", "close", "volume", "amount")
SUPPORTED_DAILY_BASIC_FIELDS: Sequence[str] = (
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe_ttm",
    "pb",
    "ps_ttm",
    "dv_ttm",
    "total_mv",
    "circ_mv",
)
SUPPORTED_MONEYFLOW_FIELDS: Sequence[str] = (
    "buy_sm_vol",
    "buy_sm_amount",
    "sell_sm_vol",
    "sell_sm_amount",
    "buy_md_vol",
    "buy_md_amount",
    "sell_md_vol",
    "sell_md_amount",
    "buy_lg_vol",
    "buy_lg_amount",
    "sell_lg_vol",
    "sell_lg_amount",
    "buy_elg_vol",
    "buy_elg_amount",
    "sell_elg_vol",
    "sell_elg_amount",
    "net_mf_vol",
    "net_mf_amount",
)
SUPPORTED_ADJ_FACTOR_FIELDS: Sequence[str] = ("adj_factor",)
ADJUST_MODES: Sequence[str] = ("raw", "qfq", "hfq")


@dataclass(frozen=True)
class TushareDailyBarsRequest:
    """TuShare 日线请求参数"""

    symbol: str  # ts_code, e.g. 600519.SH
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    adjust: str = "qfq"
    token: str | None = None  # 可显式传入 token，默认从环境变量读取


@dataclass(frozen=True)
class TushareDailyBasicRequest:
    """TuShare daily_basic 请求参数"""

    symbol: str  # ts_code, e.g. 600519.SH
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    token: str | None = None


@dataclass(frozen=True)
class TushareMoneyflowRequest:
    """TuShare moneyflow 请求参数"""

    symbol: str  # ts_code, e.g. 600519.SH
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    token: str | None = None


@dataclass(frozen=True)
class TushareAdjFactorRequest:
    """TuShare adj_factor 请求参数"""

    symbol: str  # ts_code, e.g. 600519.SH
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    token: str | None = None


def _normalize_tushare_daily(df: pd.DataFrame) -> pd.DataFrame:
    """将 TuShare 返回的原始数据规范化为内部 schema"""
    if df is None or df.empty:
        return pd.DataFrame(columns=SUPPORTED_FIELDS)

    # TuShare pro.daily 返回 trade_date 降序，需要转成升序并对齐字段
    df = df.rename(
        columns={
            "trade_date": "date",
            "vol": "volume",
        }
    )
    if "amount" in df.columns:
        # TuShare 的 amount 单位为千元
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        # 保持同一单位（不再转换），由上层自行理解

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    keep_cols = [c for c in SUPPORTED_FIELDS if c in df.columns]
    df = df[keep_cols].copy()
    for col in keep_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _normalize_tushare_adj_factor(df: pd.DataFrame) -> pd.DataFrame:
    """规范化 TuShare adj_factor 响应。"""
    return _normalize_tushare_table(df, SUPPORTED_ADJ_FACTOR_FIELDS)


def _normalize_tushare_table(df: pd.DataFrame, fields: Sequence[str]) -> pd.DataFrame:
    """将 TuShare 表接口结果规范化为日期索引 + 数值列。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=list(fields))

    if "trade_date" in df.columns:
        df = df.rename(columns={"trade_date": "date"})
    if "date" not in df.columns:
        raise ValueError("tushare table response must contain `trade_date` or `date` column")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    for col in fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    out = df.reindex(columns=list(fields)).copy()
    return out


def _get_tushare_pro(token: str | None = None):  # pragma: no cover - mostly integration
    import os
    import tushare as ts  # lazy import

    tk = token or os.environ.get("TUSHARE_TOKEN")
    if not tk:
        raise ValueError(
            "TUSHARE_TOKEN not found. Please set it in environment or pass via token parameter.\n"
            "Get your token at: https://tushare.pro/register"
        )
    return ts.pro_api(tk)


def fetch_tushare_daily_bars(req: TushareDailyBarsRequest) -> pd.DataFrame:  # pragma: no cover
    """直接调用 TuShare 接口获取日线数据，并按 req.adjust 复权。

    ETF/基金（如 ``510300.SH``）在 ``pro.daily`` 上常为空；此时回退
    ``pro.fund_daily``（计入 ``fund_daily`` 配额，不再拉 adj_factor）。
    """
    pro = _get_tushare_pro(req.token)
    adjust_mode = _normalize_adjust_mode(req.adjust)

    acquire_tushare_call("daily")
    raw = pro.daily(
        ts_code=req.symbol,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    daily = _normalize_tushare_daily(raw)
    if daily.empty:
        # ETF / fund instruments are not on stock daily.
        acquire_tushare_call("fund_daily")
        raw_fund = pro.fund_daily(
            ts_code=req.symbol,
            start_date=req.start_date,
            end_date=req.end_date,
        )
        fund = _normalize_tushare_daily(raw_fund)
        # fund_daily already exposes trade OHLC; treat as final series (no adj).
        return fund

    if adjust_mode == "raw":
        return daily

    acquire_tushare_call("adj_factor")
    raw_adj = pro.adj_factor(
        ts_code=req.symbol,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    adj = _normalize_tushare_adj_factor(raw_adj)
    return _apply_price_adjustment(daily, adj, adjust_mode)


def fetch_tushare_daily_basic(req: TushareDailyBasicRequest) -> pd.DataFrame:  # pragma: no cover
    """直接调用 TuShare daily_basic 接口。"""
    pro = _get_tushare_pro(req.token)
    acquire_tushare_call("daily_basic")
    raw = pro.daily_basic(ts_code=req.symbol, start_date=req.start_date, end_date=req.end_date)
    return _normalize_tushare_table(raw, SUPPORTED_DAILY_BASIC_FIELDS)


def fetch_tushare_moneyflow(req: TushareMoneyflowRequest) -> pd.DataFrame:  # pragma: no cover
    """直接调用 TuShare moneyflow 接口。"""
    pro = _get_tushare_pro(req.token)
    acquire_tushare_call("moneyflow")
    raw = pro.moneyflow(ts_code=req.symbol, start_date=req.start_date, end_date=req.end_date)
    return _normalize_tushare_table(raw, SUPPORTED_MONEYFLOW_FIELDS)


def fetch_tushare_adj_factor(req: TushareAdjFactorRequest) -> pd.DataFrame:  # pragma: no cover
    """直接调用 TuShare adj_factor 接口。"""
    pro = _get_tushare_pro(req.token)
    acquire_tushare_call("adj_factor")
    raw = pro.adj_factor(ts_code=req.symbol, start_date=req.start_date, end_date=req.end_date)
    return _normalize_tushare_adj_factor(raw)


def _normalize_adjust_mode(adjust: str | None) -> str:
    mode = str(adjust or "raw").strip().lower()
    if mode not in ADJUST_MODES:
        raise ValueError(f"unsupported adjust mode: {adjust!r}, expected one of {tuple(ADJUST_MODES)}")
    return mode


def _apply_price_adjustment(daily: pd.DataFrame, adj_factor: pd.DataFrame, adjust: str) -> pd.DataFrame:
    """按 adj_factor 对 OHLC 做前/后复权。"""
    mode = _normalize_adjust_mode(adjust)
    if mode == "raw" or daily.empty:
        return daily

    if adj_factor.empty or "adj_factor" not in adj_factor.columns:
        return daily

    work = daily.join(adj_factor[["adj_factor"]], how="left")
    work["adj_factor"] = pd.to_numeric(work["adj_factor"], errors="coerce")
    if work["adj_factor"].notna().sum() == 0:
        return daily
    work["adj_factor"] = work["adj_factor"].ffill().bfill()
    if work["adj_factor"].notna().sum() == 0:
        return daily

    non_na = work["adj_factor"].dropna()
    base_factor = float(non_na.iloc[-1]) if mode == "qfq" else float(non_na.iloc[0])
    if base_factor == 0:
        return daily

    ratio = work["adj_factor"] / base_factor
    out = daily.copy()
    for col in ("open", "high", "low", "close"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce") * ratio
    return out


def _retry_with_backoff(func, retries: int, base_delay: float = 0.5):
    """Retry transient errors; AO-B4: frequency-wall (2002) is not retried in-loop."""
    last_exc = None
    for attempt in range(retries):
        try:
            return func()
        except Exception as exc:  # pragma: no cover - exercised via tests with mock
            last_exc = exc
            # Do not tight-loop on TuShare frequency walls — surface to batch pause.
            if is_frequency_wall_error(exc):
                raise
            if attempt == retries - 1:
                break
            time.sleep(base_delay * (2**attempt))
    if last_exc:
        raise last_exc
    raise RuntimeError("retry failed without exception")  # pragma: no cover


def _read_cached_partitions(symbol_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if not symbol_dir.exists():
        return pd.DataFrame(columns=SUPPORTED_FIELDS)

    for part_path in symbol_dir.glob("year=*/part.parquet"):
        try:
            df = pd.read_parquet(part_path)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            frames.append(df)
        except FileNotFoundError:
            continue
        except (OSError, ValueError):  # corrupt/truncated part → skip (fail-open read)
            continue
    if not frames:
        return pd.DataFrame(columns=SUPPORTED_FIELDS)
    return pd.concat(frames).sort_index()


def _write_partitioned(df: pd.DataFrame, symbol_dir: Path) -> None:
    symbol_dir.mkdir(parents=True, exist_ok=True)
    if df.empty:
        return
    df_reset = df.reset_index()
    if "date" not in df_reset.columns and "index" in df_reset.columns:
        df_reset = df_reset.rename(columns={"index": "date"})
    df_reset["year"] = df_reset["date"].dt.year
    for year, year_df in df_reset.groupby("year"):
        year_dir = symbol_dir / f"year={year}"
        year_dir.mkdir(parents=True, exist_ok=True)
        out_path = year_dir / "part.parquet"
        tmp_path = year_dir / "part.parquet.tmp"
        year_df.drop(columns=["year"]).to_parquet(tmp_path, index=False)
        tmp_path.replace(out_path)


def _date_ranges_to_fetch(
    existing: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """根据已有数据计算缺失的日期区间"""
    if existing.empty:
        return [(start, end)]

    existing_start, existing_end = existing.index.min(), existing.index.max()
    ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []

    if start < existing_start:
        ranges.append((start, existing_start - timedelta(days=1)))
    if end > existing_end:
        ranges.append((existing_end + timedelta(days=1), end))

    # 简化假设：中间若有缺口则由 refresh 调用覆盖
    return [(s, e) for s, e in ranges if s <= e]


def _slice_result(combined: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """返回请求区间内的数据；空帧直接返回（占位 RangeIndex 无法比较 Timestamp）。"""
    combined.index.name = "date"
    if combined.empty:
        return combined.copy()
    return combined.loc[(combined.index >= start) & (combined.index <= end)].copy()


def load_or_fetch_daily_bars(
    req: TushareDailyBarsRequest,
    cache_dir: Path,
    refresh: bool = False,
    retries: int = 3,
    backoff_base: float = 0.5,
) -> pd.DataFrame:
    """加载或获取 TuShare 日线数据，带分区缓存与增量去重。

    - ``refresh=True`` 强制重取请求区间，但保留区间外已缓存行（合并后整体重写，
      不会把年度分区截成只剩请求区间）。
    - 复权模式（qfq/hfq）下，若需要增量抓取且已有缓存，则改为整段重取：
      增量拼接会让新旧两段使用不同的复权基准，在接缝处产生假跳价。
    """
    adjust_mode = _normalize_adjust_mode(req.adjust)
    cache_ns = "tushare" if adjust_mode == "raw" else f"tushare_{adjust_mode}"
    symbol_dir = cache_dir / cache_ns / req.symbol
    start = pd.to_datetime(req.start_date)
    end = pd.to_datetime(req.end_date)

    existing = _read_cached_partitions(symbol_dir)

    if refresh:
        ranges = [(start, end)] if start <= end else []
    else:
        ranges = _date_ranges_to_fetch(existing, start, end)

    # qfq/hfq：任何需要抓取的情形都整段重取（覆盖旧缓存 span ∪ 请求区间），
    # 保证整个缓存序列共享同一个复权基准。
    # 唯一例外：增量区间完全位于 existing 之前的"前端边缘"（如请求 start=20230101
    # 而缓存从 2023-01-03 起的元旦周末边缘）——前端拼接无复权接缝，且该区间通常
    # 无交易日数据；整段重取会导致每次读取都全量重拉（4.3 审计发现）。
    if ranges and adjust_mode != "raw" and not existing.empty:
        only_leading = all(
            fetch_end < existing.index.min() for fetch_start, fetch_end in ranges
        )
        if not only_leading:
            span_start = min(start, existing.index.min())
            span_end = max(end, existing.index.max())
            ranges = [(span_start, span_end)]
            existing = pd.DataFrame(columns=SUPPORTED_FIELDS)

    fetched_frames: list[pd.DataFrame] = []
    for fetch_start, fetch_end in ranges:
        fetch_req = TushareDailyBarsRequest(
            symbol=req.symbol,
            start_date=fetch_start.strftime("%Y%m%d"),
            end_date=fetch_end.strftime("%Y%m%d"),
            adjust=req.adjust,
            token=req.token,
        )
        fetched = _retry_with_backoff(
            lambda: fetch_tushare_daily_bars(fetch_req),
            retries=retries,
            base_delay=backoff_base,
        )
        fetched_frames.append(fetched)

    combined = existing
    if fetched_frames:
        frames = [df for df in [existing, *fetched_frames] if not df.empty]
        combined = pd.concat(frames).sort_index() if frames else existing
        # fetched 在 existing 之后 → keep="last" 时以新抓取为准
        combined = combined[~combined.index.duplicated(keep="last")]
        _write_partitioned(combined, symbol_dir)

    return _slice_result(combined, start, end)


def load_or_fetch_daily_basic(
    req: TushareDailyBasicRequest,
    cache_dir: Path,
    refresh: bool = False,
    retries: int = 3,
    backoff_base: float = 0.5,
) -> pd.DataFrame:
    """加载或获取 TuShare daily_basic，带分区缓存与增量去重。"""
    symbol_dir = cache_dir / "tushare_daily_basic" / req.symbol
    start = pd.to_datetime(req.start_date)
    end = pd.to_datetime(req.end_date)

    existing = _read_cached_partitions(symbol_dir)
    if refresh:
        ranges = [(start, end)] if start <= end else []
    else:
        ranges = _date_ranges_to_fetch(existing, start, end)

    fetched_frames: list[pd.DataFrame] = []
    for fetch_start, fetch_end in ranges:
        fetch_req = TushareDailyBasicRequest(
            symbol=req.symbol,
            start_date=fetch_start.strftime("%Y%m%d"),
            end_date=fetch_end.strftime("%Y%m%d"),
            token=req.token,
        )
        fetched = _retry_with_backoff(
            lambda: fetch_tushare_daily_basic(fetch_req),
            retries=retries,
            base_delay=backoff_base,
        )
        fetched_frames.append(fetched)

    combined = existing
    if fetched_frames:
        frames = [df for df in [existing, *fetched_frames] if not df.empty]
        combined = pd.concat(frames).sort_index() if frames else existing
        combined = combined[~combined.index.duplicated(keep="last")]
        _write_partitioned(combined, symbol_dir)

    result = _slice_result(combined, start, end)
    return result.reindex(columns=list(SUPPORTED_DAILY_BASIC_FIELDS))


def load_or_fetch_moneyflow(
    req: TushareMoneyflowRequest,
    cache_dir: Path,
    refresh: bool = False,
    retries: int = 3,
    backoff_base: float = 0.5,
) -> pd.DataFrame:
    """加载或获取 TuShare moneyflow，带分区缓存与增量去重。"""
    symbol_dir = cache_dir / "tushare_moneyflow" / req.symbol
    start = pd.to_datetime(req.start_date)
    end = pd.to_datetime(req.end_date)

    existing = _read_cached_partitions(symbol_dir)
    if refresh:
        ranges = [(start, end)] if start <= end else []
    else:
        ranges = _date_ranges_to_fetch(existing, start, end)

    fetched_frames: list[pd.DataFrame] = []
    for fetch_start, fetch_end in ranges:
        fetch_req = TushareMoneyflowRequest(
            symbol=req.symbol,
            start_date=fetch_start.strftime("%Y%m%d"),
            end_date=fetch_end.strftime("%Y%m%d"),
            token=req.token,
        )
        fetched = _retry_with_backoff(
            lambda: fetch_tushare_moneyflow(fetch_req),
            retries=retries,
            base_delay=backoff_base,
        )
        fetched_frames.append(fetched)

    combined = existing
    if fetched_frames:
        frames = [df for df in [existing, *fetched_frames] if not df.empty]
        combined = pd.concat(frames).sort_index() if frames else existing
        combined = combined[~combined.index.duplicated(keep="last")]
        _write_partitioned(combined, symbol_dir)

    result = _slice_result(combined, start, end)
    return result.reindex(columns=list(SUPPORTED_MONEYFLOW_FIELDS))
