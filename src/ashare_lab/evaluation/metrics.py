"""量化评估指标 — shim；IC 唯一实现在 ``ashare_infra.guard.metrics``。"""

from __future__ import annotations

from ashare_infra.guard.metrics import (
    aggregate_daily_to_monthly,
    calculate_daily_cs_ic,
    calculate_daily_ic,
    evaluate_model,
    information_coefficient,
    mean_absolute_error,
    mean_squared_error,
    rank_information_coefficient,
    sharpe_ratio,
    summarize_daily_cs,
)

__all__ = [
    "aggregate_daily_to_monthly",
    "calculate_daily_cs_ic",
    "calculate_daily_ic",
    "evaluate_model",
    "information_coefficient",
    "mean_absolute_error",
    "mean_squared_error",
    "rank_information_coefficient",
    "sharpe_ratio",
    "summarize_daily_cs",
]
