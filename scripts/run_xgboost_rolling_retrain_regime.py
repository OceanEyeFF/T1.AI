#!/usr/bin/env python3
"""Rolling retrain + horizon-wise sign calibration for XGBoost baseline."""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ashare_lab.evaluation.metrics import (
    information_coefficient,
    mean_absolute_error,
    rank_information_coefficient,
)

FEATURES_DIM19 = [
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "volume_ratio_5d",
    "relative_volume",
    "volume_change",
    "amount_change",
    "rsi_14",
    "macd_line",
    "macd_signal",
    "macd_hist",
    "bollinger_deviation",
    "price_slope_5d",
    "price_slope_20d",
    "market_mom_5d",
    "market_vol_20d",
    "market_amount_z20",
]

LABEL_COLS = ["label_3d", "label_5d", "label_10d"]
PRED_COLS = ["pred_3d", "pred_5d", "pred_10d"]
FEATURE_MODES = ("dim19", "auto")
XGB_DEVICES = ("cpu", "cuda")


def _months_to_weeks(months: int) -> int:
    return max(1, int(round(float(months) * 52.0 / 12.0)))


def _resolve_window_weeks(
    *,
    weeks: int | None,
    months: int | None,
    default_weeks: int,
    field_name: str,
) -> int:
    if weeks is not None:
        if weeks <= 0:
            raise ValueError(f"{field_name} must be > 0")
        return int(weeks)
    if months is not None:
        if months <= 0:
            raise ValueError(f"{field_name} legacy months input must be > 0")
        return _months_to_weeks(int(months))
    return int(default_weeks)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _metrics(pred: np.ndarray, y: np.ndarray) -> dict[str, float]:
    ic = [information_coefficient(pred[:, i], y[:, i]) for i in range(3)]
    ric = [rank_information_coefficient(pred[:, i], y[:, i]) for i in range(3)]
    mae = [mean_absolute_error(pred[:, i], y[:, i]) for i in range(3)]
    return {
        "ic_3d": float(ic[0]),
        "ic_5d": float(ic[1]),
        "ic_10d": float(ic[2]),
        "avg_ic": float(np.mean(ic)),
        "rank_ic_3d": float(ric[0]),
        "rank_ic_5d": float(ric[1]),
        "rank_ic_10d": float(ric[2]),
        "avg_rank_ic": float(np.mean(ric)),
        "mae_3d": float(mae[0]),
        "mae_5d": float(mae[1]),
        "mae_10d": float(mae[2]),
        "avg_mae": float(np.mean(mae)),
    }


def _infer_feature_bases(df: pd.DataFrame, seq_len: int) -> list[str]:
    bases: list[str] = []
    seen: set[str] = set()
    for col in df.columns:
        if not col.endswith("_t0"):
            continue
        base = col[:-3]
        if not base or base in seen:
            continue
        required = [f"{base}_t{t}" for t in range(seq_len)]
        if all(c in df.columns for c in required):
            bases.append(base)
            seen.add(base)
    if not bases:
        raise ValueError("no feature columns inferred from dataset (expected pattern '*_t0')")
    return bases


def _infer_max_horizon_days(label_cols: list[str]) -> int:
    horizons: list[int] = []
    for col in label_cols:
        m = re.fullmatch(r"label_(\d+)d", str(col))
        if m is not None:
            horizons.append(int(m.group(1)))
    if not horizons:
        raise ValueError("failed to infer horizon days from LABEL_COLS")
    return int(max(horizons))


def _load_label_mode(dataset_dir: Path) -> str:
    meta_path = dataset_dir / "metadata.json"
    if not meta_path.exists():
        return "close_to_close"
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return "close_to_close"
    mode = str(data.get("label_config", {}).get("label_mode", "close_to_close"))
    if mode not in {"close_to_close", "next_open_to_open"}:
        return "close_to_close"
    return mode


def _label_mode_shift_days(label_mode: str) -> int:
    if label_mode == "next_open_to_open":
        return 1
    return 0


