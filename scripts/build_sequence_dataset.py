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
import json
import logging
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ashare_infra.lake import DataLake
from ashare_infra.lake.r4_contract import R4_ADJUST_DEFAULT, make_r4_datalake
from ashare_lab.dataset.sequence_builder import SequenceDatasetBuilder
from ashare_lab.features.momentum import Return1D, Return20D, Return5D
from ashare_lab.features.volume import AmountChange, VolumeChange, VolumeRatio
from ashare_lab.features.technical import RSI, MACDHist, BollingerDeviation
from ashare_lab.features.price_slope import PriceSlope
from ashare_lab.labels.multi_horizon import MultiHorizonLabel, OneDayHLCLabel
from ashare_lab.stock_pool import export_stock_pool_artifacts, get_stock_pool_record, resolve_stock_pool_symbols

try:
    from scripts.config_io import dump_json, extract_arg_overrides
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config_io import dump_json, extract_arg_overrides
try:
    from scripts.runtime_metadata import infer_dataset_id
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from runtime_metadata import infer_dataset_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("build_sequence_dataset")
CONFIG_SECTION_NAME = "build_sequence_dataset"


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


def _resolve_symbols_input(
    *,
    symbols: str | None,
    symbols_csv: str | None,
    stock_pool_id: str,
    stock_pool_version: str,
    stock_pool_registry_dir: str,
    stock_pool_export_dir: str,
) -> tuple[list[str], dict[str, str]]:
    if str(stock_pool_id).strip():
        if symbols or symbols_csv:
            raise ValueError("use either stock_pool_id or symbols/symbols_csv, not both")
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

    resolved_symbols = _parse_symbols(symbols, symbols_csv)
    return resolved_symbols, {
        "stock_pool_id": "",
        "stock_pool_version": "",
        "symbols_csv": str(symbols_csv or ""),
        "registry_path": "",
    }


def _compute_features(data: pd.DataFrame) -> pd.DataFrame:
    """Compute MVP + technical indicator features.

    Features (11 total):
    - Momentum: Return1D, Return5D, Return20D
    - Volume: VolumeRatio, VolumeChange, AmountChange
    - Technical: RSI(14), MACDHist, BollingerDeviation
    - Trend: PriceSlope(5), PriceSlope(20)
    """
    features = [
        # Momentum features (3)
        Return1D(),
        Return5D(),
        Return20D(),
        # Volume features (3)
        VolumeRatio(window=5),
        VolumeChange(),
        AmountChange(),
        # Technical indicators (3)
        RSI(period=14),
        MACDHist(),
        BollingerDeviation(window=20),
        # Trend features (2)
        PriceSlope(window=5),
        PriceSlope(window=20),
    ]
    feat_dict: dict[str, pd.Series] = {}
    for f in features:
        feat_dict[f.name] = f.compute(data)
    return pd.DataFrame(feat_dict, index=data.index)


def _compute_labels(
    data: pd.DataFrame,
    horizons: Iterable[int],
    label_mode: str = "close_to_close",
    include_1d_hlc_labels: bool = False,
) -> pd.DataFrame:
    labels = MultiHorizonLabel(horizons=horizons, label_mode=label_mode).compute(data)
    if include_1d_hlc_labels:
        hlc_labels = OneDayHLCLabel(label_mode=label_mode).compute(data)
        labels = pd.concat([labels, hlc_labels], axis=1)
    return labels


