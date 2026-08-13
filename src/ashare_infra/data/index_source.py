"""Index daily bars via TuShare ``index_daily`` (single A-share data source).

AkShare 已从项目中移除；指数日线统一走 TuShare ``pro.index_daily``。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class IndexDailyRequest:
    symbol: str  # e.g. 000300 (CSI 300); bare code or ts_code style
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    token: str | None = None  # 可显式传入 token，默认从环境变量读取


_INDEX_FIELDS: tuple[str, ...] = ("open", "high", "low", "close", "volume", "amount")


def _to_index_ts_code(symbol: str) -> str:
    """bare 指数代码 → TuShare ts_code（39 开头为深市，其余默认沪市）。"""
    sym = str(symbol).strip()
    if "." in sym:
        return sym.upper()
    return f"{sym}.{'SZ' if sym.startswith('39') else 'SH'}"


def _normalize_index_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=list(_INDEX_FIELDS))
    df = df.rename(
        columns={
            "trade_date": "date",
            "vol": "volume",
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    keep = [c for c in _INDEX_FIELDS if c in df.columns]
    df = df[keep].copy()
    for col in keep:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def fetch_index_daily(req: IndexDailyRequest) -> pd.DataFrame:
    """调用 TuShare ``index_daily`` 获取指数日线（成交量单位为手，金额为千元）。"""
    import os

    import tushare as ts  # lazy import

    from ashare_infra.data.tushare_rate_limit import acquire_tushare_call

    tk = req.token or os.environ.get("TUSHARE_TOKEN")
    if not tk:
        raise ValueError(
            "TUSHARE_TOKEN not found. Please set it in environment or pass via token parameter.\n"
            "Get your token at: https://tushare.pro/register"
        )
    pro = ts.pro_api(tk)
    acquire_tushare_call("index_daily")
    raw = pro.index_daily(
        ts_code=_to_index_ts_code(req.symbol),
        start_date=req.start_date,
        end_date=req.end_date,
    )
    return _normalize_index_daily(raw)


def load_or_fetch_index_daily(
    req: IndexDailyRequest, cache_dir: Path, refresh: bool = False
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (
        f"index_{_to_index_ts_code(req.symbol)}_daily_{req.start_date}_{req.end_date}.csv"
    )
    if cache_path.exists() and not refresh:
        df = pd.read_csv(cache_path, parse_dates=["date"])
        return df.set_index("date").sort_index()

    df = fetch_index_daily(req)
    if df.empty:
        return df
    df.reset_index().to_csv(cache_path, index=False)
    return df
