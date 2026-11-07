#!/usr/bin/env python3
"""Rolling retrain + horizon-wise sign calibration for XGBoost baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ashare_lab.dataset.preprocessing import (
    FeatureQualityReport,
    RobustScaleConfig,
    RollingRobustScaler,
    screen_feature_rows,
)
from ashare_lab.features.contract import FeatureContract, FeatureContractLoader
from ashare_lab.evaluation.metrics import (
    information_coefficient,
    mean_absolute_error,
    rank_information_coefficient,
)
from ashare_lab.evaluation.trade_like_panel import build_primary_trade_like_comparison_panel
from ashare_lab.models.artifact_manifest import build_model_artifact_manifest
from ashare_lab.trend_schema import PRIMARY_TREND_LABEL_COLS, PRIMARY_TREND_PRED_COLS

try:
    from scripts.config_io import dump_json, extract_arg_overrides
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config_io import dump_json, extract_arg_overrides
try:
    from scripts.runtime_metadata import (
        PARSER_CONFIG_STATUS_CHOICES,
        build_default_report_path,
        build_effective_config_payload,
        resolve_experiment_context,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from runtime_metadata import (
        PARSER_CONFIG_STATUS_CHOICES,
        build_default_report_path,
        build_effective_config_payload,
        resolve_experiment_context,
    )
try:
    from scripts.env_guard import ensure_required_conda_env
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from env_guard import ensure_required_conda_env

LABEL_COLS = list(PRIMARY_TREND_LABEL_COLS)
PRED_COLS = list(PRIMARY_TREND_PRED_COLS)
FEATURE_MODES = ("contract", "auto")  # auto is a deprecated alias for contract.
XGB_DEVICES = ("cpu", "cuda")
CONFIG_SECTION_NAME = "run_xgboost_rolling_retrain_regime"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _build_evaluation_protocol(label_mode: str) -> dict[str, str]:
    return {
        "signal_time_mode": "close",
        "execution_time_mode": "next_open",
        "label_mode": str(label_mode),
        "return_mode": str(label_mode),
        "cost_model": "none",
        "daily_cs_mode": "required",
    }


def _build_comparison_panel(oos: pd.DataFrame, *, top_n: int) -> dict[str, object]:
    return build_primary_trade_like_comparison_panel(oos, top_n=top_n)


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


def _load_dataset_metadata(dataset_dir: Path) -> dict[str, object]:
    meta_path = dataset_dir / "metadata.json"
    if not meta_path.exists():
        raise ValueError(f"dataset metadata is required: {meta_path}")
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid dataset metadata JSON: {meta_path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"dataset metadata must be a JSON object: {meta_path}")
    return data


def _load_label_mode(dataset_dir: Path) -> str:
    data = _load_dataset_metadata(dataset_dir)
    mode = str(data.get("label_config", {}).get("label_mode", "")).strip()
    if mode not in {"close_to_close", "next_open_to_open"}:
        raise ValueError(f"dataset metadata has unsupported label_mode: {mode!r}")
    return mode


def _load_dataset_feature_contract(
    dataset_dir: Path, *, feature_contract_path: str = ""
) -> FeatureContract:
    metadata = _load_dataset_metadata(dataset_dir)
    expected = FeatureContractLoader.load(feature_contract_path) if feature_contract_path.strip() else None
    contract = FeatureContractLoader.from_dataset_metadata(metadata, expected_contract=expected)
    FeatureContractLoader.validate_dataset_feature_layout(metadata, contract)
    return contract


def _xgb_architecture(cfg: "XgbConfig", *, input_dim: int, seq_len: int) -> dict[str, object]:
    return {
        "input_dim": int(input_dim),
        "flat_input_dim": int(input_dim * seq_len),
        "seq_len": int(seq_len),
        "n_estimators": int(cfg.n_estimators),
        "max_depth": int(cfg.max_depth),
        "learning_rate": float(cfg.learning_rate),
        "subsample": float(cfg.subsample),
        "colsample_bytree": float(cfg.colsample_bytree),
        "min_child_weight": float(cfg.min_child_weight),
        "gamma": float(cfg.gamma),
        "reg_alpha": float(cfg.reg_alpha),
        "reg_lambda": float(cfg.reg_lambda),
        "n_jobs": int(cfg.n_jobs),
        "early_stopping_rounds": int(cfg.early_stopping_rounds),
        "device": cfg.device,
    }


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
    y = df[LABEL_COLS].to_numpy(dtype=np.float32, copy=False)
    return x, y


def _screen_feature_partition(
    df: pd.DataFrame,
    *,
    feature_bases: list[str],
    seq_len: int,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, FeatureQualityReport]:
    """Drop non-finite feature sequences before fitting or scoring XGBoost."""

    x_flat, y = _extract_xy_flat(df, feature_bases, seq_len)
    x_sequence = x_flat.reshape(len(df), seq_len, len(feature_bases))
    keep_mask, quality = screen_feature_rows(x_sequence, feature_bases)
    clean_df = df.loc[keep_mask].reset_index(drop=True)
    return clean_df, x_sequence[keep_mask], y[keep_mask], quality


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XGBoost rolling retrain + horizon sign calibration.")
    parser.add_argument("--config-file", default="", help="JSON/TOML config file path (args mapping)")
    parser.add_argument(
        "--effective-config-out",
        default="",
        help="optional: save effective merged config (after CLI overrides) to JSON",
    )
    parser.add_argument("--dataset-dir", default="workspace/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts")
    parser.add_argument(
        "--seq-len",
        type=int,
        default=None,
        help="deprecated consistency assertion; dataset Feature Contract owns seq_len",
    )
    parser.add_argument(
        "--feature-mode",
        choices=list(FEATURE_MODES),
        default="contract",
        help="contract: use ordered dataset Feature Contract; auto is a deprecated alias",
    )
    parser.add_argument(
        "--feature-contract",
        default="",
        help="optional Feature Contract TOML pin; must exactly match dataset metadata",
    )
    parser.add_argument(
        "--feature-clip-lower",
        type=float,
        default=0.005,
        help="训练窗口特征 winsorize 下分位数（仅 fit 于训练集）",
    )
    parser.add_argument(
        "--feature-clip-upper",
        type=float,
        default=0.995,
        help="训练窗口特征 winsorize 上分位数（仅 fit 于训练集）",
    )
    parser.add_argument(
        "--feature-scale-epsilon",
        type=float,
        default=1e-6,
        help="鲁棒尺度下限；更小的常量特征按零中心、单位尺度处理",
    )
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
    parser.add_argument("--model-track", default="mainline_3510d", help="模型线标识，默认 mainline_3510d")
    parser.add_argument(
        "--config-profile",
        default="xgb_rolling_baseline",
        help="当前配置档位名称，写入报告与 effective_config",
    )
    parser.add_argument(
        "--config-status",
        choices=list(PARSER_CONFIG_STATUS_CHOICES),
        default="baseline",
        help="当前配置状态：baseline / candidate / frozen（兼容 candidate-best / frozen-best）",
    )
    parser.add_argument("--stock-pool-id", default="", help="股票池 ID，默认由数据集 metadata 推断")
    parser.add_argument("--stock-pool-version", default="", help="股票池版本，默认由数据集 metadata 或 v1 推断")
    parser.add_argument(
        "--evaluation-window-id",
        default="",
        help="评估窗口 ID，默认 fixed_20230101_20250701",
    )
    parser.add_argument("--dataset-id", default="", help="数据集 ID，默认由数据集 metadata 推断")
    parser.add_argument(
        "--save-oos-parquet",
        default="",
        help="可选：保存 OOS 逐样本预测（含 raw/cal）到 parquet，用于 daily-CS 统一评估",
    )
    parser.add_argument(
        "--comparison-top-n",
        type=int,
        default=10,
        help="主线比较面板按 alpha_score 取前 N 名做等权交易近似评估",
    )
    parser.add_argument(
        "--report",
        default="",
    )
    return parser


def _argparse_allowed_keys(parser: argparse.ArgumentParser) -> set[str]:
    return {a.dest for a in parser._actions if a.dest != "help"}


def main() -> None:
    ensure_required_conda_env("py311-private")
    parser = _build_parser()
    pre_args, _ = parser.parse_known_args()
    config_section_used: str | None = None
    if pre_args.config_file:
        allowed_keys = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        overrides, config_section_used = extract_arg_overrides(
            config_path=pre_args.config_file,
            allowed_keys=allowed_keys,
            section_candidates=(CONFIG_SECTION_NAME, "xgb"),
        )
        parser.set_defaults(**overrides)
    args = parser.parse_args()
    config_file_resolved = (
        str(Path(args.config_file).resolve()) if str(args.config_file).strip() else ""
    )

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
    feature_scale_config = RobustScaleConfig(
        lower_clip_quantile=float(args.feature_clip_lower),
        upper_clip_quantile=float(args.feature_clip_upper),
        min_scale=float(args.feature_scale_epsilon),
    )
    ddir = Path(args.dataset_dir)
    feature_contract = _load_dataset_feature_contract(
        ddir, feature_contract_path=str(args.feature_contract)
    )
    if args.seq_len is not None and int(args.seq_len) != feature_contract.seq_len:
        raise ValueError(
            f"--seq-len={args.seq_len} conflicts with dataset Feature Contract seq_len="
            f"{feature_contract.seq_len}"
        )
    seq_len = feature_contract.seq_len

    resolved_context = resolve_experiment_context(
        dataset_dir=args.dataset_dir,
        model_track=str(args.model_track),
        config_profile=str(args.config_profile),
        config_status=str(args.config_status),
        stock_pool_id=str(args.stock_pool_id),
        stock_pool_version=str(args.stock_pool_version),
        evaluation_window_id=str(args.evaluation_window_id),
        dataset_id=str(args.dataset_id),
    )
    run_started_at = datetime.now().astimezone()
    report_path = (
        Path(args.report)
        if str(args.report).strip()
        else build_default_report_path(
            backbone="xgb",
            model_track=resolved_context["model_track"],
            config_profile=resolved_context["config_profile"],
            generated_at=run_started_at,
        )
    )

    effective_config_path = ""
    effective_config_out = str(args.effective_config_out).strip()
    if effective_config_out:
        effective_config_path = effective_config_out
    elif config_file_resolved:
        effective_config_path = str(
            report_path.with_name(f"{report_path.stem}_effective_config.json")
        )

    if effective_config_path:
        allowed_effective = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        effective_args = {k: getattr(args, k) for k in sorted(allowed_effective)}
        saved = dump_json(
            effective_config_path,
            build_effective_config_payload(
                context=resolved_context,
                seed=int(args.seed),
                script=CONFIG_SECTION_NAME,
                config_file=config_file_resolved,
                generated_at=run_started_at,
                args_mapping=effective_args,
            ),
        )
        print(f"Saved effective config: {saved}")

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

    feature_bases = list(feature_contract.feature_names)

    required_x = [f"{b}_t{t}" for t in range(seq_len) for b in feature_bases]
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

        tr_df, x_tr_seq, y_tr, train_feature_quality = _screen_feature_partition(
            tr_df,
            feature_bases=feature_bases,
            seq_len=seq_len,
        )
        va_df, x_va_seq, y_va, valid_feature_quality = _screen_feature_partition(
            va_df,
            feature_bases=feature_bases,
            seq_len=seq_len,
        )
        week_df, x_wk_seq, y_wk, oos_feature_quality = _screen_feature_partition(
            week_df,
            feature_bases=feature_bases,
            seq_len=seq_len,
        )
        if tr_df.empty or va_df.empty or week_df.empty:
            raise RuntimeError(
                "feature quality screening emptied train, validation, or OOS partition "
                f"for week {week}"
            )

        scaler = RollingRobustScaler(feature_bases, config=feature_scale_config)
        x_tr_seq = scaler.fit_transform(x_tr_seq)
        x_va_seq = scaler.transform(x_va_seq)
        x_wk_seq = scaler.transform(x_wk_seq)
        feature_contract.assert_sequence_shape(x_tr_seq.shape, context=f"train features for week {week}")
        feature_contract.assert_sequence_shape(x_va_seq.shape, context=f"validation features for week {week}")
        feature_contract.assert_sequence_shape(x_wk_seq.shape, context=f"OOS features for week {week}")
        x_tr = x_tr_seq.reshape(len(tr_df), -1)
        x_va = x_va_seq.reshape(len(va_df), -1)
        x_wk = x_wk_seq.reshape(len(week_df), -1)
        flat_input_dim = feature_contract.seq_len * feature_contract.input_dim
        if any(array.shape[1] != flat_input_dim for array in (x_tr, x_va, x_wk)):
            raise RuntimeError(
                f"XGBoost flattened input dimension must be {flat_input_dim} from Feature Contract"
            )
        preprocessing_state = scaler.to_dict()
        artifact_manifest = build_model_artifact_manifest(
            model_family="xgboost",
            architecture=_xgb_architecture(
                cfg, input_dim=feature_contract.input_dim, seq_len=feature_contract.seq_len
            ),
            contract=feature_contract,
            label_mode=label_mode,
            preprocessing={
                "missing_value_policy": feature_contract.missing_value_policy,
                "scaler": preprocessing_state,
            },
            dataset_id=resolved_context["dataset_id"],
        )

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
                "feature_quality": {
                    "train": train_feature_quality.to_dict(),
                    "valid": valid_feature_quality.to_dict(),
                    "oos": oos_feature_quality.to_dict(),
                },
                "preprocessing": preprocessing_state,
                "model_artifact_manifest": artifact_manifest,
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
    evaluation_protocol = _build_evaluation_protocol(label_mode)
    comparison_panel = _build_comparison_panel(oos, top_n=int(args.comparison_top_n))

    out = {
        "experiment_metadata": build_effective_config_payload(
            context=resolved_context,
            seed=int(args.seed),
            script=CONFIG_SECTION_NAME,
            config_file=config_file_resolved,
            generated_at=run_started_at,
            args_mapping={},
        ),
        "config": {
            "dataset_dir": str(ddir),
            "backbone": "xgboost",
            "feature_mode": str(args.feature_mode),
            "features": feature_bases,
            "feature_contract_id": feature_contract.contract_id,
            "feature_contract_hash": feature_contract.contract_hash,
            "feature_names": list(feature_contract.feature_names),
            "input_dim": feature_contract.input_dim,
            "flat_input_dim": feature_contract.seq_len * feature_contract.input_dim,
            "seq_len": int(seq_len),
            "preprocessing_policy": {
                "method": "train_window_robust_clip_median_iqr",
                "lower_clip_quantile": feature_scale_config.lower_clip_quantile,
                "upper_clip_quantile": feature_scale_config.upper_clip_quantile,
                "min_scale": feature_scale_config.min_scale,
                "missing_value_policy": feature_contract.missing_value_policy,
                "nonfinite_feature_policy": "reject_nonfinite",
            },
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
            "model_track": resolved_context["model_track"],
            "config_profile": resolved_context["config_profile"],
            "config_status": resolved_context["config_status"],
            "stock_pool_id": resolved_context["stock_pool_id"],
            "stock_pool_version": resolved_context["stock_pool_version"],
            "evaluation_window_id": resolved_context["evaluation_window_id"],
            "dataset_id": resolved_context["dataset_id"],
            "comparison_top_n": int(args.comparison_top_n),
            "label_mode": str(label_mode),
            "maturity_gate_enabled": True,
            "maturity_gate_horizon_days": int(maturity_horizon_days),
            "maturity_gate_shift_days": int(maturity_shift_days),
            "retrain_weeks": [str(w) for w in retrain_weeks],
            "retrain_frequency": "weekly",
            "prediction_frequency": "daily",
            "retrain_week_freq": "W-FRI",
            "months": [str(m) for m in legacy_months],
            "config_file": config_file_resolved,
            "config_section": config_section_used,
            "effective_config_path": effective_config_path,
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
        "evaluation_protocol": evaluation_protocol,
        "comparison_panel": comparison_panel,
        "feature_contract": feature_contract.to_metadata(),
    }

    if args.save_oos_parquet:
        oos_path = Path(args.save_oos_parquet)
        oos_path.parent.mkdir(parents=True, exist_ok=True)
        oos.to_parquet(oos_path, index=False)
        out["oos_artifact"] = {
            "path": str(oos_path),
            "sha256": _sha256_file(oos_path),
            "rows": int(len(oos)),
            "columns": list(oos.columns),
            "dataset_id": resolved_context["dataset_id"],
            "feature_contract_hash": feature_contract.contract_hash,
        }
        out["oos_predictions_path"] = str(oos_path.resolve())
        print(f"Saved OOS parquet: {oos_path}")

    report = report_path
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved report: {report}")


if __name__ == "__main__":
    main()
