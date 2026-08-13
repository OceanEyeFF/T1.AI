#!/usr/bin/env python3
"""Auto-tune XGBoost rolling retrain parameters via Optuna.

This script keeps the existing training/evaluation pipeline unchanged:
it launches `scripts/run_xgboost_rolling_retrain_regime.py` for each trial.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from dataclasses import dataclass
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

CONFIG_SECTION_NAME = "run_xgboost_rolling_retrain_regime"
TRAIN_SCRIPT = "scripts/run_xgboost_rolling_retrain_regime.py"
METRIC_SOURCE_CHOICES = ("raw", "calibrated")

ALLOWED_BASE_KEYS = {
    "dataset_dir",
    "seq_len",
    "feature_mode",
    "train_window_weeks",
    "valid_window_weeks",
    "calibration_weeks",
    "train_window_months",
    "valid_window_months",
    "calibration_months",
    "sign_threshold",
    "n_estimators",
    "max_depth",
    "learning_rate",
    "subsample",
    "colsample_bytree",
    "min_child_weight",
    "gamma",
    "reg_alpha",
    "reg_lambda",
    "n_jobs",
    "early_stopping_rounds",
    "device",
    "seed",
}


@dataclass(frozen=True)
class ScoreWeights:
    w_ic: float
    w_rank_ic: float
    w_win_rate: float
    p_worst_month: float
    p_neg_streak: float


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    mean_ic_5_10: float
    mean_rank_ic_5_10: float
    monthly_win_rate: float
    worst_month: float
    max_consecutive_negative_months: int
    monthly_mean: float
    monthly_std: float
    monthly_icir: float


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Optuna auto-tuning for XGBoost rolling retrain.")
    p.add_argument(
        "--base-config-file",
        default="configs/experiments/xgb_rolling_baseline.toml",
        help="base JSON/TOML config used as defaults for each trial",
    )
    p.add_argument("--output-dir", default="outputs/reports/auto_tune_xgb")
    p.add_argument("--study-name", default="xgb_rolling_auto_tune")
    p.add_argument("--storage", default="", help="optuna storage URL, empty -> sqlite in output-dir")
    p.add_argument("--n-trials", type=int, default=40, help="number of new trials; 0 means summarize existing trials only")
    p.add_argument("--timeout-seconds", type=int, default=0, help="0 means no timeout")
    p.add_argument("--n-jobs", type=int, default=1, help="parallel trial workers")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--metric-source", choices=list(METRIC_SOURCE_CHOICES), default="calibrated")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--python-exec", default=sys.executable)
    p.add_argument("--continue-on-error", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--pruner-startup-trials", type=int, default=8)
    p.add_argument("--w-ic", type=float, default=1.0)
    p.add_argument("--w-rank-ic", type=float, default=0.30)
    p.add_argument("--w-win-rate", type=float, default=0.10)
    p.add_argument("--p-worst-month", type=float, default=0.60)
    p.add_argument("--p-neg-streak", type=float, default=0.08)
    return p.parse_args()


def _max_consecutive_negative(values: list[float]) -> int:
    best = 0
    curr = 0
    for v in values:
        if v < 0:
            curr += 1
            best = max(best, curr)
        else:
            curr = 0
    return best


def _weekly_metric_key(metric_source: str) -> str:
    return "raw_avg_ic" if metric_source == "raw" else "cal_avg_ic"


def _monthly_values_from_weekly_logs(weekly_logs: list[dict[str, Any]], metric_source: str) -> list[float]:
    key = _weekly_metric_key(metric_source)
    grouped: dict[str, list[float]] = {}
    for row in weekly_logs:
        week_start = str(row.get("week_start", ""))
        if len(week_start) < 7:
            continue
        month = week_start[:7]
        val = row.get(key)
        if val is None:
            continue
        try:
            fv = float(val)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(fv):
            continue
        grouped.setdefault(month, []).append(fv)
    if not grouped:
        return []
    months = sorted(grouped.keys())
    return [float(sum(grouped[m]) / len(grouped[m])) for m in months]


def _safe_mean(values: list[float], default: float = 0.0) -> float:
    if not values:
        return default
    return float(sum(values) / len(values))


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _safe_mean(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return float(math.sqrt(var))


def score_report(
    report: dict[str, Any],
    *,
    metric_source: str,
    weights: ScoreWeights,
) -> ScoreBreakdown:
    metric_root = "raw_oos_metrics" if metric_source == "raw" else "calibrated_oos_metrics"
    metrics = report.get(metric_root, {})

    ic_5 = float(metrics.get("ic_5d", 0.0))
    ic_10 = float(metrics.get("ic_10d", 0.0))
    rank_5 = float(metrics.get("rank_ic_5d", 0.0))
    rank_10 = float(metrics.get("rank_ic_10d", 0.0))

    mean_ic_5_10 = 0.5 * (ic_5 + ic_10)
    mean_rank_ic_5_10 = 0.5 * (rank_5 + rank_10)

    weekly_logs = report.get("weekly_logs", [])
    monthly_values = _monthly_values_from_weekly_logs(weekly_logs, metric_source=metric_source)
    monthly_mean = _safe_mean(monthly_values, default=0.0)
    monthly_std = _safe_std(monthly_values)
    monthly_icir = 0.0 if monthly_std <= 1e-12 else float(monthly_mean / monthly_std)
    worst_month = min(monthly_values) if monthly_values else 0.0
    monthly_win_rate = _safe_mean([1.0 if x > 0 else 0.0 for x in monthly_values], default=0.0)
    neg_streak = _max_consecutive_negative(monthly_values)

    total = (
        weights.w_ic * mean_ic_5_10
        + weights.w_rank_ic * mean_rank_ic_5_10
        + weights.w_win_rate * monthly_win_rate
        - weights.p_worst_month * max(0.0, -worst_month)
        - weights.p_neg_streak * float(neg_streak)
    )
    return ScoreBreakdown(
        total=float(total),
        mean_ic_5_10=float(mean_ic_5_10),
        mean_rank_ic_5_10=float(mean_rank_ic_5_10),
        monthly_win_rate=float(monthly_win_rate),
        worst_month=float(worst_month),
        max_consecutive_negative_months=int(neg_streak),
        monthly_mean=float(monthly_mean),
        monthly_std=float(monthly_std),
        monthly_icir=float(monthly_icir),
    )


def _format_toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        text = f"{v:.12g}"
        if "." not in text and "e" not in text.lower():
            text = text + ".0"
        return text
    return json.dumps(str(v), ensure_ascii=False)


def write_best_toml(path: Path, section_name: str, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"[{section_name}]"]
    for k in sorted(payload.keys()):
        lines.append(f"{k} = {_format_toml_value(payload[k])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_trial_command(
    *,
    python_exec: str,
    config_path: Path,
    report_path: Path,
    oos_path: Path,
) -> list[str]:
    return [
        python_exec,
        TRAIN_SCRIPT,
        "--config-file",
        str(config_path),
        "--report",
        str(report_path),
        "--save-oos-parquet",
        str(oos_path),
    ]


def _sample_xgb_params(trial: Any) -> dict[str, Any]:
    return {
        "n_estimators": int(trial.suggest_int("n_estimators", 200, 900, step=100)),
        "max_depth": int(trial.suggest_int("max_depth", 3, 10)),
        "learning_rate": float(trial.suggest_float("learning_rate", 0.01, 0.08, log=True)),
        "subsample": float(trial.suggest_float("subsample", 0.60, 1.00, step=0.05)),
        "colsample_bytree": float(trial.suggest_float("colsample_bytree", 0.60, 1.00, step=0.05)),
        "min_child_weight": float(trial.suggest_float("min_child_weight", 1.0, 8.0, step=0.5)),
        "gamma": float(trial.suggest_float("gamma", 0.0, 1.0, step=0.1)),
        "reg_alpha": float(trial.suggest_float("reg_alpha", 0.0, 1.0, step=0.1)),
        "reg_lambda": float(trial.suggest_float("reg_lambda", 0.5, 6.0, step=0.5)),
        "early_stopping_rounds": int(trial.suggest_int("early_stopping_rounds", 10, 80, step=10)),
        "sign_threshold": float(trial.suggest_float("sign_threshold", 0.01, 0.05, step=0.005)),
        "train_window_weeks": int(trial.suggest_categorical("train_window_weeks", [78, 104, 130])),
        "valid_window_weeks": int(trial.suggest_categorical("valid_window_weeks", [6, 8, 10])),
        "calibration_weeks": int(trial.suggest_categorical("calibration_weeks", [8, 12, 16])),
    }


def _resolve_storage_url(storage: str, output_dir: Path) -> str:
    if storage.strip():
        return storage.strip()
    db_path = (output_dir / "optuna_xgb_study.db").resolve()
    return f"sqlite:///{db_path}"


def _collect_base_args(config_file: Path) -> dict[str, Any]:
    overrides, _ = extract_arg_overrides(
        config_path=config_file,
        allowed_keys=ALLOWED_BASE_KEYS,
        section_candidates=(CONFIG_SECTION_NAME, "xgb"),
    )
    if "dataset_dir" not in overrides:
        raise ValueError("base config must include dataset_dir")
    if "seq_len" not in overrides:
        overrides["seq_len"] = 20
    if "feature_mode" not in overrides:
        overrides["feature_mode"] = "auto"
    return dict(overrides)


def _write_leaderboard_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = sorted(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    ensure_required_conda_env("py311-private")
    args = _parse_args()

    try:
        import optuna
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime env dependent
        print("optuna is required. Install with: python -m pip install 'optuna>=3.6'", file=sys.stderr)
        raise SystemExit(2) from exc

    output_dir = Path(args.output_dir)
    trials_dir = output_dir / "trials"
    configs_dir = output_dir / "trial_configs"
    output_dir.mkdir(parents=True, exist_ok=True)
    trials_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)

    base_config_file = Path(args.base_config_file)
    base_args = _collect_base_args(base_config_file)
    weights = ScoreWeights(
        w_ic=float(args.w_ic),
        w_rank_ic=float(args.w_rank_ic),
        w_win_rate=float(args.w_win_rate),
        p_worst_month=float(args.p_worst_month),
        p_neg_streak=float(args.p_neg_streak),
    )

    storage_url = _resolve_storage_url(args.storage, output_dir)
    sampler = optuna.samplers.TPESampler(seed=int(args.seed), multivariate=True)
    pruner = optuna.pruners.MedianPruner(n_startup_trials=max(0, int(args.pruner_startup_trials)))
    study = optuna.create_study(
        study_name=str(args.study_name),
        storage=storage_url,
        load_if_exists=True,
        direction="maximize",
        sampler=sampler,
        pruner=pruner,
    )

    def objective(trial: Any) -> float:
        trial_name = f"trial_{trial.number:04d}"
        sampled = _sample_xgb_params(trial)
        merged = dict(base_args)
        merged.update(sampled)

        config_path = configs_dir / f"{trial_name}.json"
        report_path = trials_dir / f"{trial_name}.json"
        oos_path = trials_dir / f"{trial_name}_oos.parquet"
        dump_json(config_path, {CONFIG_SECTION_NAME: merged})

        cmd = _build_trial_command(
            python_exec=args.python_exec,
            config_path=config_path,
            report_path=report_path,
            oos_path=oos_path,
        )
        trial.set_user_attr("run_name", trial_name)
        trial.set_user_attr("config_path", str(config_path))
        trial.set_user_attr("report_path", str(report_path))
        trial.set_user_attr("oos_path", str(oos_path))
        trial.set_user_attr("cmd", cmd)

        run_kwargs: dict[str, Any] = {"check": True}
        if not args.verbose:
            run_kwargs.update({"capture_output": True, "text": True})
        try:
            subprocess.run(cmd, **run_kwargs)
        except subprocess.CalledProcessError as exc:
            trial.set_user_attr("status", "failed")
            if not args.continue_on_error:
                raise
            # Continue search while making this trial clearly poor.
            trial.set_user_attr("error", f"exit={exc.returncode}")
            return -1e9

        payload = json.loads(report_path.read_text(encoding="utf-8"))
        score = score_report(
            payload,
            metric_source=str(args.metric_source),
            weights=weights,
        )
        trial.set_user_attr("status", "ok")
        trial.set_user_attr("score", score.total)
        trial.set_user_attr("mean_ic_5_10", score.mean_ic_5_10)
        trial.set_user_attr("mean_rank_ic_5_10", score.mean_rank_ic_5_10)
        trial.set_user_attr("monthly_win_rate", score.monthly_win_rate)
        trial.set_user_attr("worst_month", score.worst_month)
        trial.set_user_attr("neg_streak", score.max_consecutive_negative_months)
        trial.set_user_attr("monthly_icir", score.monthly_icir)
        return score.total

    timeout = None if int(args.timeout_seconds) <= 0 else int(args.timeout_seconds)
    requested_trials = max(0, int(args.n_trials))
    if requested_trials > 0:
        study.optimize(
            objective,
            n_trials=requested_trials,
            timeout=timeout,
            n_jobs=max(1, int(args.n_jobs)),
        )
    else:
        print("No new trials requested (--n-trials=0). Summarizing existing study records only.")

    completed = [t for t in study.trials if t.state.name == "COMPLETE"]
    completed.sort(key=lambda t: float(t.value), reverse=True)
    top_k = completed[: max(1, int(args.top_k))]

    leaderboard_rows: list[dict[str, Any]] = []
    for t in top_k:
        row = {
            "trial_number": int(t.number),
            "score": float(t.value),
            "run_name": t.user_attrs.get("run_name", ""),
            "mean_ic_5_10": float(t.user_attrs.get("mean_ic_5_10", 0.0)),
            "mean_rank_ic_5_10": float(t.user_attrs.get("mean_rank_ic_5_10", 0.0)),
            "monthly_win_rate": float(t.user_attrs.get("monthly_win_rate", 0.0)),
            "worst_month": float(t.user_attrs.get("worst_month", 0.0)),
            "neg_streak": int(t.user_attrs.get("neg_streak", 0)),
            "monthly_icir": float(t.user_attrs.get("monthly_icir", 0.0)),
            "report_path": t.user_attrs.get("report_path", ""),
            "config_path": t.user_attrs.get("config_path", ""),
        }
        for k, v in sorted(t.params.items()):
            row[f"param_{k}"] = v
        leaderboard_rows.append(row)

    leaderboard_csv = output_dir / "leaderboard.csv"
    _write_leaderboard_csv(leaderboard_csv, leaderboard_rows)
    leaderboard_json = output_dir / "leaderboard.json"
    dump_json(leaderboard_json, {"rows": leaderboard_rows})

    if not completed:
        print("No completed trial. Check trial logs in output directory.")
        return 1

    best = completed[0]
    best_config = dict(base_args)
    best_config.update(best.params)
    best_json = output_dir / "best_params.json"
    dump_json(
        best_json,
        {
            "study_name": str(args.study_name),
            "metric_source": str(args.metric_source),
            "score_weights": weights.__dict__,
            "best_trial_number": int(best.number),
            "best_score": float(best.value),
            "best_params": best.params,
            "config": best_config,
            "report_path": best.user_attrs.get("report_path", ""),
            "config_path": best.user_attrs.get("config_path", ""),
        },
    )

    best_toml = output_dir / "best_params.toml"
    write_best_toml(best_toml, CONFIG_SECTION_NAME, best_config)

    summary = {
        "study_name": str(args.study_name),
        "storage": storage_url,
        "n_trials_total": len(study.trials),
        "n_trials_complete": len(completed),
        "best_trial_number": int(best.number),
        "best_score": float(best.value),
        "best_report_path": best.user_attrs.get("report_path", ""),
        "leaderboard_csv": str(leaderboard_csv),
        "best_params_json": str(best_json),
        "best_params_toml": str(best_toml),
    }
    summary_json = output_dir / "summary.json"
    dump_json(summary_json, summary)

    print("\n=== Auto Tune Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
