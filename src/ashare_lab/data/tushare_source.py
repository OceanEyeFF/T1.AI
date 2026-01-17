from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence
import time

import pandas as pd

# Public constants
SUPPORTED_FIELDS: Sequence[str] = ("open", "high", "low", "close", "volume", "amount")


@dataclass(frozen=True)
class TushareDailyBarsRequest:
    """TuShare 日线请求参数"""

    symbol: str  # ts_code, e.g. 600519.SH
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    adjust: str = "qfq"
    token: str | None = None  # 可显式传入 token，默认从环境变量读取


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


def fetch_tushare_daily_bars(req: TushareDailyBarsRequest) -> pd.DataFrame:  # pragma: no cover
    """直接调用 TuShare 接口获取日线数据（前复权）"""
    import tushare as ts  # lazy import

    # token 优先级：参数 > 环境变量
    if req.token:
        pro = ts.pro_api(req.token)
    else:
        pro = ts.pro_api()

    raw = pro.daily(
        ts_code=req.symbol,
        start_date=req.start_date,
        end_date=req.end_date,
        # TuShare 的 daily 不直接支持 adj，通常配合 adj_factor 使用。
        # 此处保持接口兼容，后续可扩展为价格复权。
    )
    return _normalize_tushare_daily(raw)


def _retry_with_backoff(func, retries: int, base_delay: float = 0.5):
    last_exc = None
    for attempt in range(retries):
        try:
            return func()
        except Exception as exc:  # pragma: no cover - exercised via tests with mock
            last_exc = exc
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
        year_df.drop(columns=["year"]).to_parquet(out_path, index=False)


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


def load_or_fetch_daily_bars(
    req: TushareDailyBarsRequest,
    cache_dir: Path,
    refresh: bool = False,
    retries: int = 3,
    backoff_base: float = 0.5,
) -> pd.DataFrame:
    """加载或获取 TuShare 日线数据，带分区缓存与增量去重"""
    symbol_dir = cache_dir / "tushare" / req.symbol
    start = pd.to_datetime(req.start_date)
    end = pd.to_datetime(req.end_date)

    if refresh:
        existing = pd.DataFrame(columns=SUPPORTED_FIELDS)
    else:
        existing = _read_cached_partitions(symbol_dir)

    ranges = _date_ranges_to_fetch(existing, start, end)

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
        combined = pd.concat([existing, *fetched_frames]).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        _write_partitioned(combined, symbol_dir)

    combined.index.name = "date"

    # 返回请求区间内的数据
    result = combined.loc[(combined.index >= start) & (combined.index <= end)].copy()
    return result
