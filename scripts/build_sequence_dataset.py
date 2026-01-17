#!/usr/bin/env python
"""Build sequence dataset (X: [N, seq_len, n_feat], y: [N, 3]) and save to Parquet.

This script loads daily bars, computes MVP features and 3/5/10-day forward return labels,
then converts them into fixed-length sequences with strict time alignment:
label at date t only uses features from dates <= t-1.

Outputs (default):
  - data/datasets/train.parquet
  - data/datasets/valid.parquet
  - data/datasets/test.parquet
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ashare_lab.data.akshare_source import AkshareDailyBarsRequest, load_or_fetch_daily_bars
from ashare_lab.data.tushare_source import TushareDailyBarsRequest, load_or_fetch_daily_bars as load_tushare
from ashare_lab.dataset.sequence_builder import SequenceDatasetBuilder
from ashare_lab.features.momentum import Return1D, Return20D, Return5D
from ashare_lab.features.volume import AmountChange, VolumeChange, VolumeRatio
from ashare_lab.labels.multi_horizon import MultiHorizonLabel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("build_sequence_dataset")


def _parse_symbols(symbols: str | None, symbols_csv: str | None) -> list[str]:
    if symbols and symbols_csv:
        raise ValueError("use either --symbols or --symbols-csv, not both")

    if symbols:
        out = [s.strip() for s in symbols.split(",") if s.strip()]
        if not out:
            raise ValueError("--symbols is empty")
        return out

    if symbols_csv:
        path = Path(symbols_csv)
        df = pd.read_csv(path, dtype=str)
        # tolerate common column names
        for col in ["symbol", "code", "ts_code"]:
            if col in df.columns:
                out = df[col].dropna().astype(str).tolist()
                out = [s.strip() for s in out if s.strip()]
                if col in {"code"}:
                    out = [s.zfill(6) for s in out]
                if not out:
                    raise ValueError(f"no symbols found in column '{col}' of {path}")
                return sorted(set(out))
        raise ValueError(f"{path} must contain one of columns: symbol, code, ts_code")

    raise ValueError("either --symbols or --symbols-csv is required")


def _compute_features(data: pd.DataFrame) -> pd.DataFrame:
    features = [
        Return1D(),
        Return5D(),
        Return20D(),
        VolumeRatio(window=5),
        VolumeChange(),
        AmountChange(),
    ]
    feat_dict: dict[str, pd.Series] = {}
    for f in features:
        feat_dict[f.name] = f.compute(data)
    return pd.DataFrame(feat_dict, index=data.index)


def _compute_labels(data: pd.DataFrame, horizons: Iterable[int]) -> pd.DataFrame:
    return MultiHorizonLabel(horizons=horizons).compute(data)


def _load_bars(source: str, symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    if source == "akshare":
        req = AkshareDailyBarsRequest(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
        return load_or_fetch_daily_bars(req, cache_dir)
    if source == "tushare":
        ts_code = symbol
        if len(ts_code) == 6 and "." not in ts_code:
            # heuristic: 60/68/90/93 -> SH, others -> SZ
            ts_code = f"{ts_code}.SH" if ts_code[:2] in {"60", "68", "90", "93"} else f"{ts_code}.SZ"
        req = TushareDailyBarsRequest(symbol=ts_code, start_date=start, end_date=end, adjust="qfq")
        return load_tushare(req, cache_dir)
    raise ValueError(f"unsupported --source: {source}")


def _flatten_sequences(
    X: np.ndarray, feature_names: list[str], seq_len: int
) -> tuple[np.ndarray, list[str]]:
    n_feat = len(feature_names)
    if X.ndim != 3 or X.shape[1] != seq_len or X.shape[2] != n_feat:
        raise ValueError("X has unexpected shape, cannot flatten")
    flat = X.reshape(X.shape[0], seq_len * n_feat)
    cols: list[str] = []
    # t0 is the oldest timestep in the window; t{seq_len-1} is the newest (t-1)
    for t in range(seq_len):
        for name in feature_names:
            cols.append(f"{name}_t{t}")
    return flat, cols


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sequence dataset and save Parquet splits.")
    parser.add_argument("--start", required=True, help="Start date YYYYMMDD")
    parser.add_argument("--end", required=True, help="End date YYYYMMDD")
    parser.add_argument("--symbols", help="Comma-separated symbols, e.g. 600519,000333")
    parser.add_argument("--symbols-csv", help="CSV file containing symbols (column: symbol/code/ts_code)")
    parser.add_argument("--source", default="akshare", choices=["akshare", "tushare"], help="Data source")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache dir for daily bars")
    parser.add_argument("--output-dir", default="data/datasets", help="Output dir for parquet files")
    parser.add_argument("--seq-len", type=int, default=30, help="Sequence length (default: 30)")
    parser.add_argument("--stride", type=int, default=1, help="Sliding window stride (default: 1)")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Train ratio (default: 0.7)")
    parser.add_argument("--valid-ratio", type=float, default=0.15, help="Valid ratio (default: 0.15)")
    parser.add_argument(
        "--horizons",
        default="3,5,10",
        help="Label horizons in days (default: 3,5,10)",
    )
    args = parser.parse_args()

    symbols = _parse_symbols(args.symbols, args.symbols_csv)
    cache_dir = Path(args.cache_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    horizons = tuple(int(x.strip()) for x in str(args.horizons).split(",") if x.strip())
    if len(horizons) == 0:
        raise ValueError("--horizons is empty")

    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Date range: {args.start} ~ {args.end}")
    logger.info(f"seq_len={args.seq_len}, stride={args.stride}, horizons={horizons}")

    feature_frames: list[pd.DataFrame] = []
    label_frames: list[pd.DataFrame] = []

    for symbol in symbols:
        bars = _load_bars(args.source, symbol, args.start, args.end, cache_dir)
        if bars.empty:
            logger.warning(f"{symbol}: empty bars, skip")
            continue

        feats = _compute_features(bars)
        labs = _compute_labels(bars, horizons=horizons)

        feats = feats.assign(symbol=str(symbol)).reset_index().set_index(["date", "symbol"]).sort_index()
        labs = labs.assign(symbol=str(symbol)).reset_index().set_index(["date", "symbol"]).sort_index()
        feature_frames.append(feats)
        label_frames.append(labs)

    if not feature_frames:
        raise RuntimeError("no data loaded; cannot build dataset")

    features_all = pd.concat(feature_frames).sort_index()
    labels_all = pd.concat(label_frames).sort_index()

    builder = SequenceDatasetBuilder(seq_len=args.seq_len, stride=args.stride)
    X, y = builder.build_sequences(features_all, labels_all)
    splits = builder.split_walk_forward(X, y, train_ratio=args.train_ratio, valid_ratio=args.valid_ratio)

    flat_X, x_cols = _flatten_sequences(X, builder.feature_columns_ or list(features_all.columns), args.seq_len)
    y_cols = builder.label_columns_ or list(labels_all.columns)

    if builder.sample_meta_ is None:
        raise RuntimeError("internal error: sample_meta_ not available after build_sequences")

    meta = builder.sample_meta_.copy()
    full_df = pd.concat(
        [
            meta.reset_index(drop=True),
            pd.DataFrame(flat_X, columns=x_cols),
            pd.DataFrame(y, columns=y_cols),
        ],
        axis=1,
    )

    def _save_split(name: str, mask: np.ndarray) -> Path:
        df = full_df.loc[mask].reset_index(drop=True)
        out_path = output_dir / f"{name}.parquet"
        df.to_parquet(out_path, index=False)
        return out_path

    # Reconstruct masks from returned arrays by matching object identity (fast path)
    # Since splits are sliced views, we use lengths to carve masks from sample order.
    # For strict reproducibility, rebuild boolean masks based on dates.
    dates = pd.to_datetime(meta["date"])
    unique_dates = np.array(sorted(pd.unique(dates)))
    n_dates = len(unique_dates)
    train_cut = max(1, int(n_dates * args.train_ratio))
    valid_cut = max(train_cut, int(n_dates * (args.train_ratio + args.valid_ratio)))
    train_dates = set(unique_dates[: min(train_cut, n_dates)].tolist())
    valid_dates = set(unique_dates[min(train_cut, n_dates) : min(valid_cut, n_dates)].tolist())
    m_train = dates.isin(train_dates).to_numpy()
    m_valid = dates.isin(valid_dates).to_numpy()
    m_test = ~(m_train | m_valid)

    out_train = _save_split("train", m_train)
    out_valid = _save_split("valid", m_valid)
    out_test = _save_split("test", m_test)

    logger.info("Saved:")
    logger.info(f"  train: {out_train} ({m_train.sum()} samples)")
    logger.info(f"  valid: {out_valid} ({m_valid.sum()} samples)")
    logger.info(f"  test : {out_test} ({m_test.sum()} samples)")

    logger.info(f"X: {X.shape} (n_feat={X.shape[2]}), y: {y.shape}")
    y_df = pd.DataFrame(y, columns=y_cols)
    for col in y_cols:
        valid_ratio = float(y_df[col].notna().mean())
        mean = float(y_df[col].mean(skipna=True))
        std = float(y_df[col].std(skipna=True))
        logger.info(f"{col}: valid={valid_ratio:.2%}, mean={mean:.6f}, std={std:.6f}")


if __name__ == "__main__":
    main()
