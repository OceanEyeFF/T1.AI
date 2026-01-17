"""Monitoring + retrain trigger utilities (Task 3.4).

This module provides:
- rolling-window monitoring over recent validation results (IC / hit rate etc.)
- degradation detection (relative to a historical best baseline window)
- retrain decision logic (incremental vs full)
- an optional retrain trigger hook that records model snapshots

The canonical source of metrics is `RecommendationHistory.validations`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from ashare_lab.recommendation import RecommendationHistory


@dataclass(frozen=True, slots=True)
class MonitoringMetrics:
    window_start_date: str
    window_end_date: str
    mean_ic: float
    mean_hit_rate: float
    mean_rank_ic: float
    mean_excess_return: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class RetrainDecision:
    should_retrain: bool
    strategy: str  # incremental / full
    trigger_reason: str
    current_metrics: MonitoringMetrics
    baseline_metrics: MonitoringMetrics | None


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return float(default)


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return int(default)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    try:
        return int(float(str(value).strip()))
    except Exception:
        return int(default)


def _mapping_get_first(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


class PerformanceMonitor:
    """Compute rolling metrics and decide whether to retrain."""

    def __init__(
        self,
        history: RecommendationHistory,
        config: Mapping[str, Any] | None = None,
        *,
        incremental_trainer: Callable[[str, RetrainDecision], Mapping[str, Any]] | None = None,
        full_trainer: Callable[[str, RetrainDecision], Mapping[str, Any]] | None = None,
    ) -> None:
        self.history = history
        cfg = dict(config or {})
        self.config = dict(cfg.get("monitoring") or cfg)

        self.enabled = bool(self.config.get("enabled", True))
        self.rolling_window_days = _as_int(self.config.get("rolling_window_days", 20), 20)
        self.ic_threshold = _as_float(self.config.get("ic_threshold", 0.04), 0.04)
        self.hit_rate_threshold = _as_float(self.config.get("hit_rate_threshold", 0.55), 0.55)
        self.horizon = _as_int(self.config.get("horizon", 5), 5)

        self.retrain_trigger_mode = str(self.config.get("retrain_trigger_mode", "auto"))
        retrain_threshold = dict(self.config.get("retrain_threshold") or {})
        self.ic_degrade_ratio = _as_float(retrain_threshold.get("ic_degrade_ratio", 0.3), 0.3)
        self.consecutive_low_days = _as_int(retrain_threshold.get("consecutive_low_days", 5), 5)

        self.default_strategy = str(self.config.get("retrain_strategy", "incremental"))
        self.incremental_trainer = incremental_trainer
        self.full_trainer = full_trainer

    def _empty_metrics(self, date_str: str) -> MonitoringMetrics:
        return MonitoringMetrics(
            window_start_date=str(date_str),
            window_end_date=str(date_str),
            mean_ic=0.0,
            mean_hit_rate=0.0,
            mean_rank_ic=0.0,
            mean_excess_return=0.0,
            sample_count=0,
        )

    def _metrics_from_df(self, df) -> MonitoringMetrics:
        if df is None or df.empty:
            raise ValueError("no validation results available to compute monitoring metrics")
        df = df.sort_values("rec_date").reset_index(drop=True)
        return MonitoringMetrics(
            window_start_date=str(df.iloc[0]["rec_date"]),
            window_end_date=str(df.iloc[-1]["rec_date"]),
            mean_ic=float(df["ic"].mean()),
            mean_hit_rate=float(df["hit_rate"].mean()),
            mean_rank_ic=float(df["rank_ic"].mean()),
            mean_excess_return=float(df["excess_return"].mean()),
            sample_count=int(len(df)),
        )

    def calculate_rolling_metrics(self, end_date: str, window_days: int) -> MonitoringMetrics:
        """Compute rolling-window metrics using last N validation rows (trade-day aligned)."""
        if window_days <= 0:
            raise ValueError("window_days must be positive")

        df = self.history.query_validations(end_date=end_date, horizon=self.horizon)
        if df is None or df.empty:
            raise ValueError("no validations found for rolling metrics")

        df = df.sort_values("rec_date").reset_index(drop=True)
        window = df.tail(int(window_days))
        return self._metrics_from_df(window)

    def _best_baseline_metrics(self, end_date: str, window_days: int) -> MonitoringMetrics | None:
        df = self.history.query_validations(end_date=end_date, horizon=self.horizon)
        if df is None or df.empty:
            return None

        df = df.sort_values("rec_date").reset_index(drop=True)
        if len(df) < window_days:
            return None

        rolling_ic = df["ic"].rolling(window_days).mean()
        best_end_idx = int(rolling_ic.idxmax())
        start_idx = best_end_idx - window_days + 1
        if start_idx < 0:
            return None
        return self._metrics_from_df(df.iloc[start_idx : best_end_idx + 1])

    def detect_degradation(self, current: MonitoringMetrics, baseline: MonitoringMetrics) -> bool:
        """Detect IC degradation relative to baseline."""
        if baseline.sample_count <= 0:
            return False
        if baseline.mean_ic <= 0:
            return False
        ratio = (baseline.mean_ic - current.mean_ic) / baseline.mean_ic
        return float(ratio) > float(self.ic_degrade_ratio)

    def _degradation_ratio(self, current: MonitoringMetrics, baseline: MonitoringMetrics) -> float:
        if baseline.sample_count <= 0 or baseline.mean_ic <= 0:
            return 0.0
        return float((baseline.mean_ic - current.mean_ic) / baseline.mean_ic)

    def check_consecutive_low_performance(self, end_date: str, threshold_ic: float, consecutive_days: int) -> bool:
        """Check whether recent `consecutive_days` IC values are all below `threshold_ic`."""
        if consecutive_days <= 0:
            raise ValueError("consecutive_days must be positive")
        df = self.history.query_validations(end_date=end_date, horizon=self.horizon)
        if df is None or df.empty:
            return False
        df = df.sort_values("rec_date").reset_index(drop=True)
        tail = df.tail(int(consecutive_days))
        if len(tail) < consecutive_days:
            return False
        return bool((tail["ic"] < float(threshold_ic)).all())

    def _check_consecutive_low_hit_rate(self, end_date: str, threshold_hit_rate: float, consecutive_days: int) -> bool:
        df = self.history.query_validations(end_date=end_date, horizon=self.horizon)
        if df is None or df.empty:
            return False
        df = df.sort_values("rec_date").reset_index(drop=True)
        tail = df.tail(int(consecutive_days))
        if len(tail) < consecutive_days:
            return False
        return bool((tail["hit_rate"] < float(threshold_hit_rate)).all())

    def make_retrain_decision(self, current_date: str) -> RetrainDecision:
        """Decide whether to retrain and which strategy to use."""
        if not self.enabled:
            empty = self._empty_metrics(current_date)
            return RetrainDecision(
                should_retrain=False,
                strategy=str(self.default_strategy),
                trigger_reason="monitoring_disabled",
                current_metrics=empty,
                baseline_metrics=None,
            )

        if self.retrain_trigger_mode != "auto":
            current_metrics = self.calculate_rolling_metrics(current_date, self.rolling_window_days)
            baseline = self._best_baseline_metrics(current_date, self.rolling_window_days)
            return RetrainDecision(
                should_retrain=False,
                strategy=str(self.default_strategy),
                trigger_reason="manual_mode",
                current_metrics=current_metrics,
                baseline_metrics=baseline,
            )

        current_metrics = self.calculate_rolling_metrics(current_date, self.rolling_window_days)
        baseline = self._best_baseline_metrics(current_date, self.rolling_window_days)

        low_ic = current_metrics.mean_ic < float(self.ic_threshold)
        low_hit = current_metrics.mean_hit_rate < float(self.hit_rate_threshold)

        consecutive_low_ic = self.check_consecutive_low_performance(
            current_date,
            threshold_ic=float(self.ic_threshold),
            consecutive_days=int(self.consecutive_low_days),
        )
        consecutive_low_hit = self._check_consecutive_low_hit_rate(
            current_date,
            threshold_hit_rate=float(self.hit_rate_threshold),
            consecutive_days=int(self.consecutive_low_days),
        )

        degrade = False
        degrade_ratio = 0.0
        if baseline is not None:
            degrade = self.detect_degradation(current_metrics, baseline)
            degrade_ratio = self._degradation_ratio(current_metrics, baseline)

        should_retrain = bool(low_ic or low_hit or consecutive_low_ic or consecutive_low_hit or degrade)
        strategy = str(self.default_strategy)
        reason = "ok"

        if should_retrain:
            if degrade_ratio >= 0.5:
                strategy = "full"
                reason = "ic_severe_degradation"
            elif consecutive_low_ic or consecutive_low_hit:
                strategy = "incremental"
                reason = "consecutive_low_performance"
            elif low_ic:
                strategy = "incremental"
                reason = "ic_below_threshold"
            elif low_hit:
                strategy = "incremental"
                reason = "hit_rate_below_threshold"
            elif degrade:
                strategy = "incremental"
                reason = "ic_degradation"
            else:  # pragma: no cover - defensive
                strategy = "incremental"
                reason = "triggered"

        if strategy not in ("incremental", "full"):
            strategy = "incremental" if strategy != "full" else "full"

        return RetrainDecision(
            should_retrain=should_retrain,
            strategy=strategy,
            trigger_reason=reason,
            current_metrics=current_metrics,
            baseline_metrics=baseline,
        )

    def trigger_retrain(self, decision: RetrainDecision, current_date: str) -> dict[str, Any]:
        """Trigger retraining via injected trainer callbacks and record a model snapshot."""
        if not decision.should_retrain:
            return {"skipped": True, "reason": decision.trigger_reason}

        if decision.strategy == "incremental":
            trainer = self.incremental_trainer
        elif decision.strategy == "full":
            trainer = self.full_trainer
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown retrain strategy: {decision.strategy}")

        if trainer is None:
            raise RuntimeError(f"no trainer configured for strategy={decision.strategy}")

        result = dict(trainer(current_date, decision))

        model_path = _mapping_get_first(result, ("model_path", "checkpoint", "path")) or ""
        train_samples = _as_int(_mapping_get_first(result, ("train_samples", "samples", "n_samples")), 0)
        val_ic = _mapping_get_first(result, ("val_ic", "ic"))
        trigger_reason = decision.trigger_reason

        self.history.save_model_snapshot(
            snapshot_date=current_date,
            model_path=str(model_path),
            model_type=decision.strategy,
            train_samples=int(train_samples),
            val_ic=None if val_ic is None else float(val_ic),
            trigger_reason=str(trigger_reason),
        )

        result["model_path"] = str(model_path)
        result["train_samples"] = int(train_samples)
        if val_ic is not None:
            result["val_ic"] = float(val_ic)
        else:
            result.pop("val_ic", None)
        result.setdefault("snapshot_recorded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return result
