from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class AkshareDailyBarsRequest:
    symbol: str
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    adjust: str = "qfq"


def _normalize_akshare_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # akshare stock_zh_a_hist columns:
    # 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, ...
    df = df.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    keep = [c for c in ["open", "high", "low", "close", "volume", "amount"] if c in df.columns]
    df = df[keep].copy()
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def fetch_akshare_daily_bars(req: AkshareDailyBarsRequest) -> pd.DataFrame:
    import akshare as ak  # lazy import

    raw = ak.stock_zh_a_hist(
        symbol=req.symbol,
        period="daily",
        start_date=req.start_date,
        end_date=req.end_date,
        adjust=req.adjust,
    )
    return _normalize_akshare_daily(raw)


def load_or_fetch_daily_bars(
    req: AkshareDailyBarsRequest,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{req.symbol}_daily_{req.adjust}_{req.start_date}_{req.end_date}.csv"

    if cache_path.exists() and not refresh:
        df = pd.read_csv(cache_path, parse_dates=["date"])
        df = df.set_index("date").sort_index()
        return df

    df = fetch_akshare_daily_bars(req)
    if df.empty:
        return df
    df.reset_index().to_csv(cache_path, index=False)
    return df
