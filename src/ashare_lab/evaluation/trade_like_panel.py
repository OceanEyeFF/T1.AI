"""Trade-like main-line evaluation built from OOS prediction tables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ashare_lab.evaluation.metrics import information_coefficient, rank_information_coefficient
from ashare_lab.recommendation.trend_aggregation import (
    DEFAULT_TREND_AGGREGATION_WEIGHTS,
    TrendAggregationConfig,
    aggregate_primary_trend_scores,
    rank_primary_trend_scores,
)
from ashare_lab.trend_schema import PRIMARY_TREND_LABEL_COLS, PRIMARY_TREND_PRED_COLS, target_name_from_label


@dataclass(frozen=True, slots=True)
class TradeLikeGateThresholds:
    """Gate thresholds for the main-line trade-like panel."""

    mean_excess_return: float = 0.0
    daily_win_rate: float = 0.50
    monthly_win_rate: float = 0.55
    worst_month: float = -0.05
    max_consecutive_negative_months: int = 2


def build_primary_trade_like_comparison_panel(
    oos_df: pd.DataFrame,
    *,
    top_n: int = 10,
    aggregation_config: TrendAggregationConfig | None = None,
    gate: TradeLikeGateThresholds | None = None,
) -> dict[str, Any]:
    """Build a single canonical comparison panel for the primary 3d/5d/10d line."""

    if top_n <= 0:
        raise ValueError("top_n must be positive")

    cfg = aggregation_config or TrendAggregationConfig()
    gate_cfg = gate or TradeLikeGateThresholds()
    raw_panel = _build_trade_like_panel_block(
        oos_df,
        metric_source="raw",
        top_n=top_n,
        aggregation_config=cfg,
        gate=gate_cfg,
    )
    cal_panel = _build_trade_like_panel_block(
        oos_df,
        metric_source="calibrated",
        top_n=top_n,
        aggregation_config=cfg,
        gate=gate_cfg,
    )
    return {
        "score_target": "alpha_score",
        "evaluation_method": "topn_equal_weight_excess",
        "benchmark_definition": "same-day universe equal-weight realized alpha proxy",
        "top_n": int(top_n),
        "return_proxy_weights": _resolved_primary_weights(cfg.weights),
        "gate_thresholds": asdict(gate_cfg),
        "raw": raw_panel,
        "calibrated": cal_panel,
        "delta_cal_minus_raw": {
            "mean_excess_return": _metric_delta(cal_panel, raw_panel, "mean_excess_return"),
            "daily_win_rate": _metric_delta(cal_panel, raw_panel, "daily_win_rate"),
            "monthly_win_rate": _metric_delta(cal_panel, raw_panel, "monthly_win_rate"),
            "worst_month": _metric_delta(cal_panel, raw_panel, "worst_month"),
            "mean_hit_rate": _metric_delta(cal_panel, raw_panel, "mean_hit_rate"),
            "mean_ic": _metric_delta(cal_panel, raw_panel, "mean_ic"),
            "mean_rank_ic": _metric_delta(cal_panel, raw_panel, "mean_rank_ic"),
        },
    }


def _build_trade_like_panel_block(
    oos_df: pd.DataFrame,
    *,
    metric_source: str,
    top_n: int,
    aggregation_config: TrendAggregationConfig,
    gate: TradeLikeGateThresholds,
) -> dict[str, Any]:
    pred_cols = _prediction_columns(metric_source)
    required = {"date", "symbol", *PRIMARY_TREND_LABEL_COLS, *pred_cols}
    if not required.issubset(set(oos_df.columns)):
        return _empty_panel(metric_source)

    work = oos_df[list(required)].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    for col in PRIMARY_TREND_LABEL_COLS:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    for col in pred_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=["date"]).sort_values(["date", "symbol"]).reset_index(drop=True)
    if work.empty:
        return _empty_panel(metric_source)

    proxy_weights = _resolved_primary_weights(aggregation_config.weights)
    daily_rows: list[dict[str, Any]] = []

    for day, group in work.groupby("date", sort=True):
        day_work = group.dropna(subset=[*PRIMARY_TREND_LABEL_COLS, *pred_cols]).copy()
        if day_work.empty:
            continue

        realized_alpha = np.zeros(len(day_work), dtype=float)
        for label_col in PRIMARY_TREND_LABEL_COLS:
            realized_alpha += (
                float(proxy_weights[target_name_from_label(label_col)])
                * day_work[label_col].to_numpy(dtype=float, copy=False)
            )
        day_work["realized_alpha"] = realized_alpha

        aggregated = rank_primary_trend_scores(
            aggregate_primary_trend_scores(
                symbols=day_work["symbol"].astype(str).tolist(),
                predictions={
                    base_pred_col: day_work[pred_col].to_numpy(dtype=float, copy=False)
                    for base_pred_col, pred_col in zip(PRIMARY_TREND_PRED_COLS, pred_cols)
                },
                config=aggregation_config,
            )
        )
        score_map = {item.symbol: float(item.aggregate_score) for item in aggregated}
        day_work["alpha_score"] = day_work["symbol"].map(score_map).astype(float)
        day_work = day_work[np.isfinite(day_work["alpha_score"]) & np.isfinite(day_work["realized_alpha"])].copy()
        if day_work.empty:
            continue

        ranked = day_work.sort_values(["alpha_score", "symbol"], ascending=[False, True]).reset_index(drop=True)
        picked = ranked.head(min(top_n, len(ranked))).copy()
        if picked.empty:
            continue

        daily_rows.append(
            {
                "date": pd.Timestamp(day),
                "selected_count": int(len(picked)),
                "portfolio_return": float(picked["realized_alpha"].mean()),
                "universe_return": float(ranked["realized_alpha"].mean()),
                "excess_return": float(picked["realized_alpha"].mean() - ranked["realized_alpha"].mean()),
                "hit_rate": float((picked["realized_alpha"] > 0).mean()),
                "ic": float(
                    information_coefficient(
                        ranked["alpha_score"].to_numpy(dtype=float, copy=False),
                        ranked["realized_alpha"].to_numpy(dtype=float, copy=False),
                    )
                ),
                "rank_ic": float(
                    rank_information_coefficient(
                        ranked["alpha_score"].to_numpy(dtype=float, copy=False),
                        ranked["realized_alpha"].to_numpy(dtype=float, copy=False),
                    )
                ),
            }
        )

    if not daily_rows:
        return _empty_panel(metric_source)

    daily_df = pd.DataFrame(daily_rows).sort_values("date").reset_index(drop=True)
    daily_values = daily_df["excess_return"].tolist()
    daily_summary = _sequence_summary(daily_values)

    monthly_df = daily_df.copy()
    monthly_df["month"] = monthly_df["date"].dt.to_period("M").astype(str)
    monthly_series = (
        monthly_df.groupby("month", sort=True)["excess_return"]
        .mean()
        .astype(float)
    )
    monthly_values = monthly_series.tolist()
    monthly_summary = _sequence_summary(monthly_values)

    pass_gate = (
        float(daily_df["excess_return"].mean()) >= gate.mean_excess_return
        and float((daily_df["excess_return"] > 0).mean()) >= gate.daily_win_rate
        and float(monthly_summary["win_rate"]) >= gate.monthly_win_rate
        and float(monthly_summary["worst"]) >= gate.worst_month
        and int(monthly_summary["max_consecutive_negative"]) <= gate.max_consecutive_negative_months
    )
    monthly_records = [
        {"month": month, "avg_excess_return": float(value)}
        for month, value in monthly_series.items()
    ]

    return {
        "available": True,
        "metric_source": metric_source,
        "day_count": int(len(daily_df)),
        "month_count": int(len(monthly_records)),
        "mean_portfolio_return": float(daily_df["portfolio_return"].mean()),
        "mean_universe_return": float(daily_df["universe_return"].mean()),
        "mean_excess_return": float(daily_df["excess_return"].mean()),
        "daily_win_rate": float((daily_df["excess_return"] > 0).mean()),
        "worst_day_excess_return": float(daily_summary["worst"]),
        "max_consecutive_negative_days": int(daily_summary["max_consecutive_negative"]),
        "mean_hit_rate": float(daily_df["hit_rate"].mean()),
        "mean_ic": float(daily_df["ic"].mean()),
        "mean_rank_ic": float(daily_df["rank_ic"].mean()),
        "monthly_win_rate": float(monthly_summary["win_rate"]),
        "worst_month": float(monthly_summary["worst"]),
        "max_consecutive_negative_months": int(monthly_summary["max_consecutive_negative"]),
        "selected_count_avg": float(daily_df["selected_count"].mean()),
        "pass_gate": bool(pass_gate),
        "monthly": monthly_records,
    }


def _prediction_columns(metric_source: str) -> list[str]:
    if metric_source == "calibrated":
        return [f"{pred_col}_cal" for pred_col in PRIMARY_TREND_PRED_COLS]
    return list(PRIMARY_TREND_PRED_COLS)


def _resolved_primary_weights(overrides: Mapping[str, float] | None) -> dict[str, float]:
    weights = dict(DEFAULT_TREND_AGGREGATION_WEIGHTS)
    if overrides:
        for key, value in overrides.items():
            name = str(key)
            if name not in weights:
                raise ValueError(f"unsupported aggregation weight key: {name}")
            weight = float(value)
            if weight < 0:
                raise ValueError(f"aggregation weight must be non-negative: {name}={weight}")
            weights[name] = weight
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("aggregation weights sum to 0")
    return {key: float(value / total) for key, value in weights.items()}


def _sequence_summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"win_rate": 0.0, "worst": 0.0, "max_consecutive_negative": 0}
    arr = np.asarray(values, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"win_rate": 0.0, "worst": 0.0, "max_consecutive_negative": 0}

    negative_flags = [float(value) < 0.0 for value in finite.tolist()]
    streak = 0
    max_streak = 0
    for flag in negative_flags:
        if flag:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return {
        "win_rate": float(np.mean(finite > 0)),
        "worst": float(np.min(finite)),
        "max_consecutive_negative": int(max_streak),
    }


def _empty_panel(metric_source: str) -> dict[str, Any]:
    return {
        "available": False,
        "metric_source": metric_source,
        "day_count": 0,
        "month_count": 0,
        "mean_portfolio_return": 0.0,
        "mean_universe_return": 0.0,
        "mean_excess_return": 0.0,
        "daily_win_rate": 0.0,
        "worst_day_excess_return": 0.0,
        "max_consecutive_negative_days": 0,
        "mean_hit_rate": 0.0,
        "mean_ic": 0.0,
        "mean_rank_ic": 0.0,
        "monthly_win_rate": 0.0,
        "worst_month": 0.0,
        "max_consecutive_negative_months": 0,
        "selected_count_avg": 0.0,
        "pass_gate": False,
        "monthly": [],
    }


def _metric_delta(cal_panel: Mapping[str, Any], raw_panel: Mapping[str, Any], key: str) -> float:
    return float(float(cal_panel.get(key, 0.0)) - float(raw_panel.get(key, 0.0)))