def _attach_label_maturity_date(
    df: pd.DataFrame,
    *,
    horizon_days: int,
    shift_days: int,
    maturity_col: str = "label_maturity_date",
) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str)
    out = out.sort_values(["symbol", "date"]).reset_index(drop=True)
    steps = int(horizon_days + shift_days)
    if steps <= 0:
        raise ValueError("horizon_days + shift_days must be > 0")
    out[maturity_col] = out.groupby("symbol", sort=False)["date"].shift(-steps)
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


def _extract_xy_flat(df: pd.DataFrame, feature_bases: list[str], seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    x_cols = [f"{b}_t{t}" for t in range(seq_len) for b in feature_bases]
    x = df[x_cols].to_numpy(dtype=np.float32, copy=False)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    y = df[LABEL_COLS].to_numpy(dtype=np.float32, copy=False)
    return x, y


def _horizon_sign_with_threshold(score: float, threshold: float) -> int:
    if not np.isfinite(score):
        return 1
    if abs(score) < threshold:
        return 1
    return 1 if score >= 0 else -1


def _choose_sign_consensus(hist_ic: float, val_ic: float, threshold: float) -> tuple[int, str]:
    hist_ok = np.isfinite(hist_ic)
    val_ok = np.isfinite(val_ic)

    if hist_ok and val_ok:
        if abs(hist_ic) >= threshold and abs(val_ic) >= threshold and np.sign(hist_ic) == np.sign(val_ic):
            return (1 if hist_ic >= 0 else -1), "hist_val_consensus"
        return 1, "no_consensus_or_low_conf"

    if hist_ok:
        return _horizon_sign_with_threshold(hist_ic, threshold), "hist_only"
    if val_ok:
        return _horizon_sign_with_threshold(val_ic, threshold), "val_only"
    return 1, "no_signal"


def _select_train_valid_for_month(
    train_pool: pd.DataFrame,
    month_start: pd.Timestamp,
    *,
    train_window_weeks: int,
    valid_window_weeks: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    left = month_start - pd.DateOffset(weeks=train_window_weeks)
    pool_raw = train_pool[(train_pool["date"] >= left) & (train_pool["date"] < month_start)].copy()
    pool = pool_raw[
        pool_raw["label_maturity_date"].notna() & (pool_raw["label_maturity_date"] < month_start)
    ].copy()
    split_stats = {
        "pool_rows_before_maturity": int(len(pool_raw)),
        "pool_rows_after_maturity": int(len(pool)),
    }
    if pool.empty:
        raise RuntimeError(f"empty rolling pool before {month_start.date()} after maturity filter")

    valid_left = month_start - pd.DateOffset(weeks=valid_window_weeks)
    valid_df = pool[(pool["date"] >= valid_left) & (pool["date"] < month_start)].copy()
    train_df = pool[pool["date"] < valid_left].copy()

    if train_df.empty or valid_df.empty:
        ud = np.array(sorted(pool["date"].unique()))
        cut = max(1, int(len(ud) * 0.85))
        train_dates = set(pd.to_datetime(ud[:cut]))
        valid_dates = set(pd.to_datetime(ud[cut:]))
        train_df = pool[pool["date"].isin(train_dates)].copy()
        valid_df = pool[pool["date"].isin(valid_dates)].copy()
        if train_df.empty or valid_df.empty:
            raise RuntimeError(f"unable to split train/valid before {month_start.date()}")

    return train_df, valid_df, split_stats


@dataclass(frozen=True)
class XgbConfig:
    n_estimators: int
    max_depth: int
    learning_rate: float
    subsample: float
    colsample_bytree: float
    min_child_weight: float
    gamma: float
    reg_alpha: float
    reg_lambda: float
    n_jobs: int
    early_stopping_rounds: int
    device: str
    random_seed: int


def _build_xgb_regressor(cfg: XgbConfig, seed: int) -> xgb.XGBRegressor:
    return xgb.XGBRegressor(
        n_estimators=cfg.n_estimators,
        max_depth=cfg.max_depth,
        learning_rate=cfg.learning_rate,
        subsample=cfg.subsample,
        colsample_bytree=cfg.colsample_bytree,
        min_child_weight=cfg.min_child_weight,
        gamma=cfg.gamma,
        reg_alpha=cfg.reg_alpha,
        reg_lambda=cfg.reg_lambda,
        objective="reg:squarederror",
        tree_method="hist",
        device=cfg.device,
        random_state=seed,
        n_jobs=cfg.n_jobs,
        eval_metric="mae",
        early_stopping_rounds=(cfg.early_stopping_rounds if cfg.early_stopping_rounds > 0 else None),
    )


def _fit_predict_multihorizon(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    x_test: np.ndarray,
    cfg: XgbConfig,
    month_seed: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, float | int | None]], float]:
    models: list[xgb.XGBRegressor | None] = [None, None, None]
    val_pred = np.zeros((x_valid.shape[0], 3), dtype=np.float32)
    test_pred = np.zeros((x_test.shape[0], 3), dtype=np.float32)
    head_logs: list[dict[str, float | int | None]] = []
    t0 = time.perf_counter()

    for h in range(3):
        ytr = y_train[:, h]
        yva = y_valid[:, h]
        mask_tr = np.isfinite(ytr)
        mask_va = np.isfinite(yva)
        train_count = int(mask_tr.sum())
        valid_count = int(mask_va.sum())

        if train_count < 32:
            head_logs.append(
                {
                    "horizon": int([3, 5, 10][h]),
                    "train_count": train_count,
                    "valid_count": valid_count,
                    "best_iteration": None,
                }
            )
            continue

        model = _build_xgb_regressor(cfg, seed=month_seed + h)
        fit_kwargs: dict[str, object] = {
            "X": x_train[mask_tr],
            "y": ytr[mask_tr],
            "verbose": False,
        }
        if valid_count >= 16:
            fit_kwargs["eval_set"] = [(x_valid[mask_va], yva[mask_va])]
        model.fit(**fit_kwargs)
        models[h] = model

        if valid_count > 0:
            pred = model.predict(x_valid)
            val_pred[:, h] = pred.astype(np.float32, copy=False)
        test_pred[:, h] = model.predict(x_test).astype(np.float32, copy=False)

        best_it = getattr(model, "best_iteration", None)
        head_logs.append(
            {
                "horizon": int([3, 5, 10][h]),
                "train_count": train_count,
                "valid_count": valid_count,
                "best_iteration": (None if best_it is None else int(best_it)),
            }
        )

    return val_pred, test_pred, head_logs, float(time.perf_counter() - t0)


