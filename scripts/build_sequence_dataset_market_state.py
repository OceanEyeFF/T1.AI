#!/usr/bin/env python
"""Build sequence dataset with market state features.

Market state features are calculated cross-sectionally from the selected universe:
  - market_mom_5d: 5-day momentum of equal-weight market return series
  - market_vol_20d: 20-day volatility of equal-weight market return series
  - market_amount_z20: z-score of total market amount over 20-day rolling window
Optional ODP global commodity features (when enabled):
  - odp_cmdty_ret_1d_ew / odp_cmdty_mom_5d_ew / odp_cmdty_vol_20d_ew
  - odp_cmdty_amount_z20_ew / odp_cmdty_cross_disp_20d
Optional TuShare domestic futures commodity features (when enabled):
  - uses same 5 aggregate fields above for compatibility
All market features are shifted by 1 day to avoid look-ahead leakage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_lab.data.akshare_source import AkshareDailyBarsRequest, load_or_fetch_daily_bars
from ashare_lab.data.odp_source import (
    ODPHistoricalRequest,
    load_or_fetch_historical_bars as load_or_fetch_odp_historical_bars,
)
from ashare_lab.data.tushare_source import (
    SUPPORTED_DAILY_BASIC_FIELDS,
    SUPPORTED_MONEYFLOW_FIELDS,
    TushareDailyBarsRequest,
    TushareDailyBasicRequest,
    TushareMoneyflowRequest,
    load_or_fetch_daily_bars as load_tushare_daily_bars,
    load_or_fetch_daily_basic as load_tushare_daily_basic,
    load_or_fetch_moneyflow as load_tushare_moneyflow,
)
from ashare_lab.dataset.sequence_builder import SequenceDatasetBuilder
from ashare_lab.features.momentum import Return1D, Return5D, Return10D, Return20D, Return60D
from ashare_lab.features.price_slope import PriceSlope
from ashare_lab.stock_pool import (
    export_stock_pool_artifacts,
    get_stock_pool_record,
    resolve_stock_pool_symbols,
)
from ashare_lab.features.technical import BollingerDeviation, MACDHist, MACDLine, MACDSignal, RSI
from ashare_lab.features.volume import AmountChange, RelativeVolume, VolumeChange, VolumeRatio
from ashare_lab.labels.multi_horizon import MultiHorizonLabel, OneDayHLCLabel

try:
    from scripts.config_io import dump_json, extract_arg_overrides
    from scripts.runtime_metadata import infer_dataset_id
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config_io import dump_json, extract_arg_overrides
    from runtime_metadata import infer_dataset_id

SYMBOL_FEATURES_16 = [
    Return1D(),
    Return5D(),
    Return10D(),
    Return20D(),
    Return60D(),
    VolumeRatio(window=5),
    RelativeVolume(window=5),
    VolumeChange(),
    AmountChange(),
    RSI(period=14),
    MACDLine(),
    MACDSignal(),
    MACDHist(),
    BollingerDeviation(window=20),
    PriceSlope(window=5),
    PriceSlope(window=20),
]

MARKET_FEATURE_NAMES = ["market_mom_5d", "market_vol_20d", "market_amount_z20"]
ODP_COMMODITY_FEATURE_NAMES = [
    "odp_cmdty_ret_1d_ew",
    "odp_cmdty_mom_5d_ew",
    "odp_cmdty_vol_20d_ew",
    "odp_cmdty_amount_z20_ew",
    "odp_cmdty_cross_disp_20d",
]
TUSHARE_FUT_BARS_FIELDS = ("open", "high", "low", "close", "volume", "amount")
ETF_FEATURE_NAMES = [
    "etf_ret_1d",
    "etf_ret_1d_ma5",
    "etf_ret_1d_ma10",
    "etf_mom_5d",
    "etf_slope_10d",
]
SHORT_TERM_FEATURE_NAMES = [
    "hist_high_5d",
    "hist_low_5d",
    "hist_high_10d",
    "hist_low_10d",
    "turnover_rate",
    "turnover_rate_f",
    "turnover_spread",
    "turnover_rate_z20",
    "turnover_rate_f_z20",
    "turnover_spread_z20",
    "db_volume_ratio",
    "db_volume_ratio_z20",
    "volume_volatility_10d",
    "pe_ttm_z20",
    "pb_z20",
    "ps_ttm_z20",
    "dv_ttm",
    "total_mv_log",
    "circ_mv_log",
    "float_share_ratio",
    "float_share_ratio_z20",
    "mf_net_amount_ratio",
    "mf_net_vol_ratio",
    "mf_net_amount_abs_ratio",
    "mf_sm_amount_ratio",
    "mf_md_amount_ratio",
    "mf_lg_amount_ratio",
    "mf_elg_amount_ratio",
    "mf_sm_vol_ratio",
    "mf_md_vol_ratio",
    "mf_lg_vol_ratio",
    "mf_elg_vol_ratio",
    "mf_buy_pressure_amount",
    "mf_buy_pressure_vol",
    "mf_flow_concentration",
    "mf_net_amount_z20",
    "mf_net_vol_z20",
    "mf_net_amount_impulse",
    "mf_net_vol_impulse",
    "mf_large_amount_ratio",
    "mf_retail_amount_ratio",
    "mf_large_retail_spread",
    "mf_net_amount_ratio_ma5",
    "mf_net_amount_ratio_ma10",
    "mf_net_amount_ratio_mom5",
    "mf_net_amount_ratio_mom10",
    "mf_large_amount_ratio_ma5",
    "mf_large_amount_ratio_mom5",
    "mf_retail_amount_ratio_ma5",
    "mf_buy_pressure_amount_ma5",
    "mf_activity_ratio_5d",
    "mf_activity_ratio_20d",
]
HIST_HIGH_LOW_FEATURES = {
    "hist_high_5d",
    "hist_low_5d",
    "hist_high_10d",
    "hist_low_10d",
}
COMPACT44_DROP_FEATURES = {
    "relative_volume",
    "volume_change",
    "turnover_rate_f_z20",
    "turnover_spread_z20",
    "mf_net_vol_ratio",
    "mf_sm_amount_ratio",
    "mf_sm_vol_ratio",
    "mf_md_vol_ratio",
    "mf_lg_vol_ratio",
    "mf_elg_vol_ratio",
    "mf_net_vol_z20",
    "mf_net_vol_impulse",
    "mf_activity_ratio_5d",
    "float_share_ratio_z20",
}
NO_HIST_HL_DROP_FEATURES = COMPACT44_DROP_FEATURES | HIST_HIGH_LOW_FEATURES
PROFILE_DROP_FEATURES: dict[str, set[str]] = {
    "compact44": COMPACT44_DROP_FEATURES,
    "full58": set(),
    "no_hist_hl": NO_HIST_HL_DROP_FEATURES,
}
FEATURE_PROFILES = tuple(PROFILE_DROP_FEATURES.keys())
CONFIG_SECTION_NAME = "build_sequence_dataset_market_state"
# No default symbols CSV — use --stock-pool-id to specify a pool instead
DEFAULT_SYMBOLS_CSV = None


def _parse_symbols(path: Path) -> list[str]:
    df = pd.read_csv(path, dtype=str)
    if "symbol" not in df.columns:
        raise ValueError(f"{path} must contain a `symbol` column")
    syms = [str(s).strip().zfill(6) for s in df["symbol"].dropna().tolist() if str(s).strip()]
    out = sorted(set(syms))
    if not out:
        raise ValueError(f"no symbols parsed from {path}")
    return out


def _resolve_symbols_input(
    *,
    symbols_csv: str | None,
    stock_pool_id: str,
    stock_pool_version: str,
    stock_pool_registry_dir: str,
    stock_pool_export_dir: str,
) -> tuple[list[str], dict[str, str]]:
    symbols_csv_text = str(symbols_csv or "").strip()
    if str(stock_pool_id).strip():
        if symbols_csv_text and Path(symbols_csv_text) != Path(DEFAULT_SYMBOLS_CSV):
            raise ValueError("use either stock_pool_id or symbols_csv, not both")
        record = get_stock_pool_record(
            stock_pool_registry_dir,
            stock_pool_id=str(stock_pool_id).strip(),
            stock_pool_version=(str(stock_pool_version).strip() or None),
        )
        artifacts = export_stock_pool_artifacts(
            record,
            output_dir=stock_pool_export_dir,
            registry_root=Path(stock_pool_registry_dir),
        )
        resolved_symbols = resolve_stock_pool_symbols(
            record, registry_root=Path(stock_pool_registry_dir)
        )
        return resolved_symbols, {
            "stock_pool_id": record.stock_pool_id,
            "stock_pool_version": record.stock_pool_version,
            "symbols_csv": str(artifacts["symbols_csv"]),
            "registry_path": record.registry_path,
        }

    resolved_symbols = _parse_symbols(Path(symbols_csv_text or DEFAULT_SYMBOLS_CSV))
    return resolved_symbols, {
        "stock_pool_id": "",
        "stock_pool_version": "",
        "symbols_csv": str(symbols_csv_text or DEFAULT_SYMBOLS_CSV),
        "registry_path": "",
    }


def _to_ts_code(symbol: str) -> str:
    return f"{symbol}.SH" if symbol[:2] in {"60", "68", "90", "93"} else f"{symbol}.SZ"


def _to_etf_ts_code(code_or_ts: str) -> str:
    raw = str(code_or_ts).strip().upper()
    if not raw:
        raise ValueError("empty etf code")
    if "." in raw:
        return raw

    code = raw.zfill(6)
    if code[:2] in {"15", "16", "18"}:
        return f"{code}.SZ"
    return f"{code}.SH"


def _load_tushare_cache_only(
    ts_code: str,
    start: str,
    end: str,
    cache_dir: Path,
    dataset_name: str,
    columns: list[str],
) -> pd.DataFrame:
    symbol_dir = cache_dir / dataset_name / ts_code
    if not symbol_dir.exists():
        return pd.DataFrame(index=pd.DatetimeIndex([], name="date"), columns=columns)

    frames: list[pd.DataFrame] = []
    for part in symbol_dir.glob("year=*/part.parquet"):
        df = pd.read_parquet(part)
        if "date" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        keep = [c for c in columns if c in df.columns]
        frames.append(df[keep])

    if not frames:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="date"), columns=columns)

    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "date"

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)
    return out.loc[(out.index >= start_ts) & (out.index <= end_ts)].copy().reindex(columns=columns)


def _normalize_tushare_fund_daily(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["open", "high", "low", "close", "volume", "amount"]
    if df is None or df.empty:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="date"), columns=cols)

    work = df.rename(columns={"trade_date": "date", "vol": "volume"}).copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date"]).set_index("date").sort_index()
    out = work.reindex(columns=cols).copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out.index.name = "date"
    return out


def _write_partitioned(df: pd.DataFrame, symbol_dir: Path) -> None:
    symbol_dir.mkdir(parents=True, exist_ok=True)
    if df.empty:
        return

    out = df.copy().reset_index()
    if "date" not in out.columns and "index" in out.columns:
        out = out.rename(columns={"index": "date"})
    out["year"] = pd.to_datetime(out["date"]).dt.year
    for year, part in out.groupby("year"):
        year_dir = symbol_dir / f"year={year}"
        year_dir.mkdir(parents=True, exist_ok=True)
        part.drop(columns=["year"]).to_parquet(year_dir / "part.parquet", index=False)


def _fetch_tushare_fund_daily(
    ts_code: str, start: str, end: str, token: str | None = None
) -> pd.DataFrame:
    import tushare as ts  # lazy import

    tk = token or os.environ.get("TUSHARE_TOKEN")
    if not tk:
        raise ValueError("TUSHARE_TOKEN not found for ETF fund_daily fetch")
    pro = ts.pro_api(tk)
    raw = pro.fund_daily(ts_code=ts_code, start_date=start, end_date=end)
    return _normalize_tushare_fund_daily(raw)


def _load_tushare_fund_daily_cache_or_live(
    ts_code: str,
    start: str,
    end: str,
    cache_dir: Path,
    source: str,
    retries: int = 3,
) -> pd.DataFrame:
    cols = ["open", "high", "low", "close", "volume", "amount"]
    if source == "akshare":
        return pd.DataFrame(index=pd.DatetimeIndex([], name="date"), columns=cols)

    cache_ds = "tushare_fund_daily"
    cached = _load_tushare_cache_only(
        ts_code=ts_code,
        start=start,
        end=end,
        cache_dir=cache_dir,
        dataset_name=cache_ds,
        columns=cols,
    )
    if source == "tushare_cache":
        return cached

    need_fetch = (
        cached.empty
        or cached.index.min() > pd.to_datetime(start)
        or cached.index.max() < pd.to_datetime(end)
    )
    if not need_fetch:
        return cached

    last_err: Exception | None = None
    fetched = pd.DataFrame(index=pd.DatetimeIndex([], name="date"), columns=cols)
    for i in range(retries):
        try:
            fetched = _fetch_tushare_fund_daily(ts_code=ts_code, start=start, end=end)
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.0 + float(i))
    if fetched.empty and last_err is not None:
        print(
            f"[warn] ETF {ts_code} fund_daily fetch failed: {type(last_err).__name__}: {last_err}"
        )

    frames = [df for df in [cached, fetched] if not df.empty]
    merged = pd.concat(frames).sort_index() if frames else cached.copy()
    merged = merged[~merged.index.duplicated(keep="last")]
    merged.index.name = "date"
    _write_partitioned(merged, cache_dir / cache_ds / ts_code)
    return merged.loc[
        (merged.index >= pd.to_datetime(start)) & (merged.index <= pd.to_datetime(end))
    ].copy()


def _parse_sector_etf_map(path: Path, symbols: list[str]) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"sector etf map not found: {path}")

    df = pd.read_csv(path, dtype=str)
    if "symbol" not in df.columns:
        raise ValueError(f"{path} must contain `symbol` column")
    etf_col = (
        "etf_ts_code"
        if "etf_ts_code" in df.columns
        else "etf_symbol"
        if "etf_symbol" in df.columns
        else None
    )
    if etf_col is None:
        raise ValueError(f"{path} must contain `etf_ts_code` or `etf_symbol` column")

    sym_set = set(symbols)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        s = str(row.get("symbol", "")).strip().zfill(6)
        if not s or s not in sym_set:
            continue
        etf_raw = str(row.get(etf_col, "")).strip()
        if not etf_raw:
            continue
        out[s] = _to_etf_ts_code(etf_raw)
    return out


def _load_akshare(
    symbol: str, start: str, end: str, cache_dir: Path, retries: int = 3
) -> pd.DataFrame:
    req = AkshareDailyBarsRequest(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
    last_err: Exception | None = None
    for i in range(retries):
        try:
            return load_or_fetch_daily_bars(req, cache_dir / "akshare")
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait_s = 1.0 + float(i)
            print(
                f"[warn] {symbol} akshare attempt={i + 1}/{retries} failed: {type(e).__name__}: {e}; sleep={wait_s}s"
            )
            time.sleep(wait_s)
    if last_err is not None:
        print(f"[warn] {symbol} akshare all retries failed: {type(last_err).__name__}: {last_err}")
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])


def _parse_symbol_list(raw: str) -> list[str]:
    out = [str(x).strip() for x in str(raw).split(",") if str(x).strip()]
    return sorted(dict.fromkeys(out))


def _load_tushare_live(symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    ts_code = _to_ts_code(symbol)
    bars_req = TushareDailyBarsRequest(symbol=ts_code, start_date=start, end_date=end, adjust="qfq")
    basic_req = TushareDailyBasicRequest(symbol=ts_code, start_date=start, end_date=end)
    moneyflow_req = TushareMoneyflowRequest(symbol=ts_code, start_date=start, end_date=end)

    bars = load_tushare_daily_bars(bars_req, cache_dir, refresh=False, retries=5, backoff_base=1.0)
    basic = load_tushare_daily_basic(
        basic_req, cache_dir, refresh=False, retries=5, backoff_base=1.0
    )
    moneyflow = load_tushare_moneyflow(
        moneyflow_req,
        cache_dir,
        refresh=False,
        retries=5,
        backoff_base=1.0,
    )
    return bars.join(basic, how="left").join(moneyflow, how="left")


def _load_tushare_cache_with_extras(
    symbol: str, start: str, end: str, cache_dir: Path
) -> pd.DataFrame:
    ts_code = _to_ts_code(symbol)
    bars = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])
    for dataset_name in ("tushare_qfq", "tushare", "tushare_hfq", "tushare_raw"):
        bars = _load_tushare_cache_only(
            ts_code=ts_code,
            start=start,
            end=end,
            cache_dir=cache_dir,
            dataset_name=dataset_name,
            columns=["open", "high", "low", "close", "volume", "amount"],
        )
        if not bars.empty:
            break
    daily_basic = _load_tushare_cache_only(
        ts_code=ts_code,
        start=start,
        end=end,
        cache_dir=cache_dir,
        dataset_name="tushare_daily_basic",
        columns=list(SUPPORTED_DAILY_BASIC_FIELDS),
    )
    moneyflow = _load_tushare_cache_only(
        ts_code=ts_code,
        start=start,
        end=end,
        cache_dir=cache_dir,
        dataset_name="tushare_moneyflow",
        columns=list(SUPPORTED_MONEYFLOW_FIELDS),
    )
    return bars.join(daily_basic, how="left").join(moneyflow, how="left")


def _load_bars(source: str, symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    if source == "tushare_cache":
        return _load_tushare_cache_with_extras(symbol, start, end, cache_dir)
    if source == "tushare_live":
        return _load_tushare_live(symbol, start, end, cache_dir)
    if source == "akshare":
        return _load_akshare(symbol, start, end, cache_dir)
    raise ValueError(f"unsupported source: {source}")


def _num_col(data: pd.DataFrame, col: str) -> pd.Series:
    if col not in data.columns:
        return pd.Series(np.nan, index=data.index, dtype=float)
    return pd.to_numeric(data[col], errors="coerce")


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    den_safe = pd.to_numeric(den, errors="coerce").replace(0.0, np.nan)
    return pd.to_numeric(num, errors="coerce") / den_safe


def _rolling_zscore(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    mean = s.rolling(window=window, min_periods=min_periods).mean()
    std = s.rolling(window=window, min_periods=min_periods).std().replace(0.0, np.nan)
    return (s - mean) / std


def _compute_short_term_features(data: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=data.index)

    close = _num_col(data, "close")
    high = _num_col(data, "high")
    low = _num_col(data, "low")
    volume = _num_col(data, "volume")
    turnover_rate = _num_col(data, "turnover_rate")
    turnover_rate_f = _num_col(data, "turnover_rate_f")
    turnover_spread = turnover_rate_f - turnover_rate
    db_volume_ratio = _num_col(data, "volume_ratio")
    pe_ttm = _num_col(data, "pe_ttm")
    pb = _num_col(data, "pb")
    ps_ttm = _num_col(data, "ps_ttm")
    dv_ttm = _num_col(data, "dv_ttm")
    total_mv = _num_col(data, "total_mv")
    circ_mv = _num_col(data, "circ_mv")
    float_share_ratio = _safe_div(circ_mv, total_mv)

    # 历史高低价做归一化：相对同日收盘价的偏离，再整体 shift(1) 避免前视。
    hist_high_5d = high.rolling(window=5, min_periods=5).max()
    hist_low_5d = low.rolling(window=5, min_periods=5).min()
    hist_high_10d = high.rolling(window=10, min_periods=10).max()
    hist_low_10d = low.rolling(window=10, min_periods=10).min()
    out["hist_high_5d"] = _safe_div(hist_high_5d - close, close).shift(1)
    out["hist_low_5d"] = _safe_div(hist_low_5d - close, close).shift(1)
    out["hist_high_10d"] = _safe_div(hist_high_10d - close, close).shift(1)
    out["hist_low_10d"] = _safe_div(hist_low_10d - close, close).shift(1)
    out["turnover_rate"] = turnover_rate.shift(1)
    out["turnover_rate_f"] = turnover_rate_f.shift(1)
    out["turnover_spread"] = turnover_spread.shift(1)
    out["turnover_rate_z20"] = _rolling_zscore(turnover_rate, window=20, min_periods=10).shift(1)
    out["turnover_rate_f_z20"] = _rolling_zscore(turnover_rate_f, window=20, min_periods=10).shift(
        1
    )
    out["turnover_spread_z20"] = _rolling_zscore(turnover_spread, window=20, min_periods=10).shift(
        1
    )
    out["db_volume_ratio"] = db_volume_ratio.shift(1)
    out["db_volume_ratio_z20"] = _rolling_zscore(db_volume_ratio, window=20, min_periods=10).shift(
        1
    )
    out["volume_volatility_10d"] = (
        volume.pct_change(fill_method=None).rolling(window=10, min_periods=5).std().shift(1)
    )
    out["pe_ttm_z20"] = _rolling_zscore(pe_ttm, window=20, min_periods=10).shift(1)
    out["pb_z20"] = _rolling_zscore(pb, window=20, min_periods=10).shift(1)
    out["ps_ttm_z20"] = _rolling_zscore(ps_ttm, window=20, min_periods=10).shift(1)
    out["dv_ttm"] = dv_ttm.shift(1)
    out["total_mv_log"] = np.log1p(total_mv.clip(lower=0.0)).shift(1)
    out["circ_mv_log"] = np.log1p(circ_mv.clip(lower=0.0)).shift(1)
    out["float_share_ratio"] = float_share_ratio.shift(1)
    out["float_share_ratio_z20"] = _rolling_zscore(
        float_share_ratio, window=20, min_periods=10
    ).shift(1)

    buy_sm_amount = _num_col(data, "buy_sm_amount")
    buy_md_amount = _num_col(data, "buy_md_amount")
    buy_lg_amount = _num_col(data, "buy_lg_amount")
    buy_elg_amount = _num_col(data, "buy_elg_amount")
    sell_sm_amount = _num_col(data, "sell_sm_amount")
    sell_md_amount = _num_col(data, "sell_md_amount")
    sell_lg_amount = _num_col(data, "sell_lg_amount")
    sell_elg_amount = _num_col(data, "sell_elg_amount")
    buy_sm_vol = _num_col(data, "buy_sm_vol")
    buy_md_vol = _num_col(data, "buy_md_vol")
    buy_lg_vol = _num_col(data, "buy_lg_vol")
    buy_elg_vol = _num_col(data, "buy_elg_vol")
    sell_sm_vol = _num_col(data, "sell_sm_vol")
    sell_md_vol = _num_col(data, "sell_md_vol")
    sell_lg_vol = _num_col(data, "sell_lg_vol")
    sell_elg_vol = _num_col(data, "sell_elg_vol")

    net_amount = _num_col(data, "net_mf_amount")
    net_vol = _num_col(data, "net_mf_vol")

    buy_amount_total = buy_sm_amount + buy_md_amount + buy_lg_amount + buy_elg_amount
    sell_amount_total = sell_sm_amount + sell_md_amount + sell_lg_amount + sell_elg_amount
    buy_vol_total = buy_sm_vol + buy_md_vol + buy_lg_vol + buy_elg_vol
    sell_vol_total = sell_sm_vol + sell_md_vol + sell_lg_vol + sell_elg_vol

    total_amount = (buy_amount_total + sell_amount_total).replace(0.0, np.nan)
    total_vol = (buy_vol_total + sell_vol_total).replace(0.0, np.nan)

    net_sm_amount = buy_sm_amount - sell_sm_amount
    net_md_amount = buy_md_amount - sell_md_amount
    net_lg_amount = buy_lg_amount - sell_lg_amount
    net_elg_amount = buy_elg_amount - sell_elg_amount
    net_sm_vol = buy_sm_vol - sell_sm_vol
    net_md_vol = buy_md_vol - sell_md_vol
    net_lg_vol = buy_lg_vol - sell_lg_vol
    net_elg_vol = buy_elg_vol - sell_elg_vol

    net_amount_ratio = _safe_div(net_amount, total_amount)
    out["mf_net_amount_ratio"] = net_amount_ratio.shift(1)
    out["mf_net_vol_ratio"] = _safe_div(net_vol, total_vol).shift(1)
    out["mf_net_amount_abs_ratio"] = _safe_div(net_amount.abs(), total_amount).shift(1)
    out["mf_sm_amount_ratio"] = _safe_div(net_sm_amount, total_amount).shift(1)
    out["mf_md_amount_ratio"] = _safe_div(net_md_amount, total_amount).shift(1)
    out["mf_lg_amount_ratio"] = _safe_div(net_lg_amount, total_amount).shift(1)
    out["mf_elg_amount_ratio"] = _safe_div(net_elg_amount, total_amount).shift(1)
    out["mf_sm_vol_ratio"] = _safe_div(net_sm_vol, total_vol).shift(1)
    out["mf_md_vol_ratio"] = _safe_div(net_md_vol, total_vol).shift(1)
    out["mf_lg_vol_ratio"] = _safe_div(net_lg_vol, total_vol).shift(1)
    out["mf_elg_vol_ratio"] = _safe_div(net_elg_vol, total_vol).shift(1)
    buy_pressure_amount = _safe_div(buy_amount_total, total_amount)
    out["mf_buy_pressure_amount"] = buy_pressure_amount.shift(1)
    out["mf_buy_pressure_vol"] = _safe_div(buy_vol_total, total_vol).shift(1)

    net_abs_sum_amount = (
        net_sm_amount.abs() + net_md_amount.abs() + net_lg_amount.abs() + net_elg_amount.abs()
    ).replace(
        0.0,
        np.nan,
    )
    out["mf_flow_concentration"] = _safe_div(
        net_lg_amount.abs() + net_elg_amount.abs(), net_abs_sum_amount
    ).shift(1)
    out["mf_net_amount_z20"] = _rolling_zscore(net_amount, window=20, min_periods=10).shift(1)
    out["mf_net_vol_z20"] = _rolling_zscore(net_vol, window=20, min_periods=10).shift(1)

    net_amount_abs_scale = net_amount.abs().rolling(20, min_periods=10).mean().replace(0.0, np.nan)
    net_vol_abs_scale = net_vol.abs().rolling(20, min_periods=10).mean().replace(0.0, np.nan)
    out["mf_net_amount_impulse"] = _safe_div(net_amount.diff(1), net_amount_abs_scale).shift(1)
    out["mf_net_vol_impulse"] = _safe_div(net_vol.diff(1), net_vol_abs_scale).shift(1)

    large_net_amount = net_lg_amount + net_elg_amount
    retail_net_amount = net_sm_amount
    large_amount_ratio = _safe_div(large_net_amount, total_amount)
    retail_amount_ratio = _safe_div(retail_net_amount, total_amount)
    out["mf_large_amount_ratio"] = large_amount_ratio.shift(1)
    out["mf_retail_amount_ratio"] = retail_amount_ratio.shift(1)
    out["mf_large_retail_spread"] = _safe_div(
        large_net_amount - retail_net_amount, total_amount
    ).shift(1)

    out["mf_net_amount_ratio_ma5"] = (
        net_amount_ratio.rolling(window=5, min_periods=3).mean().shift(1)
    )
    out["mf_net_amount_ratio_ma10"] = (
        net_amount_ratio.rolling(window=10, min_periods=5).mean().shift(1)
    )
    out["mf_net_amount_ratio_mom5"] = net_amount_ratio.diff(5).shift(1)
    out["mf_net_amount_ratio_mom10"] = net_amount_ratio.diff(10).shift(1)
    out["mf_large_amount_ratio_ma5"] = (
        large_amount_ratio.rolling(window=5, min_periods=3).mean().shift(1)
    )
    out["mf_large_amount_ratio_mom5"] = large_amount_ratio.diff(5).shift(1)
    out["mf_retail_amount_ratio_ma5"] = (
        retail_amount_ratio.rolling(window=5, min_periods=3).mean().shift(1)
    )
    out["mf_buy_pressure_amount_ma5"] = (
        buy_pressure_amount.rolling(window=5, min_periods=3).mean().shift(1)
    )

    out["mf_activity_ratio_5d"] = _safe_div(
        total_amount, total_amount.rolling(5, min_periods=3).mean()
    ).shift(1)
    out["mf_activity_ratio_20d"] = _safe_div(
        total_amount, total_amount.rolling(20, min_periods=10).mean()
    ).shift(1)
    return out


def _compute_etf_features(data: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=data.index)
    close = _num_col(data, "close")

    ret_1d = close.pct_change(1, fill_method=None)
    out["etf_ret_1d"] = ret_1d.shift(1)
    out["etf_ret_1d_ma5"] = ret_1d.rolling(window=5, min_periods=3).mean().shift(1)
    out["etf_ret_1d_ma10"] = ret_1d.rolling(window=10, min_periods=5).mean().shift(1)
    out["etf_mom_5d"] = close.pct_change(5, fill_method=None).shift(1)
    out["etf_slope_10d"] = PriceSlope(window=10).compute(
        pd.DataFrame({"close": close}, index=data.index)
    )
    return out


def _drop_all_nan_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in df.columns if df[c].notna().any()]
    if not keep:
        return pd.DataFrame(index=df.index)
    return df[keep].copy()


def _compute_symbol_features(
    bars: pd.DataFrame,
    include_short_term_features: bool,
    feature_profile: str,
    etf_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    feat: dict[str, pd.Series] = {}
    for f in SYMBOL_FEATURES_16:
        feat[f.name] = f.compute(bars)
    out = pd.DataFrame(feat, index=bars.index)

    drop_features = PROFILE_DROP_FEATURES.get(feature_profile, set())
    has_short_term_inputs = any(
        c in bars.columns and pd.to_numeric(bars[c], errors="coerce").notna().any()
        for c in [
            "turnover_rate",
            "turnover_rate_f",
            "buy_sm_amount",
            "sell_sm_amount",
            "net_mf_amount",
        ]
    )
    if include_short_term_features and has_short_term_inputs:
        short_df = _drop_all_nan_columns(_compute_short_term_features(bars))
        if drop_features and not short_df.empty:
            keep_cols = [c for c in short_df.columns if c not in drop_features]
            short_df = short_df[keep_cols].copy()
        if not short_df.empty:
            out = out.join(short_df, how="left")
    if etf_features is not None and not etf_features.empty:
        out = out.join(etf_features, how="left")
    if drop_features:
        keep_cols = [c for c in out.columns if c not in drop_features]
        out = out[keep_cols].copy()
    return out


def _compute_market_state_features(all_bars: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for symbol, bars in all_bars.items():
        if bars.empty:
            continue
        tmp = pd.DataFrame(index=bars.index.copy())
        tmp["symbol"] = symbol
        tmp["ret1d"] = bars["close"].pct_change(1, fill_method=None)
        tmp["amount"] = pd.to_numeric(bars["amount"], errors="coerce")
        rows.append(tmp.reset_index())

    if not rows:
        raise RuntimeError("no bars loaded; cannot build market state features")

    all_df = pd.concat(rows, ignore_index=True)
    all_df["date"] = pd.to_datetime(all_df["date"])
    all_df = all_df.sort_values(["date", "symbol"])

    by_date = all_df.groupby("date", sort=True)
    market = pd.DataFrame(index=sorted(all_df["date"].unique()))
    market.index = pd.to_datetime(market.index)
    market.index.name = "date"
    market["mkt_ret1d"] = by_date["ret1d"].mean()
    market["mkt_amount_total"] = by_date["amount"].sum()

    mom5 = (
        (1.0 + market["mkt_ret1d"]).rolling(window=5, min_periods=5).apply(np.prod, raw=True) - 1.0
    ).shift(1)
    vol20 = market["mkt_ret1d"].rolling(window=20, min_periods=20).std().shift(1)
    amt_mean20 = market["mkt_amount_total"].rolling(window=20, min_periods=20).mean()
    amt_std20 = market["mkt_amount_total"].rolling(window=20, min_periods=20).std()
    amt_z20 = ((market["mkt_amount_total"] - amt_mean20) / amt_std20).shift(1)

    out = pd.DataFrame(
        {
            "market_mom_5d": mom5,
            "market_vol_20d": vol20,
            "market_amount_z20": amt_z20,
        },
        index=market.index,
    )
    return out


def _load_odp_commodity_bars(
    symbols: list[str],
    *,
    start: str,
    end: str,
    cache_dir: Path,
    provider: str,
    base_url: str | None,
    prefer_rest: bool,
    request_interval_seconds: float,
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for idx, symbol in enumerate(symbols):
        req = ODPHistoricalRequest(
            endpoint="derivatives/futures/historical",
            symbol=symbol,
            start_date=start,
            end_date=end,
            provider=provider,
            interval="1d",
            base_url=base_url,
            prefer_rest=prefer_rest,
        )
        try:
            bars = load_or_fetch_odp_historical_bars(req, cache_dir=cache_dir, refresh=False)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] ODP commodity {symbol} fetch error: {type(e).__name__}: {e}")
            bars = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])

        if not bars.empty:
            out[symbol] = bars
        else:
            print(f"[warn] ODP commodity {symbol} has no data")

        if idx < len(symbols) - 1 and request_interval_seconds > 0:
            time.sleep(float(request_interval_seconds))
    return out


def _normalize_tushare_fut_daily(raw: pd.DataFrame | None) -> pd.DataFrame:
    cols = ["date", "ts_code", "open", "high", "low", "close", "volume", "amount"]
    if raw is None or raw.empty:
        return pd.DataFrame(columns=cols)

    work = raw.rename(columns={"trade_date": "date", "vol": "volume"}).copy()
    if "date" not in work.columns or "ts_code" not in work.columns:
        return pd.DataFrame(columns=cols)

    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["ts_code"] = work["ts_code"].astype(str).str.upper().str.strip()
    work = work.dropna(subset=["date"])
    work = work[work["ts_code"] != ""]

    for c in ("open", "high", "low", "close", "volume", "amount"):
        if c in work.columns:
            work[c] = pd.to_numeric(work[c], errors="coerce")
        else:
            work[c] = np.nan

    out = work[cols].sort_values(["date", "ts_code"]).reset_index(drop=True)
    return out


def _fetch_tushare_fut_daily_by_exchange(
    *,
    exchange: str,
    start: str,
    end: str,
    page_limit: int,
    max_pages: int,
    page_sleep_seconds: float,
    token: str | None = None,
) -> pd.DataFrame:
    import tushare as ts  # lazy import

    tk = token or os.environ.get("TUSHARE_TOKEN")
    if not tk:
        raise ValueError("TUSHARE_TOKEN not found for tushare_fut commodity fetch")

    pro = ts.pro_api(tk)
    frames: list[pd.DataFrame] = []
    offset = 0
    fields = "ts_code,trade_date,open,high,low,close,vol,amount,oi"
    for _ in range(max_pages):
        raw = None
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                raw = pro.fut_daily(
                    exchange=exchange,
                    start_date=start,
                    end_date=end,
                    offset=offset,
                    limit=page_limit,
                    fields=fields,
                )
                last_err = None
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                backoff = max(float(page_sleep_seconds), 0.2) * float(attempt + 1)
                time.sleep(backoff)
        if raw is None:
            if frames:
                print(
                    f"[warn] TuShare futures {exchange} pagination stopped at offset={offset}: "
                    f"{type(last_err).__name__}: {last_err}"
                )
                break
            if last_err is not None:
                raise last_err
            break

        page = _normalize_tushare_fut_daily(raw)
        if page.empty:
            break
        frames.append(page)
        if len(page) < page_limit:
            break
        offset += page_limit
        if page_sleep_seconds > 0:
            time.sleep(float(page_sleep_seconds))

    if not frames:
        return pd.DataFrame(columns=["date", "ts_code", *TUSHARE_FUT_BARS_FIELDS])

    out = pd.concat(frames, ignore_index=True)
    out = (
        out.sort_values(["date", "ts_code"])
        .drop_duplicates(subset=["date", "ts_code"], keep="last")
        .reset_index(drop=True)
    )
    return out


def _ts_code_symbol_part(ts_code: str) -> str:
    return str(ts_code).split(".", 1)[0].strip().upper()


def _is_main_like_tushare_fut_code(ts_code: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]+", _ts_code_symbol_part(ts_code)))


def _build_tushare_fut_bars_map(
    fut_df: pd.DataFrame,
    *,
    symbol_filters: set[str] | None = None,
    main_only: bool = True,
) -> dict[str, pd.DataFrame]:
    if fut_df is None or fut_df.empty:
        return {}

    work = fut_df.copy()
    work["ts_code"] = work["ts_code"].astype(str).str.upper().str.strip()
    work["symbol_part"] = work["ts_code"].map(_ts_code_symbol_part)
    if main_only:
        work = work[work["ts_code"].map(_is_main_like_tushare_fut_code)]

    filt = {str(x).strip().upper() for x in (symbol_filters or set()) if str(x).strip()}
    if filt:
        work = work[(work["ts_code"].isin(filt)) | (work["symbol_part"].isin(filt))]

    out: dict[str, pd.DataFrame] = {}
    if work.empty:
        return out

    for ts_code, g in work.groupby("ts_code", sort=True):
        bars = g[["date", *TUSHARE_FUT_BARS_FIELDS]].copy()
        bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
        bars = bars.dropna(subset=["date"]).set_index("date").sort_index()
        bars = bars[~bars.index.duplicated(keep="last")]
        bars.index.name = "date"
        if bars.empty:
            continue
        out[ts_code] = bars
    return out


def _load_tushare_commodity_bars(
    *,
    start: str,
    end: str,
    exchanges: list[str],
    symbols: list[str],
    main_only: bool,
    page_limit: int,
    max_pages: int,
    page_sleep_seconds: float,
    request_interval_seconds: float,
) -> dict[str, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for idx, exchange in enumerate(exchanges):
        try:
            ex_df = _fetch_tushare_fut_daily_by_exchange(
                exchange=str(exchange).upper(),
                start=start,
                end=end,
                page_limit=int(page_limit),
                max_pages=int(max_pages),
                page_sleep_seconds=float(page_sleep_seconds),
            )
        except Exception as e:  # noqa: BLE001
            print(f"[warn] TuShare futures {exchange} fetch error: {type(e).__name__}: {e}")
            ex_df = pd.DataFrame(columns=["date", "ts_code", *TUSHARE_FUT_BARS_FIELDS])

        if not ex_df.empty:
            frames.append(ex_df)
        else:
            print(f"[warn] TuShare futures {exchange} has no data")

        if idx < len(exchanges) - 1 and request_interval_seconds > 0:
            time.sleep(float(request_interval_seconds))

    if not frames:
        return {}

    all_df = pd.concat(frames, ignore_index=True)
    all_df = (
        all_df.sort_values(["date", "ts_code"])
        .drop_duplicates(subset=["date", "ts_code"], keep="last")
        .reset_index(drop=True)
    )
    out = _build_tushare_fut_bars_map(
        all_df,
        symbol_filters=set(symbols),
        main_only=bool(main_only),
    )
    if symbols:
        requested = {str(x).strip().upper() for x in symbols if str(x).strip()}
        got_codes = set(out.keys())
        got_symbols = {_ts_code_symbol_part(code) for code in got_codes}
        missing = sorted([s for s in requested if s not in got_codes and s not in got_symbols])
        if missing:
            print(f"[warn] TuShare futures requested symbols missing: {missing}")
    return out


def _compute_commodity_features(commodity_bars: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for symbol, bars in commodity_bars.items():
        if bars is None or bars.empty:
            continue
        close = _num_col(bars, "close")
        volume = _num_col(bars, "volume")
        amount = _num_col(bars, "amount")
        amount_proxy = amount.copy()
        if amount_proxy.notna().sum() == 0:
            amount_proxy = close * volume

        ret1d = close.pct_change(1, fill_method=None)
        mom5 = close.pct_change(5, fill_method=None)
        vol20 = ret1d.rolling(window=20, min_periods=10).std()

        tmp = pd.DataFrame(index=bars.index.copy())
        tmp["symbol"] = symbol
        tmp["ret1d"] = ret1d
        tmp["mom5"] = mom5
        tmp["vol20"] = vol20
        tmp["amount_proxy"] = amount_proxy
        rows.append(tmp.reset_index())

    if not rows:
        return pd.DataFrame(
            index=pd.DatetimeIndex([], name="date"), columns=ODP_COMMODITY_FEATURE_NAMES
        )

    all_df = pd.concat(rows, ignore_index=True)
    all_df["date"] = pd.to_datetime(all_df["date"])
    all_df = all_df.sort_values(["date", "symbol"])

    by_date = all_df.groupby("date", sort=True)
    agg = pd.DataFrame(index=sorted(all_df["date"].unique()))
    agg.index = pd.to_datetime(agg.index)
    agg.index.name = "date"

    agg["ret1d_ew"] = by_date["ret1d"].mean()
    agg["mom5_ew"] = by_date["mom5"].mean()
    agg["vol20_ew"] = by_date["vol20"].mean()
    agg["amount_ew"] = by_date["amount_proxy"].mean()

    amount_mean20 = agg["amount_ew"].rolling(window=20, min_periods=10).mean()
    amount_std20 = agg["amount_ew"].rolling(window=20, min_periods=10).std().replace(0.0, np.nan)
    amount_z20 = (agg["amount_ew"] - amount_mean20) / amount_std20

    ret_pivot = all_df.pivot_table(index="date", columns="symbol", values="ret1d", aggfunc="first")
    cross_disp = ret_pivot.std(axis=1, skipna=True)

    out = pd.DataFrame(index=agg.index)
    out["odp_cmdty_ret_1d_ew"] = agg["ret1d_ew"].shift(1)
    out["odp_cmdty_mom_5d_ew"] = agg["mom5_ew"].shift(1)
    out["odp_cmdty_vol_20d_ew"] = agg["vol20_ew"].shift(1)
    out["odp_cmdty_amount_z20_ew"] = amount_z20.shift(1)
    out["odp_cmdty_cross_disp_20d"] = cross_disp.rolling(window=20, min_periods=10).mean().shift(1)
    return out


def _flatten_sequences(
    X: np.ndarray, feature_names: list[str], seq_len: int
) -> tuple[np.ndarray, list[str]]:
    flat = X.reshape(X.shape[0], seq_len * len(feature_names))
    cols: list[str] = []
    for t in range(seq_len):
        for n in feature_names:
            cols.append(f"{n}_t{t}")
    return flat, cols


def _split_by_ratio(
    dates: pd.Series,
    *,
    train_ratio: float,
    valid_ratio: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    if not (0.0 < train_ratio < 1.0):
        raise ValueError("train_ratio must be in (0, 1)")
    if not (0.0 <= valid_ratio < 1.0):
        raise ValueError("valid_ratio must be in [0, 1)")
    if train_ratio + valid_ratio >= 1.0:
        raise ValueError("train_ratio + valid_ratio must be < 1")

    unique_dates = np.array(sorted(pd.unique(dates)))
    n_dates = len(unique_dates)
    train_cut = max(1, int(n_dates * train_ratio))
    valid_cut = max(train_cut, int(n_dates * (train_ratio + valid_ratio)))
    train_dates = set(pd.to_datetime(unique_dates[: min(train_cut, n_dates)]))
    valid_dates = set(
        pd.to_datetime(unique_dates[min(train_cut, n_dates) : min(valid_cut, n_dates)])
    )

    m_train = dates.isin(train_dates).to_numpy()
    m_valid = dates.isin(valid_dates).to_numpy()
    m_test = ~(m_train | m_valid)

    split_config: dict[str, object] = {
        "method": "ratio",
        "train_ratio": float(train_ratio),
        "valid_ratio": float(valid_ratio),
        "test_ratio": float(1.0 - train_ratio - valid_ratio),
    }
    return m_train, m_valid, m_test, split_config


def _split_by_fixed_weeks(
    dates: pd.Series,
    *,
    valid_weeks: int,
    test_weeks: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    if valid_weeks <= 0 or test_weeks <= 0:
        raise ValueError("valid_weeks and test_weeks must be > 0")

    week_periods = dates.dt.to_period("W-FRI")
    unique_weeks = np.array(sorted(pd.unique(week_periods)))
    required = int(valid_weeks + test_weeks + 1)
    if len(unique_weeks) < required:
        raise ValueError(
            f"not enough weeks for fixed split: need >= {required}, got {len(unique_weeks)} "
            f"(valid_weeks={valid_weeks}, test_weeks={test_weeks})"
        )

    test_set = set(unique_weeks[-test_weeks:])
    valid_set = set(unique_weeks[-(valid_weeks + test_weeks) : -test_weeks])
    m_test = week_periods.isin(test_set).to_numpy()
    m_valid = week_periods.isin(valid_set).to_numpy()
    m_train = ~(m_valid | m_test)

    split_config: dict[str, object] = {
        "method": "fixed_weeks",
        "valid_weeks": int(valid_weeks),
        "test_weeks": int(test_weeks),
    }
    return m_train, m_valid, m_test, split_config


def _argparse_allowed_keys(parser: argparse.ArgumentParser) -> set[str]:
    return {a.dest for a in parser._actions if a.dest != "help"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build sequence parquet dataset with market state features."
    )
    parser.add_argument(
        "--config-file", default="", help="JSON/TOML config file path (args mapping)"
    )
    parser.add_argument(
        "--effective-config-out",
        default="",
        help="optional: save effective merged config (after CLI overrides) to JSON",
    )
    parser.add_argument(
        "--symbols-csv", default=DEFAULT_SYMBOLS_CSV, help="股票列表 CSV，需含 symbol 列"
    )
    parser.add_argument("--stock-pool-id", default="", help="从 registry 读取股票池成员")
    parser.add_argument(
        "--stock-pool-version", default="", help="股票池版本，留空则要求 registry 内仅有单版本"
    )
    parser.add_argument(
        "--stock-pool-registry-dir", default="inputs/pools", help="股票池 registry 目录"
    )
    parser.add_argument(
        "--stock-pool-export-dir", default="output/stock_pools", help="导出的股票池产物目录"
    )
    parser.add_argument("--cache-dir", default="data/cache")
    parser.add_argument(
        "--source",
        default="tushare_live",
        choices=["akshare", "tushare_cache", "tushare_live"],
        help="行情来源：akshare 在线拉取、tushare 本地缓存或 tushare 在线拉取",
    )
    parser.add_argument(
        "--request-interval-seconds",
        type=float,
        default=0.8,
        help="每只股票请求后睡眠秒数（用于限流，默认 0.8）",
    )
    parser.add_argument("--start", default="20210101")
    parser.add_argument("--end", default="20260120")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--valid-weeks", type=int, default=26)
    parser.add_argument("--test-weeks", type=int, default=26)
    parser.add_argument(
        "--train-ratio", type=float, default=None, help="Deprecated: ratio split mode"
    )
    parser.add_argument(
        "--valid-ratio", type=float, default=None, help="Deprecated: ratio split mode"
    )
    parser.add_argument("--horizons", default="3,5,10")
    parser.add_argument(
        "--label-mode",
        default="close_to_close",
        choices=["close_to_close", "next_open_to_open"],
        help="Label calculation mode (default: close_to_close for backward compatibility)",
    )
    parser.add_argument(
        "--include-1d-hlc-labels",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="是否追加 1 日 high/low/close 标签（label_1d_high/low/close）",
    )
    parser.add_argument(
        "--output-dir", default="data/datasets/lstm_sector70_19d_mkt_20210101_20260120"
    )
    parser.add_argument(
        "--feature-profile",
        default="compact44",
        choices=list(FEATURE_PROFILES),
        help="compact44: 精简特征集合（默认）；full58: 保留扩展后全部特征；no_hist_hl: 去历史高低价特征",
    )
    parser.add_argument(
        "--include-short-term-features",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否加入 TuShare 的换手与资金流特征（默认开启）",
    )
    parser.add_argument(
        "--sector-etf-map-csv",
        default="",
        help="可选：symbol->etf 映射 CSV，需含 symbol 与 etf_ts_code(etf_symbol) 列",
    )
    parser.add_argument(
        "--include-sector-etf-features",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否加入板块ETF特征（默认开启；需配合 --sector-etf-map-csv）",
    )
    parser.add_argument(
        "--include-odp-commodity-features",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="是否加入 ODP 国际大宗商品特征（默认关闭）",
    )
    parser.add_argument(
        "--commodity-source",
        default="odp",
        choices=["odp", "tushare_fut"],
        help="商品数据来源：odp(国际) 或 tushare_fut(国内期货)",
    )
    parser.add_argument(
        "--odp-provider",
        default="yfinance",
        help="ODP provider（默认 yfinance）",
    )
    parser.add_argument(
        "--odp-base-url",
        default="",
        help="可选：ODP REST 服务地址（例如 http://127.0.0.1:8000）",
    )
    parser.add_argument(
        "--odp-prefer-rest",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="ODP 拉取优先走 REST（默认优先 SDK）",
    )
    parser.add_argument(
        "--odp-commodity-symbols",
        default="CL=F,GC=F,HG=F,NG=F,SI=F,ZC=F",
        help="ODP 国际大宗商品代码列表（逗号分隔）",
    )
    parser.add_argument(
        "--tushare-fut-exchanges",
        default="SHFE,DCE,CZCE,INE,GFEX",
        help="TuShare 期货交易所列表（逗号分隔）",
    )
    parser.add_argument(
        "--tushare-fut-symbols",
        default="CU.SHF,AL.SHF,ZN.SHF,PB.SHF,NI.SHF,SN.SHF,AU.SHF,AG.SHF,RB.SHF,HC.SHF,SC.INE,FU.SHF,BU.SHF,PG.DCE,ZC.CZCE",
        help="TuShare 期货符号过滤（逗号分隔，支持 ts_code 或品种简称）",
    )
    parser.add_argument(
        "--tushare-fut-main-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否仅使用主连/连续类代码（默认开启）",
    )
    parser.add_argument(
        "--tushare-fut-page-limit",
        type=int,
        default=2000,
        help="TuShare fut_daily 单页 limit（默认 2000）",
    )
    parser.add_argument(
        "--tushare-fut-max-pages",
        type=int,
        default=120,
        help="TuShare fut_daily 每个交易所最大翻页数（默认 120）",
    )
    parser.add_argument(
        "--tushare-fut-page-sleep-seconds",
        type=float,
        default=0.05,
        help="TuShare fut_daily 翻页间隔秒数（默认 0.05）",
    )
    pre_args, _ = parser.parse_known_args()
    config_section_used: str | None = None
    if pre_args.config_file:
        allowed_keys = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        overrides, config_section_used = extract_arg_overrides(
            config_path=pre_args.config_file,
            allowed_keys=allowed_keys,
            section_candidates=(CONFIG_SECTION_NAME, "build_sequence_dataset", "dataset"),
        )
        parser.set_defaults(**overrides)
    args = parser.parse_args()
    config_file_resolved = (
        str(Path(args.config_file).resolve()) if str(args.config_file).strip() else ""
    )
    effective_config_path = ""
    effective_config_out = str(args.effective_config_out).strip()
    if effective_config_out:
        effective_config_path = effective_config_out
    elif config_file_resolved:
        effective_config_path = str(
            Path(args.output_dir) / "build_sequence_dataset_market_state_effective_config.json"
        )

    if effective_config_path:
        allowed_effective = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        effective_args = {k: getattr(args, k) for k in sorted(allowed_effective)}
        saved = dump_json(
            effective_config_path,
            {
                "script": CONFIG_SECTION_NAME,
                "config_file": config_file_resolved or None,
                "config_section": config_section_used,
                "args": effective_args,
            },
        )
        print(f"Saved effective config: {saved}")

    symbols, stock_pool_context = _resolve_symbols_input(
        symbols_csv=args.symbols_csv,
        stock_pool_id=str(args.stock_pool_id),
        stock_pool_version=str(args.stock_pool_version),
        stock_pool_registry_dir=str(args.stock_pool_registry_dir),
        stock_pool_export_dir=str(args.stock_pool_export_dir),
    )
    horizons = tuple(int(x.strip()) for x in str(args.horizons).split(",") if x.strip())
    cache_dir = Path(args.cache_dir)

    all_bars: dict[str, pd.DataFrame] = {}
    for idx, s in enumerate(symbols):
        try:
            bars = _load_bars(args.source, s, args.start, args.end, cache_dir)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {s} source={args.source} fetch error: {type(e).__name__}: {e}")
            continue
        if bars.empty:
            print(f"[warn] {s} no data from source={args.source}")
            continue
        all_bars[s] = bars

        # TuShare 存在分钟级限流，按 symbol 级别节流。
        if (
            args.source.startswith("tushare")
            and idx < len(symbols) - 1
            and args.request_interval_seconds > 0
        ):
            time.sleep(float(args.request_interval_seconds))

    if not all_bars:
        raise RuntimeError("no symbol bars available from cache")

    etf_map: dict[str, str] = {}
    etf_features_by_symbol: dict[str, pd.DataFrame] = {}
    if bool(args.include_sector_etf_features) and str(args.sector_etf_map_csv).strip():
        etf_map = _parse_sector_etf_map(Path(args.sector_etf_map_csv), symbols)
        unique_etf_codes = sorted(set(etf_map.values()))
        etf_feature_by_code: dict[str, pd.DataFrame] = {}
        for idx, etf_code in enumerate(unique_etf_codes):
            try:
                etf_bars = _load_tushare_fund_daily_cache_or_live(
                    ts_code=etf_code,
                    start=args.start,
                    end=args.end,
                    cache_dir=cache_dir,
                    source=args.source,
                    retries=5,
                )
            except Exception as e:  # noqa: BLE001
                print(
                    f"[warn] ETF {etf_code} source={args.source} fetch error: {type(e).__name__}: {e}"
                )
                continue
            if etf_bars.empty:
                print(f"[warn] ETF {etf_code} has no fund_daily data from source={args.source}")
                continue
            etf_feat = _drop_all_nan_columns(_compute_etf_features(etf_bars))
            if not etf_feat.empty:
                etf_feature_by_code[etf_code] = etf_feat

            if (
                args.source.startswith("tushare")
                and idx < len(unique_etf_codes) - 1
                and args.request_interval_seconds > 0
            ):
                time.sleep(float(args.request_interval_seconds))

        for s, etf_code in etf_map.items():
            feat = etf_feature_by_code.get(etf_code)
            if feat is not None and not feat.empty:
                etf_features_by_symbol[s] = feat

    market_state = _compute_market_state_features(all_bars)
    commodity_source = str(args.commodity_source).strip().lower()
    odp_symbols = _parse_symbol_list(str(args.odp_commodity_symbols))
    tushare_fut_exchanges = _parse_symbol_list(str(args.tushare_fut_exchanges))
    tushare_fut_symbols = _parse_symbol_list(str(args.tushare_fut_symbols))
    commodity_market_state = pd.DataFrame(index=market_state.index.copy())
    if bool(args.include_odp_commodity_features):
        commodity_bars: dict[str, pd.DataFrame] = {}
        if commodity_source == "odp":
            if odp_symbols:
                commodity_bars = _load_odp_commodity_bars(
                    odp_symbols,
                    start=args.start,
                    end=args.end,
                    cache_dir=cache_dir,
                    provider=str(args.odp_provider),
                    base_url=str(args.odp_base_url).strip() or None,
                    prefer_rest=bool(args.odp_prefer_rest),
                    request_interval_seconds=float(args.request_interval_seconds),
                )
        elif commodity_source == "tushare_fut":
            if not tushare_fut_exchanges:
                print("[warn] commodity_source=tushare_fut but no exchanges configured")
            else:
                commodity_bars = _load_tushare_commodity_bars(
                    start=args.start,
                    end=args.end,
                    exchanges=tushare_fut_exchanges,
                    symbols=tushare_fut_symbols,
                    main_only=bool(args.tushare_fut_main_only),
                    page_limit=int(args.tushare_fut_page_limit),
                    max_pages=int(args.tushare_fut_max_pages),
                    page_sleep_seconds=float(args.tushare_fut_page_sleep_seconds),
                    request_interval_seconds=float(args.request_interval_seconds),
                )
        else:
            raise ValueError(f"unsupported commodity_source: {commodity_source}")

        commodity_market_state = _compute_commodity_features(commodity_bars)
        commodity_market_state = commodity_market_state.reindex(market_state.index)
        if commodity_market_state.empty:
            print(
                f"[warn] commodity features are enabled but no valid data loaded (source={commodity_source})"
            )

    market_state = market_state.join(commodity_market_state, how="left")

    feat_frames: list[pd.DataFrame] = []
    lab_frames: list[pd.DataFrame] = []
    for symbol, bars in all_bars.items():
        feats = _compute_symbol_features(
            bars,
            include_short_term_features=bool(args.include_short_term_features),
            feature_profile=str(args.feature_profile),
            etf_features=etf_features_by_symbol.get(symbol),
        )
        feats = feats.join(market_state, how="left")
        labs = MultiHorizonLabel(horizons=horizons, label_mode=args.label_mode).compute(bars)
        if bool(args.include_1d_hlc_labels):
            labs = pd.concat(
                [labs, OneDayHLCLabel(label_mode=args.label_mode).compute(bars)], axis=1
            )

        feats = feats.assign(symbol=symbol).reset_index().set_index(["date", "symbol"]).sort_index()
        labs = labs.assign(symbol=symbol).reset_index().set_index(["date", "symbol"]).sort_index()
        feat_frames.append(feats)
        lab_frames.append(labs)

    features_all = pd.concat(feat_frames).sort_index()
    labels_all = pd.concat(lab_frames).sort_index()

    builder = SequenceDatasetBuilder(seq_len=args.seq_len, stride=args.stride)
    X, y = builder.build_sequences(features_all, labels_all)
    if builder.sample_meta_ is None:
        raise RuntimeError("sample_meta_ missing after build_sequences")

    feature_names = builder.feature_columns_ or list(features_all.columns)
    label_names = builder.label_columns_ or list(labels_all.columns)
    flat_X, x_cols = _flatten_sequences(X, feature_names, args.seq_len)
    meta = builder.sample_meta_.copy()

    full_df = pd.concat(
        [
            meta.reset_index(drop=True),
            pd.DataFrame(flat_X, columns=x_cols),
            pd.DataFrame(y, columns=label_names),
        ],
        axis=1,
    )

    dates = pd.to_datetime(meta["date"])
    use_ratio = args.train_ratio is not None or args.valid_ratio is not None
    if use_ratio:
        if args.train_ratio is None or args.valid_ratio is None:
            raise ValueError("ratio mode requires both --train-ratio and --valid-ratio")
        print("WARN: ratio split mode is deprecated; please use --valid-weeks/--test-weeks")
        m_train, m_valid, m_test, split_config = _split_by_ratio(
            dates,
            train_ratio=float(args.train_ratio),
            valid_ratio=float(args.valid_ratio),
        )
    else:
        m_train, m_valid, m_test, split_config = _split_by_fixed_weeks(
            dates,
            valid_weeks=int(args.valid_weeks),
            test_weeks=int(args.test_weeks),
        )

    if int(m_train.sum()) == 0 or int(m_valid.sum()) == 0 or int(m_test.sum()) == 0:
        raise RuntimeError("invalid split: one of train/valid/test is empty")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, mask in [("train", m_train), ("valid", m_valid), ("test", m_test)]:
        p = out_dir / f"{name}.parquet"
        full_df.loc[mask].reset_index(drop=True).to_parquet(p, index=False)
        print(f"{name}: {int(mask.sum())} -> {p}")

    train_dates = dates[m_train]
    valid_dates = dates[m_valid]
    test_dates = dates[m_test]
    split_config = {
        **split_config,
        "train_samples": int(m_train.sum()),
        "valid_samples": int(m_valid.sum()),
        "test_samples": int(m_test.sum()),
        "train_start_date": str(train_dates.min().date()),
        "train_end_date": str(train_dates.max().date()),
        "valid_start_date": str(valid_dates.min().date()),
        "valid_end_date": str(valid_dates.max().date()),
        "test_start_date": str(test_dates.min().date()),
        "test_end_date": str(test_dates.max().date()),
    }

    # --- metadata.json ---
    metadata = {
        "dataset_config": {
            "source": args.source,
            "symbols_csv": stock_pool_context["symbols_csv"],
            "num_symbols": len(all_bars),
            "start_date": args.start,
            "end_date": args.end,
            "stock_pool_id": stock_pool_context["stock_pool_id"],
            "stock_pool_version": stock_pool_context["stock_pool_version"],
            "stock_pool_registry_path": stock_pool_context["registry_path"],
            "include_odp_commodity_features": bool(args.include_odp_commodity_features),
            "commodity_source": commodity_source,
            "odp_provider": str(args.odp_provider),
            "odp_commodity_symbols": odp_symbols if commodity_source == "odp" else [],
            "tushare_fut_exchanges": tushare_fut_exchanges
            if commodity_source == "tushare_fut"
            else [],
            "tushare_fut_symbols": tushare_fut_symbols if commodity_source == "tushare_fut" else [],
            "tushare_fut_main_only": bool(args.tushare_fut_main_only),
            "config_file": config_file_resolved,
            "config_section": config_section_used,
            "effective_config_path": effective_config_path,
        },
        "label_config": {
            "horizons": list(horizons),
            "label_mode": args.label_mode,
            "include_1d_hlc_labels": bool(args.include_1d_hlc_labels),
        },
        "feature_config": {
            "num_features": len(feature_names),
            "feature_names": feature_names,
            "feature_profile": args.feature_profile,
            "seq_len": args.seq_len,
            "stride": args.stride,
        },
        "split_config": split_config,
    }
    metadata["dataset_id"] = infer_dataset_id(
        dataset_dir=out_dir,
        dataset_metadata=metadata,
        dataset_id="",
        stock_pool_id=stock_pool_context["stock_pool_id"] or f"custom_symbols{len(symbols)}",
    )
    metadata_path = out_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Metadata saved: {metadata_path}")

    print(f"symbols_loaded: {len(all_bars)}")
    print(f"feature_count: {len(feature_names)}")
    print(f"feature_names: {feature_names}")
    print(f"feature_profile: {args.feature_profile}")
    market_features_present = [n for n in MARKET_FEATURE_NAMES if n in feature_names]
    odp_features_present = [n for n in ODP_COMMODITY_FEATURE_NAMES if n in feature_names]
    print(f"market_features: {market_features_present}")
    if odp_features_present:
        print(f"commodity_features(source={commodity_source}): {odp_features_present}")
    if args.include_short_term_features:
        symbol_feature_names = [f.name for f in SYMBOL_FEATURES_16]
        short_term_features = [
            n
            for n in feature_names
            if n not in symbol_feature_names
            and n not in MARKET_FEATURE_NAMES
            and n not in ODP_COMMODITY_FEATURE_NAMES
            and n not in ETF_FEATURE_NAMES
        ]
        etf_features = [n for n in feature_names if n in ETF_FEATURE_NAMES]
        print(f"short_term_features({len(short_term_features)}): {short_term_features}")
        if etf_features:
            print(f"sector_etf_features({len(etf_features)}): {etf_features}")
            print(
                f"sector_etf_mapping: symbols={len(etf_map)}, mapped_with_data={len(etf_features_by_symbol)}, "
                f"unique_etf={len(set(etf_map.values())) if etf_map else 0}"
            )
        dropped = PROFILE_DROP_FEATURES.get(str(args.feature_profile), set())
        if dropped:
            print(f"{args.feature_profile}_dropped_features({len(dropped)}): {sorted(dropped)}")
    print(f"X_shape: {X.shape}, y_shape: {y.shape}")


if __name__ == "__main__":
    main()
