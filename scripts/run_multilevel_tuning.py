#!/usr/bin/env python3
"""Run multi-level hyper-parameter tuning for LSTM/XGBoost rolling baselines.

Features:
1) Show current baseline config and input feature summary.
2) Generate L1/L2/L3 tuning experiments.
3) Optionally execute all runs.
4) Auto-run audit + IC comparison after each level.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.config_io import dump_json, extract_arg_overrides
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config_io import dump_json, extract_arg_overrides
try:
    from scripts.env_guard import ensure_required_conda_env
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from env_guard import ensure_required_conda_env


DEFAULT_LSTM_BASELINE = ""
DEFAULT_XGB_BASELINE = ""
DEFAULT_LSTM_CONFIG = "configs/experiments/lstm_rolling_baseline.toml"
DEFAULT_XGB_CONFIG = "configs/experiments/xgb_rolling_baseline.toml"

MODEL_CHOICES = ("lstm", "xgb", "both")
LEVEL_CHOICES = ("L1", "L2", "L3")
SECTION_BY_MODEL = {
    "lstm": "run_lstm_rolling_retrain_dim19_regime",
    "xgb": "run_xgboost_rolling_retrain_regime",
}


@dataclass(frozen=True)
class ExperimentSpec:
    model: str
    level: str
    name: str
    overrides: dict[str, Any]


def _fmt_value(value: Any) -> str:
    if isinstance(value, float):
        text = f"{value:.8g}"
        return text.replace(".", "p").replace("-", "m")
    if isinstance(value, (tuple, list)):
        return "_".join(_fmt_value(v) for v in value)
    return str(value).replace(".", "p").replace("-", "m")


def _sanitize_name(text: str) -> str:
    keep = []
    for ch in text:
        if ch.isalnum() or ch in ("_", "-"):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("_")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _features_preview(features: list[str], n: int = 12) -> str:
    if not features:
        return "(none)"
    head = features[:n]
    tail = "" if len(features) <= n else f" ... (+{len(features) - n} more)"
    return ", ".join(head) + tail


def _as_float_triplet(weights: dict[str, Any] | None) -> tuple[float, float, float]:
    if not isinstance(weights, dict):
        return 1.0, 1.0, 1.0
    return (
        float(weights.get("3d", 1.0)),
        float(weights.get("5d", 1.0)),
        float(weights.get("10d", 1.0)),
    )


def _snapshot_lstm(config: dict[str, Any]) -> dict[str, Any]:
    if isinstance(config.get("loss_weights"), dict):
        w3, w5, w10 = _as_float_triplet(config.get("loss_weights"))
    else:
        w3 = float(config.get("w3", 1.0))
        w5 = float(config.get("w5", 1.0))
        w10 = float(config.get("w10", 1.0))
    return {
        "dataset_dir": str(config.get("dataset_dir", "")),
        "feature_mode": str(config.get("feature_mode", "")),
        "feature_count": int(len(config.get("features", []))),
        "features": list(config.get("features", [])),
        "seq_len": int(config.get("seq_len", 20)),
        "train_window_weeks": int(config.get("train_window_weeks", 104)),
        "valid_window_weeks": int(config.get("valid_window_weeks", 8)),
        "calibration_weeks": int(config.get("calibration_weeks", 12)),
        "sign_threshold": float(config.get("sign_threshold", 0.02)),
        "backbone": str(config.get("backbone", "lstm")),
        "hidden_size": int(config.get("hidden_size", 64)),
        "num_layers": int(config.get("num_layers", 2)),
        "d_model": int(config.get("d_model", 64)),
        "n_heads": int(config.get("n_heads", 4)),
        "d_ff": int(config.get("d_ff", 128)),
        "dropout": float(config.get("dropout", 0.3)),
        "lr": float(config.get("lr", 1e-4)),
        "optimizer": str(config.get("optimizer", "adamw")),
        "weight_decay": float(config.get("weight_decay", 1e-5)),
        "lr_scheduler": str(config.get("lr_scheduler", "none")),
        "lr_min": float(config.get("lr_min", 1e-6)),
        "cosine_t_max": int(config.get("cosine_t_max", 20)),
        "warm_restart_t0": int(config.get("warm_restart_t0", 8)),
        "warm_restart_t_mult": int(config.get("warm_restart_t_mult", 2)),
        "plateau_factor": float(config.get("plateau_factor", 0.5)),
        "plateau_patience": int(config.get("plateau_patience", 3)),
        "grad_clip_mode": str(config.get("grad_clip_mode", "norm")),
        "grad_clip_threshold": float(config.get("grad_clip_threshold", 1.0)),
        "norm_type": str(config.get("norm_type", "layernorm")),
        "norm_eps": float(config.get("norm_eps", 1e-8)),
        "batch_size": int(config.get("batch_size", 32)),
        "max_epochs": int(config.get("max_epochs", 40)),
        "patience": int(config.get("patience", 8)),
        "w3": float(w3),
        "w5": float(w5),
        "w10": float(w10),
        "extra_head_weight": float(config.get("extra_head_weight", 1.0)),
        "head_loss_weights": str(config.get("head_loss_weights", "")),
        "loss_type": str(config.get("loss_type", "l1")),
        "loss_alpha": float(config.get("loss_alpha", 0.3)),
        "ic_rank_beta": float(config.get("ic_rank_beta", 0.5)),
        "seed": int(config.get("seed", 42)),
        "model_track": str(config.get("model_track", "mainline_3510d")),
        "config_profile": str(config.get("config_profile", "lstm_rolling_baseline")),
        "config_status": str(config.get("config_status", "baseline")),
        "label_mode": str(config.get("label_mode", "close_to_close")),
    }


def _snapshot_xgb(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_dir": str(config.get("dataset_dir", "")),
        "feature_mode": str(config.get("feature_mode", "")),
        "feature_count": int(len(config.get("features", []))),
        "features": list(config.get("features", [])),
        "seq_len": int(config.get("seq_len", 20)),
        "train_window_weeks": int(config.get("train_window_weeks", 104)),
        "valid_window_weeks": int(config.get("valid_window_weeks", 8)),
        "calibration_weeks": int(config.get("calibration_weeks", 12)),
        "sign_threshold": float(config.get("sign_threshold", 0.02)),
        "n_estimators": int(config.get("n_estimators", 400)),
        "max_depth": int(config.get("max_depth", 6)),
        "learning_rate": float(config.get("learning_rate", 0.03)),
        "subsample": float(config.get("subsample", 0.8)),
        "colsample_bytree": float(config.get("colsample_bytree", 0.8)),
        "min_child_weight": float(config.get("min_child_weight", 1.0)),
        "gamma": float(config.get("gamma", 0.0)),
        "reg_alpha": float(config.get("reg_alpha", 0.0)),
        "reg_lambda": float(config.get("reg_lambda", 1.0)),
        "n_jobs": int(config.get("n_jobs", 8)),
        "early_stopping_rounds": int(config.get("early_stopping_rounds", 40)),
        "device": str(config.get("device", "cpu")),
        "seed": int(config.get("seed", 42)),
        "model_track": str(config.get("model_track", "mainline_3510d")),
        "config_profile": str(config.get("config_profile", "xgb_rolling_baseline")),
        "config_status": str(config.get("config_status", "baseline")),
        "stock_pool_id": str(config.get("stock_pool_id", "")),
        "stock_pool_version": str(config.get("stock_pool_version", "")),
        "evaluation_window_id": str(config.get("evaluation_window_id", "")),
        "dataset_id": str(config.get("dataset_id", "")),
    }


def _override_name(prefix: str, value: Any) -> str:
    return f"{prefix}_{_fmt_value(value)}"


def _spec_if_changed(
    *,
    model: str,
    level: str,
    name: str,
    base: dict[str, Any],
    overrides: dict[str, Any],
) -> ExperimentSpec | None:
    changed = False
    for key, value in overrides.items():
        if key not in base or base[key] != value:
            changed = True
            break
    if not changed:
        return None
    return ExperimentSpec(model=model, level=level, name=_sanitize_name(name), overrides=overrides)


def _build_lstm_specs(level: str, base: dict[str, Any]) -> list[ExperimentSpec]:
    specs: list[ExperimentSpec] = []
    model = "lstm"

    if level == "L1":
        for lr in (3e-5, 5e-5, 8e-5):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("lr", lr),
                base=base,
                overrides={"lr": float(lr)},
            )
            if spec:
                specs.append(spec)
        for dropout in (0.2, 0.3, 0.4):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("dropout", dropout),
                base=base,
                overrides={"dropout": float(dropout)},
            )
            if spec:
                specs.append(spec)
        for alpha in (0.12, 0.176, 0.24):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("loss_alpha", alpha),
                base=base,
                overrides={"loss_alpha": float(alpha)},
            )
            if spec:
                specs.append(spec)
        for weights in ((0.2, 0.4, 0.4), (0.1, 0.45, 0.45), (0.05, 0.475, 0.475)):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("w", weights),
                base=base,
                overrides={"w3": float(weights[0]), "w5": float(weights[1]), "w10": float(weights[2])},
            )
            if spec:
                specs.append(spec)
        for threshold in (0.015, 0.02, 0.03):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("sign", threshold),
                base=base,
                overrides={"sign_threshold": float(threshold)},
            )
            if spec:
                specs.append(spec)
        return specs

    if level == "L2":
        for hidden in (64, 96, 128):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("hidden", hidden),
                base=base,
                overrides={"hidden_size": int(hidden)},
            )
            if spec:
                specs.append(spec)
        for layers in (2, 3):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("layers", layers),
                base=base,
                overrides={"num_layers": int(layers)},
            )
            if spec:
                specs.append(spec)
        for window in (78, 104, 130):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("trainw", window),
                base=base,
                overrides={"train_window_weeks": int(window)},
            )
            if spec:
                specs.append(spec)
        for cal_w in (8, 12, 16):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("calw", cal_w),
                base=base,
                overrides={"calibration_weeks": int(cal_w)},
            )
            if spec:
                specs.append(spec)
        for scheduler in ("cosine_warm_restart", "plateau"):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("sched", scheduler),
                base=base,
                overrides={"lr_scheduler": str(scheduler)},
            )
            if spec:
                specs.append(spec)
        for wd in (1e-5, 3e-5, 1e-4):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("wd", wd),
                base=base,
                overrides={"weight_decay": float(wd)},
            )
            if spec:
                specs.append(spec)
        return specs

    if level == "L3":
        candidates = [
            ("long_window_low_lr", {"train_window_weeks": 130, "lr": 3e-5}),
            ("short_window_high_lr", {"train_window_weeks": 78, "lr": 8e-5}),
            (
                "high_capacity_regularized",
                {"hidden_size": 128, "num_layers": 3, "dropout": 0.4, "weight_decay": 1e-4},
            ),
            (
                "low_noise_head",
                {"w3": 0.05, "w5": 0.475, "w10": 0.475, "loss_alpha": 0.12},
            ),
            (
                "balanced_head",
                {"w3": 0.2, "w5": 0.4, "w10": 0.4, "loss_alpha": 0.24},
            ),
            (
                "plateau_schedule",
                {"lr_scheduler": "plateau", "plateau_factor": 0.3, "plateau_patience": 4},
            ),
        ]
        for name, overrides in candidates:
            spec = _spec_if_changed(model=model, level=level, name=name, base=base, overrides=overrides)
            if spec:
                specs.append(spec)
        return specs

    raise ValueError(f"unsupported level for lstm: {level}")


def _build_xgb_specs(level: str, base: dict[str, Any]) -> list[ExperimentSpec]:
    specs: list[ExperimentSpec] = []
    model = "xgb"

    if level == "L1":
        for n_estimators in (300, 400, 600):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("n_est", n_estimators),
                base=base,
                overrides={"n_estimators": int(n_estimators)},
            )
            if spec:
                specs.append(spec)
        for max_depth in (4, 6, 8):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("depth", max_depth),
                base=base,
                overrides={"max_depth": int(max_depth)},
            )
            if spec:
                specs.append(spec)
        for lr in (0.02, 0.03, 0.05):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("lr", lr),
                base=base,
                overrides={"learning_rate": float(lr)},
            )
            if spec:
                specs.append(spec)
        for subsample in (0.7, 0.8, 1.0):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("subsample", subsample),
                base=base,
                overrides={"subsample": float(subsample)},
            )
            if spec:
                specs.append(spec)
        for colsample in (0.7, 0.8, 1.0):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("colsample", colsample),
                base=base,
                overrides={"colsample_bytree": float(colsample)},
            )
            if spec:
                specs.append(spec)
        return specs

    if level == "L2":
        for child_weight in (1.0, 3.0, 5.0):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("childw", child_weight),
                base=base,
                overrides={"min_child_weight": float(child_weight)},
            )
            if spec:
                specs.append(spec)
        for gamma in (0.0, 0.2, 0.5):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("gamma", gamma),
                base=base,
                overrides={"gamma": float(gamma)},
            )
            if spec:
                specs.append(spec)
        for reg_alpha in (0.0, 0.1, 0.3):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("rega", reg_alpha),
                base=base,
                overrides={"reg_alpha": float(reg_alpha)},
            )
            if spec:
                specs.append(spec)
        for reg_lambda in (1.0, 2.0, 4.0):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("regl", reg_lambda),
                base=base,
                overrides={"reg_lambda": float(reg_lambda)},
            )
            if spec:
                specs.append(spec)
        for early_stop in (20, 40, 80):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("esr", early_stop),
                base=base,
                overrides={"early_stopping_rounds": int(early_stop)},
            )
            if spec:
                specs.append(spec)
        for train_window in (78, 104, 130):
            spec = _spec_if_changed(
                model=model,
                level=level,
                name=_override_name("trainw", train_window),
                base=base,
                overrides={"train_window_weeks": int(train_window)},
            )
            if spec:
                specs.append(spec)
        return specs

    if level == "L3":
        candidates = [
            ("shallow_fast", {"max_depth": 4, "learning_rate": 0.05, "n_estimators": 300}),
            ("deep_slow", {"max_depth": 8, "learning_rate": 0.02, "n_estimators": 800}),
            ("regularized", {"reg_alpha": 0.3, "reg_lambda": 4.0, "gamma": 0.2}),
            (
                "bagging_robust",
                {"subsample": 0.7, "colsample_bytree": 0.7, "min_child_weight": 5.0},
            ),
            ("long_window_slow", {"train_window_weeks": 130, "learning_rate": 0.02, "n_estimators": 600}),
            ("short_window_fast", {"train_window_weeks": 78, "learning_rate": 0.05, "n_estimators": 300}),
        ]
        for name, overrides in candidates:
            spec = _spec_if_changed(model=model, level=level, name=name, base=base, overrides=overrides)
            if spec:
                specs.append(spec)
        return specs

    raise ValueError(f"unsupported level for xgb: {level}")


LSTM_ARG_ORDER = [
    ("dataset_dir", "--dataset-dir"),
    ("backbone", "--backbone"),
    ("feature_mode", "--feature-mode"),
    ("seq_len", "--seq-len"),
    ("train_window_weeks", "--train-window-weeks"),
    ("valid_window_weeks", "--valid-window-weeks"),
    ("calibration_weeks", "--calibration-weeks"),
    ("sign_threshold", "--sign-threshold"),
    ("hidden_size", "--hidden-size"),
    ("num_layers", "--num-layers"),
    ("d_model", "--d-model"),
    ("n_heads", "--n-heads"),
    ("d_ff", "--d-ff"),
    ("dropout", "--dropout"),
    ("lr", "--lr"),
    ("optimizer", "--optimizer"),
    ("weight_decay", "--weight-decay"),
    ("lr_scheduler", "--lr-scheduler"),
    ("lr_min", "--lr-min"),
    ("cosine_t_max", "--cosine-t-max"),
    ("warm_restart_t0", "--warm-restart-t0"),
    ("warm_restart_t_mult", "--warm-restart-t-mult"),
    ("plateau_factor", "--plateau-factor"),
    ("plateau_patience", "--plateau-patience"),
    ("grad_clip_mode", "--grad-clip-mode"),
    ("grad_clip_threshold", "--grad-clip-threshold"),
    ("norm_type", "--norm-type"),
    ("norm_eps", "--norm-eps"),
    ("batch_size", "--batch-size"),
    ("max_epochs", "--max-epochs"),
    ("patience", "--patience"),
    ("w3", "--w3"),
    ("w5", "--w5"),
    ("w10", "--w10"),
    ("extra_head_weight", "--extra-head-weight"),
    ("head_loss_weights", "--head-loss-weights"),
    ("loss_type", "--loss-type"),
    ("loss_alpha", "--loss-alpha"),
    ("ic_rank_beta", "--ic-rank-beta"),
    ("seed", "--seed"),
    ("model_track", "--model-track"),
    ("config_profile", "--config-profile"),
    ("config_status", "--config-status"),
    ("label_mode", "--label-mode"),
]

XGB_ARG_ORDER = [
    ("dataset_dir", "--dataset-dir"),
    ("seq_len", "--seq-len"),
    ("feature_mode", "--feature-mode"),
    ("train_window_weeks", "--train-window-weeks"),
    ("valid_window_weeks", "--valid-window-weeks"),
    ("calibration_weeks", "--calibration-weeks"),
    ("sign_threshold", "--sign-threshold"),
    ("n_estimators", "--n-estimators"),
    ("max_depth", "--max-depth"),
    ("learning_rate", "--learning-rate"),
    ("subsample", "--subsample"),
    ("colsample_bytree", "--colsample-bytree"),
    ("min_child_weight", "--min-child-weight"),
    ("gamma", "--gamma"),
    ("reg_alpha", "--reg-alpha"),
    ("reg_lambda", "--reg-lambda"),
    ("n_jobs", "--n-jobs"),
    ("early_stopping_rounds", "--early-stopping-rounds"),
    ("device", "--device"),
    ("seed", "--seed"),
    ("model_track", "--model-track"),
    ("config_profile", "--config-profile"),
    ("config_status", "--config-status"),
    ("stock_pool_id", "--stock-pool-id"),
    ("stock_pool_version", "--stock-pool-version"),
    ("evaluation_window_id", "--evaluation-window-id"),
    ("dataset_id", "--dataset-id"),
]

MODEL_ALLOWED_KEYS = {
    "lstm": {k for k, _ in LSTM_ARG_ORDER},
    "xgb": {k for k, _ in XGB_ARG_ORDER},
}


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _filter_train_args(model: str, args_dict: dict[str, Any]) -> dict[str, Any]:
    allowed = MODEL_ALLOWED_KEYS.get(model)
    if allowed is None:
        raise ValueError(f"unsupported model: {model}")
    return {k: v for k, v in args_dict.items() if k in allowed}


def _build_train_command(
    *,
    python_exec: str,
    model: str,
    args_dict: dict[str, Any],
    report_path: Path,
    oos_path: Path,
    config_file: Path | None = None,
) -> list[str]:
    if model == "lstm":
        cmd = [python_exec, "scripts/run_lstm_rolling_retrain_dim19_regime.py"]
    elif model == "xgb":
        cmd = [python_exec, "scripts/run_xgboost_rolling_retrain_regime.py"]
    else:
        raise ValueError(f"unsupported model: {model}")
    if config_file is not None:
        cmd.extend(["--config-file", str(config_file)])
    else:
        arg_order = LSTM_ARG_ORDER if model == "lstm" else XGB_ARG_ORDER
        for key, flag in arg_order:
            if key in args_dict and args_dict[key] is not None:
                cmd.extend([flag, _stringify(args_dict[key])])
    cmd.extend(["--save-oos-parquet", str(oos_path), "--report", str(report_path)])
    return cmd


def _run_cmd(cmd: list[str], execute: bool) -> tuple[bool, str]:
    print("[cmd]", " ".join(cmd))
    if not execute:
        return True, "dry-run"
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        return False, f"exit={exc.returncode}"
    return True, "ok"


def _run_compare(
    *,
    python_exec: str,
    report_paths: list[Path],
    output_dir: Path,
    tag_prefix: str,
    execute: bool,
) -> list[dict[str, Any]]:
    report_args = [str(p) for p in report_paths]
    steps = [
        {
            "name": "audit",
            "cmd": [
                python_exec,
                "scripts/audit_ic_reports.py",
                "--reports",
                *report_args,
                "--output-dir",
                str(output_dir),
                "--tag",
                f"{tag_prefix}_coverage",
            ],
        },
        {
            "name": "compare_raw",
            "cmd": [
                python_exec,
                "scripts/compare_ic_reports.py",
                "--reports",
                *report_args,
                "--metric-source",
                "raw",
                "--monthly-source",
                "raw",
                "--daily-cs-mode",
                "required",
                "--check-protocol",
                "--output-dir",
                str(output_dir),
                "--tag",
                f"{tag_prefix}_raw",
            ],
        },
        {
            "name": "compare_calibrated",
            "cmd": [
                python_exec,
                "scripts/compare_ic_reports.py",
                "--reports",
                *report_args,
                "--metric-source",
                "calibrated",
                "--monthly-source",
                "calibrated",
                "--daily-cs-mode",
                "required",
                "--check-protocol",
                "--output-dir",
                str(output_dir),
                "--tag",
                f"{tag_prefix}_cal",
            ],
        },
    ]
    results: list[dict[str, Any]] = []
    for step in steps:
        ok, status = _run_cmd(step["cmd"], execute=execute)
        results.append({"name": step["name"], "status": status, "ok": ok, "cmd": step["cmd"]})
        if execute and not ok:
            break
    return results


def _print_snapshot(title: str, baseline_path: Path, base: dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    print(f"- baseline_report: {baseline_path}")
    print(f"- dataset_dir: {base.get('dataset_dir')}")
    print(f"- feature_mode: {base.get('feature_mode')}")
    features = base.get("features", [])
    print(f"- input_features: {len(features)}")
    if features:
        print(f"- feature_preview: {_features_preview(features)}")
    else:
        print("- feature_preview: (auto infer from dataset columns at runtime)")
    keys = [
        "seq_len",
        "train_window_weeks",
        "valid_window_weeks",
        "calibration_weeks",
        "sign_threshold",
        "label_mode",
        "seed",
    ]
    if "hidden_size" in base:
        keys.extend(
            [
                "hidden_size",
                "num_layers",
                "dropout",
                "lr",
                "optimizer",
                "weight_decay",
                "lr_scheduler",
                "w3",
                "w5",
                "w10",
                "loss_type",
                "loss_alpha",
                "ic_rank_beta",
            ]
        )
    else:
        keys.extend(
            [
                "n_estimators",
                "max_depth",
                "learning_rate",
                "subsample",
                "colsample_bytree",
                "min_child_weight",
                "gamma",
                "reg_alpha",
                "reg_lambda",
                "early_stopping_rounds",
                "device",
            ]
        )
    for key in keys:
        if key in base:
            print(f"- {key}: {base[key]}")


def _levels_from_arg(level_arg: str) -> list[str]:
    if level_arg.lower() == "all":
        return list(LEVEL_CHOICES)
    value = level_arg.upper()
    if value not in LEVEL_CHOICES:
        raise ValueError(f"invalid level: {level_arg}")
    return [value]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="多级别自动微调（LSTM / XGBoost）")
    p.add_argument("--model", choices=list(MODEL_CHOICES), default="both")
    p.add_argument("--level", default="all", help="L1 / L2 / L3 / all")
    p.add_argument(
        "--lstm-baseline-report",
        default=DEFAULT_LSTM_BASELINE,
        help="optional: reference baseline report for compare (if exists)",
    )
    p.add_argument(
        "--xgb-baseline-report",
        default=DEFAULT_XGB_BASELINE,
        help="optional: reference baseline report for compare (if exists)",
    )
    p.add_argument(
        "--lstm-config-file",
        default=DEFAULT_LSTM_CONFIG,
        help="JSON/TOML config for LSTM baseline args",
    )
    p.add_argument(
        "--xgb-config-file",
        default=DEFAULT_XGB_CONFIG,
        help="JSON/TOML config for XGBoost baseline args",
    )
    p.add_argument("--output-dir", default="output/reports")
    p.add_argument("--tag", default=datetime.now().strftime("%Y%m%d"))
    p.add_argument("--max-runs-per-level", type=int, default=24)
    p.add_argument("--execute", action="store_true", help="实际执行训练（默认仅输出计划）")
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--continue-on-error", action="store_true")
    p.add_argument("--python-exec", default=sys.executable)
    p.add_argument("--show-current", action="store_true", help="打印当前基线参数与输入特征")
    return p.parse_args()


def main() -> int:
    ensure_required_conda_env("py311-private")
    args = _parse_args()
    levels = _levels_from_arg(args.level)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_models = ["lstm", "xgb"] if args.model == "both" else [args.model]

    manifests: list[dict[str, Any]] = []
    config_dir = output_dir / "tuning_configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    for model in selected_models:
        reference_report: Path | None = None
        if model == "lstm":
            build_specs = _build_lstm_specs
            config_file = str(args.lstm_config_file).strip()
            if config_file:
                config_path = Path(config_file)
                if not config_path.exists():
                    raise FileNotFoundError(f"lstm config file not found: {config_path}")
                parser_like_keys = {k for k, _ in LSTM_ARG_ORDER}
                overrides, _ = extract_arg_overrides(
                    config_path=config_path,
                    allowed_keys=parser_like_keys,
                    section_candidates=(SECTION_BY_MODEL[model], model),
                )
                base = _snapshot_lstm(overrides)
                baseline_path = config_path
                candidate_text = str(args.lstm_baseline_report).strip()
                if candidate_text:
                    candidate = Path(candidate_text)
                    if candidate.exists():
                        reference_report = candidate
            else:
                baseline_text = str(args.lstm_baseline_report).strip()
                if not baseline_text:
                    raise FileNotFoundError(
                        "lstm baseline source missing: provide --lstm-config-file or --lstm-baseline-report"
                    )
                baseline_path = Path(baseline_text)
                if not baseline_path.exists():
                    raise FileNotFoundError(f"lstm baseline report not found: {baseline_path}")
                data = _load_json(baseline_path)
                base = _snapshot_lstm(data.get("config", {}))
                reference_report = baseline_path
        else:
            build_specs = _build_xgb_specs
            config_file = str(args.xgb_config_file).strip()
            if config_file:
                config_path = Path(config_file)
                if not config_path.exists():
                    raise FileNotFoundError(f"xgb config file not found: {config_path}")
                parser_like_keys = {k for k, _ in XGB_ARG_ORDER}
                overrides, _ = extract_arg_overrides(
                    config_path=config_path,
                    allowed_keys=parser_like_keys,
                    section_candidates=(SECTION_BY_MODEL[model], model),
                )
                base = _snapshot_xgb(overrides)
                baseline_path = config_path
                candidate_text = str(args.xgb_baseline_report).strip()
                if candidate_text:
                    candidate = Path(candidate_text)
                    if candidate.exists():
                        reference_report = candidate
            else:
                baseline_text = str(args.xgb_baseline_report).strip()
                if not baseline_text:
                    raise FileNotFoundError(
                        "xgb baseline source missing: provide --xgb-config-file or --xgb-baseline-report"
                    )
                baseline_path = Path(baseline_text)
                if not baseline_path.exists():
                    raise FileNotFoundError(f"xgb baseline report not found: {baseline_path}")
                data = _load_json(baseline_path)
                base = _snapshot_xgb(data.get("config", {}))
                reference_report = baseline_path

        if args.show_current:
            _print_snapshot(title=model.upper(), baseline_path=baseline_path, base=base)

        for level in levels:
            specs = build_specs(level, base)
            if args.max_runs_per_level > 0 and len(specs) > args.max_runs_per_level:
                specs = specs[: args.max_runs_per_level]

            print(f"\n[{model}:{level}] planned_runs={len(specs)} execute={args.execute}")
            run_results: list[dict[str, Any]] = []
            produced_reports: list[Path] = []

            for idx, spec in enumerate(specs, start=1):
                run_name = f"{model}_{level}_{idx:02d}_{spec.name}_{args.tag}"
                report_path = output_dir / f"{run_name}.json"
                oos_path = output_dir / f"{run_name}_oos.parquet"

                merged = dict(base)
                merged.update(spec.overrides)
                train_args = _filter_train_args(model, merged)
                run_config_path = config_dir / f"{run_name}.json"
                dump_json(
                    run_config_path,
                    {
                        SECTION_BY_MODEL[model]: train_args,
                    },
                )

                cmd = _build_train_command(
                    python_exec=args.python_exec,
                    model=model,
                    args_dict=train_args,
                    report_path=report_path,
                    oos_path=oos_path,
                    config_file=run_config_path,
                )
                ok, status = _run_cmd(cmd, execute=args.execute)
                row = {
                    "model": model,
                    "level": level,
                    "run_name": run_name,
                    "overrides": spec.overrides,
                    "run_config_path": str(run_config_path),
                    "report_path": str(report_path),
                    "oos_path": str(oos_path),
                    "status": status,
                    "ok": ok,
                    "cmd": cmd,
                }
                run_results.append(row)

                if ok:
                    produced_reports.append(report_path)
                elif args.execute and not args.continue_on_error:
                    break

            compare_results: list[dict[str, Any]] = []
            successful_reports = [Path(r["report_path"]) for r in run_results if r["ok"]]
            if not args.skip_compare and successful_reports:
                compare_reports = successful_reports
                if reference_report is not None:
                    compare_reports = [reference_report] + compare_reports
                compare_tag = f"{model}_{level}_{args.tag}"
                compare_results = _run_compare(
                    python_exec=args.python_exec,
                    report_paths=compare_reports,
                    output_dir=output_dir,
                    tag_prefix=compare_tag,
                    execute=args.execute,
                )

            manifests.append(
                {
                    "model": model,
                    "level": level,
                    "baseline_report": str(baseline_path),
                    "reference_report": (None if reference_report is None else str(reference_report)),
                    "base_config": base,
                    "runs": run_results,
                    "compare": compare_results,
                }
            )

    manifest_path = output_dir / f"multilevel_tuning_manifest_{args.tag}.json"
    manifest_path.write_text(json.dumps({"items": manifests}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved manifest: {manifest_path}")
    if not args.execute:
        print("当前为计划模式（dry-run）。如需实际训练，请追加 --execute。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
