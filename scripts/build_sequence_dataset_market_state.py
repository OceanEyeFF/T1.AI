#!/usr/bin/env python
"""Build sequence dataset with market state features.

Market state features are calculated cross-sectionally from the selected universe:
  - market_mom_5d: 5-day momentum of equal-weight market return series
  - market_vol_20d: 20-day volatility of equal-weight market return series
  - market_amount_z20: z-score of total market amount over 20-day rolling window
All market features are shifted by 1 day to avoid look-ahead leakage.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_lab.data.akshare_source import AkshareDailyBarsRequest, load_or_fetch_daily_bars
from ashare_lab.data.tushare_source import TushareDailyBarsRequest, load_or_fetch_daily_bars as load_tushare_daily_bars
from ashare_lab.dataset.sequence_builder import SequenceDatasetBuilder
from ashare_lab.features.momentum import Return1D, Return5D, Return10D, Return20D, Return60D
from ashare_lab.features.price_slope import PriceSlope
from ashare_lab.features.technical import BollingerDeviation, MACDHist, MACDLine, MACDSignal, RSI
from ashare_lab.features.volume import AmountChange, RelativeVolume, VolumeChange, VolumeRatio
from ashare_lab.labels.multi_horizon import MultiHorizonLabel

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


def _parse_symbols(path: Path) -> list[str]:
    df = pd.read_csv(path, dtype=str)
    if "symbol" not in df.columns:
        raise ValueError(f"{path} must contain a `symbol` column")
    syms = [str(s).strip().zfill(6) for s in df["symbol"].dropna().tolist() if str(s).strip()]
    out = sorted(set(syms))
    if not out:
        raise ValueError(f"no symbols parsed from {path}")
    return out


def _to_ts_code(symbol: str) -> str:
    return f"{symbol}.SH" if symbol[:2] in {"60", "68", "90", "93"} else f"{symbol}.SZ"


def _load_tushare_cache_only(ts_code: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    symbol_dir = cache_dir / "tushare" / ts_code
    if not symbol_dir.exists():
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])

    frames: list[pd.DataFrame] = []
    for part in symbol_dir.glob("year=*/part.parquet"):
        df = pd.read_parquet(part)
        if "date" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        keep = [c for c in ["open", "high", "low", "close", "volume", "amount"] if c in df.columns]
        frames.append(df[keep])

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])

    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "date"

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)
    return out.loc[(out.index >= start_ts) & (out.index <= end_ts)].copy()


def _load_akshare(symbol: str, start: str, end: str, cache_dir: Path, retries: int = 3) -> pd.DataFrame:
    req = AkshareDailyBarsRequest(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
    last_err: Exception | None = None
    for i in range(retries):
        try:
            return load_or_fetch_daily_bars(req, cache_dir / "akshare")
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait_s = 1.0 + float(i)
            print(f"[warn] {symbol} akshare attempt={i + 1}/{retries} failed: {type(e).__name__}: {e}; sleep={wait_s}s")
            time.sleep(wait_s)
    if last_err is not None:
        print(f"[warn] {symbol} akshare all retries failed: {type(last_err).__name__}: {last_err}")
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])


def _load_tushare_live(symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    ts_code = _to_ts_code(symbol)
    req = TushareDailyBarsRequest(symbol=ts_code, start_date=start, end_date=end, adjust="qfq")
    return load_tushare_daily_bars(req, cache_dir, refresh=False, retries=5, backoff_base=1.0)


def _load_bars(source: str, symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    if source == "tushare_cache":
        ts_code = _to_ts_code(symbol)
        return _load_tushare_cache_only(ts_code, start, end, cache_dir)
    if source == "tushare_live":
        return _load_tushare_live(symbol, start, end, cache_dir)
    if source == "akshare":
        return _load_akshare(symbol, start, end, cache_dir)
    raise ValueError(f"unsupported source: {source}")


def _compute_symbol_features(bars: pd.DataFrame) -> pd.DataFrame:
    feat: dict[str, pd.Series] = {}
    for f in SYMBOL_FEATURES_16:
        feat[f.name] = f.compute(bars)
    return pd.DataFrame(feat, index=bars.index)


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

    mom5 = ((1.0 + market["mkt_ret1d"]).rolling(window=5, min_periods=5).apply(np.prod, raw=True) - 1.0).shift(1)
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


def _flatten_sequences(X: np.ndarray, feature_names: list[str], seq_len: int) -> tuple[np.ndarray, list[str]]:
    flat = X.reshape(X.shape[0], seq_len * len(feature_names))
    cols: list[str] = []
    for t in range(seq_len):
        for n in feature_names:
            cols.append(f"{n}_t{t}")
    return flat, cols


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sequence parquet dataset with market state features.")
    parser.add_argument("--symbols-csv", default="data/symbols_lstm_sectors_70.csv")
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
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--valid-ratio", type=float, default=0.15)
    parser.add_argument("--horizons", default="3,5,10")
    parser.add_argument("--output-dir", default="data/datasets/lstm_sector70_19d_mkt_20210101_20260120")
    args = parser.parse_args()

    symbols = _parse_symbols(Path(args.symbols_csv))
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
        if args.source.startswith("tushare") and idx < len(symbols) - 1 and args.request_interval_seconds > 0:
            time.sleep(float(args.request_interval_seconds))

    if not all_bars:
        raise RuntimeError("no symbol bars available from cache")

    market_state = _compute_market_state_features(all_bars)

    feat_frames: list[pd.DataFrame] = []
    lab_frames: list[pd.DataFrame] = []
    for symbol, bars in all_bars.items():
        feats = _compute_symbol_features(bars)
        feats = feats.join(market_state, how="left")
        labs = MultiHorizonLabel(horizons=horizons).compute(bars)

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
    unique_dates = np.array(sorted(pd.unique(dates)))
    n_dates = len(unique_dates)
    train_cut = max(1, int(n_dates * args.train_ratio))
    valid_cut = max(train_cut, int(n_dates * (args.train_ratio + args.valid_ratio)))
    train_dates = set(pd.to_datetime(unique_dates[: min(train_cut, n_dates)]))
    valid_dates = set(pd.to_datetime(unique_dates[min(train_cut, n_dates) : min(valid_cut, n_dates)]))

    m_train = dates.isin(train_dates).to_numpy()
    m_valid = dates.isin(valid_dates).to_numpy()
    m_test = ~(m_train | m_valid)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, mask in [("train", m_train), ("valid", m_valid), ("test", m_test)]:
        p = out_dir / f"{name}.parquet"
        full_df.loc[mask].reset_index(drop=True).to_parquet(p, index=False)
        print(f"{name}: {int(mask.sum())} -> {p}")

    print(f"symbols_loaded: {len(all_bars)}")
    print(f"feature_count: {len(feature_names)}")
    print(f"feature_names: {feature_names}")
    print(f"market_features: {MARKET_FEATURE_NAMES}")
    print(f"X_shape: {X.shape}, y_shape: {y.shape}")


if __name__ == "__main__":
    main()