def _load_bars(source: str, symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    from ashare_lab.symbols import symbol_to_odp_equity_symbol, symbol_to_ts_code

    if source not in {"akshare", "tushare", "odp"}:
        raise ValueError(f"unsupported --source: {source}")

    if source == "tushare":
        lake = make_r4_datalake(cache_dir=cache_dir)
        lake_symbol = symbol_to_ts_code(symbol)
    else:
        lake = DataLake(cache_dir=cache_dir, default_source=source)  # type: ignore[arg-type]
        if source == "odp":
            lake_symbol = symbol_to_odp_equity_symbol(symbol)
        else:
            lake_symbol = symbol
    return lake.load_daily_bars(
        lake_symbol, start, end, source=source, adjust=R4_ADJUST_DEFAULT  # type: ignore[arg-type]
    )


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
    valid_dates = set(pd.to_datetime(unique_dates[min(train_cut, n_dates) : min(valid_cut, n_dates)]))

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
    parser = argparse.ArgumentParser(description="Build sequence dataset and save Parquet splits.")
    parser.add_argument("--config-file", default="", help="JSON/TOML config file path (args mapping)")
    parser.add_argument(
        "--effective-config-out",
        default="",
        help="optional: save effective merged config (after CLI overrides) to JSON",
    )
    parser.add_argument("--start", required=True, help="Start date YYYYMMDD")
    parser.add_argument("--end", required=True, help="End date YYYYMMDD")
    parser.add_argument("--symbols", help="Comma-separated symbols, e.g. 600519,000333")
    parser.add_argument("--symbols-csv", help="CSV file containing symbols (column: symbol/code/ts_code)")
    parser.add_argument("--stock-pool-id", default="", help="从 registry 读取股票池成员")
    parser.add_argument("--stock-pool-version", default="", help="股票池版本，留空则要求 registry 内仅有单版本")
    parser.add_argument("--stock-pool-registry-dir", default="inputs/pools", help="股票池 registry 目录")
    parser.add_argument("--stock-pool-export-dir", default="output/stock_pools", help="导出的股票池产物目录")
    parser.add_argument(
        "--source",
        default="akshare",
        choices=["akshare", "tushare", "odp"],
        help="Data source",
    )
    parser.add_argument("--cache-dir", default="inputs/data/cache", help="Cache dir for daily bars")
    parser.add_argument("--output-dir", default="data/datasets", help="Output dir for parquet files")
    parser.add_argument("--seq-len", type=int, default=20, help="Sequence length (default: 20)")
    parser.add_argument("--stride", type=int, default=1, help="Sliding window stride (default: 1)")
    parser.add_argument("--valid-weeks", type=int, default=26, help="Validation weeks in fixed split mode")
    parser.add_argument("--test-weeks", type=int, default=26, help="Test weeks in fixed split mode")
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=None,
        help="Deprecated: train ratio for ratio split mode",
    )
    parser.add_argument(
        "--valid-ratio",
        type=float,
        default=None,
        help="Deprecated: valid ratio for ratio split mode",
    )
    parser.add_argument(
        "--horizons",
        default="3,5,10",
        help="Label horizons in days (default: 3,5,10)",
    )
    parser.add_argument(
        "--label-mode",
        default="close_to_close",
        choices=["close_to_close", "next_open_to_open"],
        help="Label calculation mode (default: close_to_close for backward compatibility)",
    )
    parser.add_argument(
        "--include-1d-hlc-labels",
        action="store_true",
        help="append 1-day high/low/close labels: label_1d_high,label_1d_low,label_1d_close",
    )
    pre_args, _ = parser.parse_known_args()
    config_section_used: str | None = None
    if pre_args.config_file:
        allowed_keys = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        overrides, config_section_used = extract_arg_overrides(
            config_path=pre_args.config_file,
            allowed_keys=allowed_keys,
            section_candidates=(CONFIG_SECTION_NAME, "build_dataset", "dataset"),
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
        effective_config_path = str(Path(args.output_dir) / "build_sequence_dataset_effective_config.json")

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
        logger.info(f"Saved effective config: {saved}")

    symbols, stock_pool_context = _resolve_symbols_input(
        symbols=args.symbols,
        symbols_csv=args.symbols_csv,
        stock_pool_id=str(args.stock_pool_id),
        stock_pool_version=str(args.stock_pool_version),
        stock_pool_registry_dir=str(args.stock_pool_registry_dir),
        stock_pool_export_dir=str(args.stock_pool_export_dir),
    )
    cache_dir = Path(args.cache_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    horizons = tuple(int(x.strip()) for x in str(args.horizons).split(",") if x.strip())
    if len(horizons) == 0:
        raise ValueError("--horizons is empty")

    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Date range: {args.start} ~ {args.end}")
    logger.info(f"seq_len={args.seq_len}, stride={args.stride}, horizons={horizons}")
    logger.info(f"label_mode={args.label_mode}")
    logger.info(f"include_1d_hlc_labels={bool(args.include_1d_hlc_labels)}")

    feature_frames: list[pd.DataFrame] = []
    label_frames: list[pd.DataFrame] = []

    for symbol in symbols:
        bars = _load_bars(args.source, symbol, args.start, args.end, cache_dir)
        if bars.empty:
            logger.warning(f"{symbol}: empty bars, skip")
            continue

        feats = _compute_features(bars)
        labs = _compute_labels(
            bars,
            horizons=horizons,
            label_mode=args.label_mode,
            include_1d_hlc_labels=bool(args.include_1d_hlc_labels),
        )

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

    dates = pd.to_datetime(meta["date"])
    use_ratio = args.train_ratio is not None or args.valid_ratio is not None
    if use_ratio:
        if args.train_ratio is None or args.valid_ratio is None:
            raise ValueError("ratio mode requires both --train-ratio and --valid-ratio")
        logger.warning("ratio split mode is deprecated; please use --valid-weeks/--test-weeks")
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

    # 保存元数据
    metadata = {
        "dataset_config": {
            "source": args.source,
            "symbols": symbols,
            "num_symbols": len(symbols),
            "start_date": args.start,
            "end_date": args.end,
            "stock_pool_id": stock_pool_context["stock_pool_id"],
            "stock_pool_version": stock_pool_context["stock_pool_version"],
            "symbols_csv": stock_pool_context["symbols_csv"],
            "stock_pool_registry_path": stock_pool_context["registry_path"],
            "cache_dir": str(cache_dir),
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
            "seq_len": args.seq_len,
            "stride": args.stride,
            "num_features": X.shape[2],
            "feature_names": builder.feature_columns_ or list(features_all.columns),
        },
        "split_config": split_config,
        "label_statistics": {
            col: {
                "valid_ratio": float(y_df[col].notna().mean()),
                "mean": float(y_df[col].mean(skipna=True)),
                "std": float(y_df[col].std(skipna=True)),
            }
            for col in y_cols
        },
    }
    metadata["dataset_id"] = infer_dataset_id(
        dataset_dir=output_dir,
        dataset_metadata=metadata,
        dataset_id="",
        stock_pool_id=stock_pool_context["stock_pool_id"] or f"custom_symbols{len(symbols)}",
    )

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"Metadata saved: {metadata_path}")


if __name__ == "__main__":
    main()