def main() -> None:
    parser = argparse.ArgumentParser(description="XGBoost rolling retrain + horizon sign calibration.")
    parser.add_argument("--dataset-dir", default="data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--feature-mode", choices=list(FEATURE_MODES), default="auto")
    parser.add_argument("--train-window-weeks", type=int, default=None, help="训练窗口（周），默认 104")
    parser.add_argument("--valid-window-weeks", type=int, default=None, help="验证窗口（周），默认 8")
    parser.add_argument("--calibration-weeks", type=int, default=None, help="校准窗口（周），默认 12")
    parser.add_argument(
        "--train-window-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：训练窗口（月）",
    )
    parser.add_argument(
        "--valid-window-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：验证窗口（月）",
    )
    parser.add_argument(
        "--calibration-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：校准窗口（月）",
    )
    parser.add_argument("--sign-threshold", type=float, default=0.02)

    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--subsample", type=float, default=0.8)
    parser.add_argument("--colsample-bytree", type=float, default=0.8)
    parser.add_argument("--min-child-weight", type=float, default=1.0)
    parser.add_argument("--gamma", type=float, default=0.0)
    parser.add_argument("--reg-alpha", type=float, default=0.0)
    parser.add_argument("--reg-lambda", type=float, default=1.0)
    parser.add_argument("--n-jobs", type=int, default=8)
    parser.add_argument("--early-stopping-rounds", type=int, default=40)
    parser.add_argument("--device", choices=list(XGB_DEVICES), default="cpu")

    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--save-oos-parquet",
        default="",
        help="可选：保存 OOS 逐样本预测（含 raw/cal）到 parquet，用于 daily-CS 统一评估",
    )
    parser.add_argument(
        "--report",
        default="output/reports/xgboost_dim52_auto_window104w_seq20_20260305.json",
    )
    args = parser.parse_args()

    train_window_weeks = _resolve_window_weeks(
        weeks=args.train_window_weeks,
        months=args.train_window_months,
        default_weeks=104,
        field_name="train_window_weeks",
    )
    valid_window_weeks = _resolve_window_weeks(
        weeks=args.valid_window_weeks,
        months=args.valid_window_months,
        default_weeks=8,
        field_name="valid_window_weeks",
    )
    calibration_weeks = _resolve_window_weeks(
        weeks=args.calibration_weeks,
        months=args.calibration_months,
        default_weeks=12,
        field_name="calibration_weeks",
    )

    if args.n_estimators <= 0:
        raise ValueError("n_estimators must be > 0")
    if args.max_depth <= 0:
        raise ValueError("max_depth must be > 0")
    if args.learning_rate <= 0:
        raise ValueError("learning_rate must be > 0")
    if not (0 < args.subsample <= 1.0):
        raise ValueError("subsample must be in (0,1]")
    if not (0 < args.colsample_bytree <= 1.0):
        raise ValueError("colsample_bytree must be in (0,1]")
    if args.min_child_weight < 0:
        raise ValueError("min_child_weight must be >= 0")
    if args.gamma < 0:
        raise ValueError("gamma must be >= 0")
    if args.reg_alpha < 0 or args.reg_lambda < 0:
        raise ValueError("reg_alpha/reg_lambda must be >= 0")
    if args.n_jobs == 0:
        raise ValueError("n_jobs cannot be 0")

    _set_seed(args.seed)
    cfg = XgbConfig(
        n_estimators=int(args.n_estimators),
        max_depth=int(args.max_depth),
        learning_rate=float(args.learning_rate),
        subsample=float(args.subsample),
        colsample_bytree=float(args.colsample_bytree),
        min_child_weight=float(args.min_child_weight),
        gamma=float(args.gamma),
        reg_alpha=float(args.reg_alpha),
        reg_lambda=float(args.reg_lambda),
        n_jobs=int(args.n_jobs),
        early_stopping_rounds=int(args.early_stopping_rounds),
        device=str(args.device),
        random_seed=int(args.seed),
    )

    ddir = Path(args.dataset_dir)
    train_df = pd.read_parquet(ddir / "train.parquet")
    valid_df = pd.read_parquet(ddir / "valid.parquet")
    test_df = pd.read_parquet(ddir / "test.parquet")
    full_df = pd.concat([train_df, valid_df, test_df], ignore_index=True)
    full_df["date"] = pd.to_datetime(full_df["date"])
    full_df["symbol"] = full_df["symbol"].astype(str)
    full_df = full_df.sort_values(["date", "symbol"]).reset_index(drop=True)
    label_mode = _load_label_mode(ddir)
    maturity_horizon_days = _infer_max_horizon_days(LABEL_COLS)
    maturity_shift_days = _label_mode_shift_days(label_mode)
    full_df = _attach_label_maturity_date(
        full_df,
        horizon_days=maturity_horizon_days,
        shift_days=maturity_shift_days,
    )

    if args.feature_mode == "dim19":
        feature_bases = list(FEATURES_DIM19)
    else:
        feature_bases = _infer_feature_bases(train_df, args.seq_len)

    required_x = [f"{b}_t{t}" for t in range(args.seq_len) for b in feature_bases]
    missing_x = [c for c in required_x if c not in full_df.columns]
    if missing_x:
        preview = ", ".join(missing_x[:5])
        raise ValueError(f"dataset missing required feature columns (showing up to 5): {preview}")

    eval_df = test_df.copy()
    eval_df["date"] = pd.to_datetime(eval_df["date"])
    eval_df["symbol"] = eval_df["symbol"].astype(str)
    eval_df = eval_df.sort_values(["date", "symbol"]).reset_index(drop=True)
    retrain_weeks = sorted(eval_df["date"].dt.to_period("W-FRI").unique())
    legacy_months = sorted(eval_df["date"].dt.to_period("M").unique())

    hist_rows: list[pd.DataFrame] = []
    oos_rows: list[pd.DataFrame] = []
    week_logs: list[dict[str, object]] = []

    for i, w in enumerate(retrain_weeks):
        week = str(w)
        week_mask = eval_df["date"].dt.to_period("W-FRI") == w
        week_df = eval_df.loc[week_mask].copy()
        if week_df.empty:
            continue
        week_start = week_df["date"].min()
        week_end = week_df["date"].max()

        print(f"\n=== week {week} ({week_start.date()}..{week_end.date()}) ===")
        tr_df, va_df, split_stats = _select_train_valid_for_month(
            full_df,
            month_start=week_start,
            train_window_weeks=train_window_weeks,
            valid_window_weeks=valid_window_weeks,
        )
        print(
            f"train_rows={len(tr_df)} valid_rows={len(va_df)} week_rows={len(week_df)} "
            f"train_range=[{tr_df['date'].min().date()}..{tr_df['date'].max().date()}] "
            f"pool_before={split_stats['pool_rows_before_maturity']} "
            f"pool_after={split_stats['pool_rows_after_maturity']}"
        )

        month_seed = int(args.seed + i)
        _set_seed(month_seed)

        x_tr, y_tr = _extract_xy_flat(tr_df, feature_bases, args.seq_len)
        x_va, y_va = _extract_xy_flat(va_df, feature_bases, args.seq_len)
        x_wk, y_wk = _extract_xy_flat(week_df, feature_bases, args.seq_len)

        pred_val, pred_month, head_logs, train_seconds = _fit_predict_multihorizon(
            x_tr, y_tr, x_va, y_va, x_wk, cfg, month_seed
        )
        val_metrics = _metrics(pred_val, y_va)

        hist_df = pd.concat(hist_rows, ignore_index=True) if hist_rows else pd.DataFrame()
        hist_rows_before_maturity = 0
        hist_rows_after_maturity = 0
        if not hist_df.empty:
            hist_df["date"] = pd.to_datetime(hist_df["date"])
            hist_df["symbol"] = hist_df["symbol"].astype(str)
            hist_df = _attach_label_maturity_date(
                hist_df,
                horizon_days=maturity_horizon_days,
                shift_days=maturity_shift_days,
            )
            hist_left = week_start - pd.DateOffset(weeks=calibration_weeks)
            hist_window = hist_df[(hist_df["date"] >= hist_left) & (hist_df["date"] < week_start)].copy()
            hist_rows_before_maturity = int(len(hist_window))
            hist_use = hist_window[
                hist_window["label_maturity_date"].notna() & (hist_window["label_maturity_date"] < week_start)
            ].copy()
            hist_rows_after_maturity = int(len(hist_use))
        else:
            hist_use = pd.DataFrame()

        signs: list[int] = []
        decisions: list[dict[str, float | int]] = []
        for h in range(3):
            val_ic = float(information_coefficient(pred_val[:, h], y_va[:, h]))
            hist_ic = float("nan")
            if not hist_use.empty:
                hist_ic = float(
                    information_coefficient(
                        hist_use[PRED_COLS[h]].to_numpy(dtype=float, copy=False),
                        hist_use[LABEL_COLS[h]].to_numpy(dtype=float, copy=False),
                    )
                )
            score = hist_ic if np.isfinite(hist_ic) else val_ic
            sign, reason = _choose_sign_consensus(hist_ic, val_ic, args.sign_threshold)
            signs.append(sign)
            decisions.append(
                {
                    "horizon": int([3, 5, 10][h]),
                    "val_ic": val_ic,
                    "hist_ic": hist_ic,
                    "score_used": float(score),
                    "sign": int(sign),
                    "rule": reason,
                }
            )

        pred_cal = pred_month.copy()
        for h in range(3):
            pred_cal[:, h] = signs[h] * pred_cal[:, h]

        week_raw = _metrics(pred_month, y_wk)
        week_cal = _metrics(pred_cal, y_wk)
        print(
            f"week_raw_avg_ic={week_raw['avg_ic']:.4f} week_cal_avg_ic={week_cal['avg_ic']:.4f} "
            f"signs={signs}"
        )

        month_out = week_df[["date", "symbol"] + LABEL_COLS].copy()
        for h, c in enumerate(PRED_COLS):
            month_out[c] = pred_month[:, h]
            month_out[f"{c}_cal"] = pred_cal[:, h]
        oos_rows.append(month_out)
        hist_rows.append(month_out[["date", "symbol"] + LABEL_COLS + PRED_COLS].copy())

        week_logs.append(
            {
                "week": week,
                "week_start": str(week_start.date()),
                "week_end": str(week_end.date()),
                "week_rows": int(len(week_df)),
                "train_rows": int(len(tr_df)),
                "valid_rows": int(len(va_df)),
                "pool_rows_before_maturity": int(split_stats["pool_rows_before_maturity"]),
                "pool_rows_after_maturity": int(split_stats["pool_rows_after_maturity"]),
                "hist_rows_before_maturity": int(hist_rows_before_maturity),
                "hist_rows_after_maturity": int(hist_rows_after_maturity),
                "epochs_ran": int(max((log["best_iteration"] or 0) + 1 for log in head_logs)),
                "train_seconds": float(train_seconds),
                "valid_avg_ic": float(val_metrics["avg_ic"]),
                "raw_avg_ic": float(week_raw["avg_ic"]),
                "cal_avg_ic": float(week_cal["avg_ic"]),
                "signs": signs,
                "decisions": decisions,
                "xgb_heads": head_logs,
            }
        )

    if not oos_rows:
        raise RuntimeError("no out-of-sample predictions generated")

    oos = pd.concat(oos_rows, ignore_index=True)
    y = oos[LABEL_COLS].to_numpy(dtype=float, copy=False)
    raw = oos[PRED_COLS].to_numpy(dtype=float, copy=False)
    cal = oos[[f"{c}_cal" for c in PRED_COLS]].to_numpy(dtype=float, copy=False)

    raw_metrics = _metrics(raw, y)
    cal_metrics = _metrics(cal, y)

    out = {
        "config": {
            "dataset_dir": str(ddir),
            "backbone": "xgboost",
            "feature_mode": str(args.feature_mode),
            "features": feature_bases,
            "seq_len": int(args.seq_len),
            "train_window_weeks": int(train_window_weeks),
            "valid_window_weeks": int(valid_window_weeks),
            "calibration_weeks": int(calibration_weeks),
            "window_unit": "week",
            "train_window_months_legacy_input": (
                None if args.train_window_months is None else int(args.train_window_months)
            ),
            "valid_window_months_legacy_input": (
                None if args.valid_window_months is None else int(args.valid_window_months)
            ),
            "calibration_months_legacy_input": (
                None if args.calibration_months is None else int(args.calibration_months)
            ),
            "sign_threshold": float(args.sign_threshold),
            "n_estimators": int(args.n_estimators),
            "max_depth": int(args.max_depth),
            "learning_rate": float(args.learning_rate),
            "subsample": float(args.subsample),
            "colsample_bytree": float(args.colsample_bytree),
            "min_child_weight": float(args.min_child_weight),
            "gamma": float(args.gamma),
            "reg_alpha": float(args.reg_alpha),
            "reg_lambda": float(args.reg_lambda),
            "n_jobs": int(args.n_jobs),
            "early_stopping_rounds": int(args.early_stopping_rounds),
            "device": str(args.device),
            "seed": int(args.seed),
            "label_mode": str(label_mode),
            "maturity_gate_enabled": True,
            "maturity_gate_horizon_days": int(maturity_horizon_days),
            "maturity_gate_shift_days": int(maturity_shift_days),
            "retrain_weeks": [str(w) for w in retrain_weeks],
            "retrain_frequency": "weekly",
            "prediction_frequency": "daily",
            "retrain_week_freq": "W-FRI",
            "months": [str(m) for m in legacy_months],
        },
        "raw_oos_metrics": raw_metrics,
        "calibrated_oos_metrics": cal_metrics,
        "delta_cal_minus_raw": {
            "avg_ic": float(cal_metrics["avg_ic"] - raw_metrics["avg_ic"]),
            "avg_rank_ic": float(cal_metrics["avg_rank_ic"] - raw_metrics["avg_rank_ic"]),
            "avg_mae": float(cal_metrics["avg_mae"] - raw_metrics["avg_mae"]),
        },
        "weekly_logs": week_logs,
        "monthly_logs": week_logs,
    }

    if args.save_oos_parquet:
        oos_path = Path(args.save_oos_parquet)
        oos_path.parent.mkdir(parents=True, exist_ok=True)
        oos.to_parquet(oos_path, index=False)
        out["oos_predictions_path"] = str(oos_path.resolve())
        print(f"Saved OOS parquet: {oos_path}")

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved report: {report}")


if __name__ == "__main__":
    main()
