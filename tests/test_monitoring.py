from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Mapping

import pandas as pd
import pytest

from ashare_lab.pipeline.monitoring import MonitoringMetrics, PerformanceMonitor, RetrainDecision
from ashare_lab.recommendation import RecommendationHistory


def _seed_validations(
    history: RecommendationHistory,
    start: date,
    ics: list[float],
    hit_rates: list[float] | None = None,
    *,
    horizon: int = 5,
) -> list[str]:
    if hit_rates is None:
        hit_rates = [0.6 for _ in ics]
    assert len(hit_rates) == len(ics)

    dates: list[str] = []
    for i, (ic, hit) in enumerate(zip(ics, hit_rates, strict=True)):
        rec_date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        history.save_validation_results(
            rec_date=rec_date,
            validation_result={
                "hit_rate": float(hit),
                "ic": float(ic),
                "rank_ic": float(ic) * 0.8,
                "excess_return": float(ic) * 0.1,
                "valid_count": 10,
                "validation_date": rec_date,
            },
            horizon=horizon,
        )
        dates.append(rec_date)
    return dates


def test_calculate_rolling_metrics_uses_last_n_rows() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        ics = [0.01 * i for i in range(1, 26)]  # 0.01..0.25
        dates = _seed_validations(history, start, ics)

        monitor = PerformanceMonitor(history, {"monitoring": {"rolling_window_days": 20, "horizon": 5}})
        metrics = monitor.calculate_rolling_metrics(end_date=dates[-1], window_days=20)

        expected_ics = ics[-20:]
        assert metrics.sample_count == 20
        assert metrics.window_start_date == dates[-20]
        assert metrics.window_end_date == dates[-1]
        assert metrics.mean_ic == pytest.approx(sum(expected_ics) / 20)


def test_calculate_rolling_metrics_errors_on_empty_or_invalid_window() -> None:
    with RecommendationHistory(":memory:") as history:
        monitor = PerformanceMonitor(history, {"monitoring": {"horizon": 5}})
        with pytest.raises(ValueError):
            monitor.calculate_rolling_metrics("2025-01-01", window_days=0)
        with pytest.raises(ValueError):
            monitor.calculate_rolling_metrics("2025-01-01", window_days=20)


def test_detect_degradation_ratio_logic() -> None:
    with RecommendationHistory(":memory:") as history:
        monitor = PerformanceMonitor(history, {"monitoring": {"retrain_threshold": {"ic_degrade_ratio": 0.3}}})

        baseline = MonitoringMetrics("2025-01-01", "2025-01-20", 0.10, 0.6, 0.08, 0.01, 20)
        current = MonitoringMetrics("2025-01-02", "2025-01-21", 0.06, 0.6, 0.05, 0.01, 20)
        assert monitor.detect_degradation(current, baseline) is True

        current2 = MonitoringMetrics("2025-01-02", "2025-01-21", 0.08, 0.6, 0.05, 0.01, 20)
        assert monitor.detect_degradation(current2, baseline) is False

        zero_base = MonitoringMetrics("2025-01-01", "2025-01-20", 0.0, 0.6, 0.0, 0.0, 20)
        assert monitor.detect_degradation(current, zero_base) is False


def test_check_consecutive_low_performance() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        ics = [0.10] * 10 + [0.01] * 5
        dates = _seed_validations(history, start, ics)

        monitor = PerformanceMonitor(history, {"monitoring": {"horizon": 5, "retrain_threshold": {"consecutive_low_days": 5}}})
        assert monitor.check_consecutive_low_performance(dates[-1], threshold_ic=0.04, consecutive_days=5) is True
        assert monitor.check_consecutive_low_performance(dates[-1], threshold_ic=0.0, consecutive_days=5) is False

        with pytest.raises(ValueError):
            monitor.check_consecutive_low_performance(dates[-1], threshold_ic=0.04, consecutive_days=0)


def test_make_retrain_decision_normal_no_trigger() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        ics = [0.08] * 30
        hits = [0.60] * 30
        dates = _seed_validations(history, start, ics, hits)

        monitor = PerformanceMonitor(
            history,
            {
                "monitoring": {
                    "rolling_window_days": 20,
                    "horizon": 5,
                    "ic_threshold": 0.04,
                    "hit_rate_threshold": 0.55,
                    "retrain_threshold": {"ic_degrade_ratio": 0.3, "consecutive_low_days": 5},
                    "retrain_strategy": "incremental",
                }
            },
        )

        decision = monitor.make_retrain_decision(dates[-1])
        assert decision.should_retrain is False
        assert decision.trigger_reason == "ok"
        assert decision.current_metrics.sample_count == 20
        assert decision.baseline_metrics is not None


def test_make_retrain_decision_ic_below_threshold_triggers_incremental() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        # baseline window mean ~0.05, current window mean ~0.03 -> low IC triggers but not severe
        ics = [0.05] * 20 + [0.03] * 20
        hits = [0.60] * 40
        dates = _seed_validations(history, start, ics, hits)

        monitor = PerformanceMonitor(history, {"monitoring": {"rolling_window_days": 20, "horizon": 5, "ic_threshold": 0.04}})
        decision = monitor.make_retrain_decision(dates[-1])

        assert decision.should_retrain is True
        assert decision.strategy == "incremental"
        assert decision.trigger_reason in {"ic_below_threshold", "consecutive_low_performance", "ic_degradation"}


def test_make_retrain_decision_consecutive_low_triggers_incremental() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        ics = [0.06] * 30 + [0.01] * 5
        hits = [0.60] * 35
        dates = _seed_validations(history, start, ics, hits)

        monitor = PerformanceMonitor(
            history,
            {
                "monitoring": {
                    "rolling_window_days": 20,
                    "horizon": 5,
                    "ic_threshold": 0.04,
                    "retrain_threshold": {"consecutive_low_days": 5, "ic_degrade_ratio": 0.3},
                }
            },
        )
        decision = monitor.make_retrain_decision(dates[-1])

        assert decision.should_retrain is True
        assert decision.strategy == "incremental"
        assert decision.trigger_reason == "consecutive_low_performance"


def test_make_retrain_decision_severe_degradation_triggers_full() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        ics = [0.10] * 20 + [0.03] * 20
        hits = [0.60] * 40
        dates = _seed_validations(history, start, ics, hits)

        monitor = PerformanceMonitor(
            history,
            {"monitoring": {"rolling_window_days": 20, "horizon": 5, "ic_threshold": 0.04, "retrain_threshold": {"ic_degrade_ratio": 0.3}}},
        )
        decision = monitor.make_retrain_decision(dates[-1])

        assert decision.should_retrain is True
        assert decision.strategy == "full"
        assert decision.trigger_reason == "ic_severe_degradation"


def test_make_retrain_decision_manual_mode_never_triggers() -> None:
    with RecommendationHistory(":memory:") as history:
        start = date(2025, 1, 1)
        ics = [0.01] * 25
        dates = _seed_validations(history, start, ics)

        monitor = PerformanceMonitor(history, {"monitoring": {"rolling_window_days": 20, "horizon": 5, "retrain_trigger_mode": "manual"}})
        decision = monitor.make_retrain_decision(dates[-1])
        assert decision.should_retrain is False
        assert decision.trigger_reason == "manual_mode"


def test_make_retrain_decision_disabled_returns_empty_metrics() -> None:
    with RecommendationHistory(":memory:") as history:
        monitor = PerformanceMonitor(history, {"monitoring": {"enabled": False}})
        decision = monitor.make_retrain_decision("2025-01-02")
        assert decision.should_retrain is False
        assert decision.trigger_reason == "monitoring_disabled"
        assert decision.current_metrics.sample_count == 0


def test_trigger_retrain_records_model_snapshot_and_returns_summary() -> None:
    with RecommendationHistory(":memory:") as history:
        decision = RetrainDecision(
            should_retrain=True,
            strategy="incremental",
            trigger_reason="ic_below_threshold",
            current_metrics=MonitoringMetrics("2025-01-01", "2025-01-20", 0.03, 0.5, 0.02, 0.0, 20),
            baseline_metrics=None,
        )

        def inc_trainer(current_date: str, d: RetrainDecision) -> Mapping[str, Any]:
            assert current_date == "2025-02-01"
            assert d.strategy == "incremental"
            return {"model_path": "models/latest_mtl.pt", "train_samples": 123, "val_ic": 0.045}

        monitor = PerformanceMonitor(history, {"monitoring": {"horizon": 5}}, incremental_trainer=inc_trainer)
        result = monitor.trigger_retrain(decision, current_date="2025-02-01")

        assert result["model_path"] == "models/latest_mtl.pt"
        assert result["train_samples"] == 123
        assert result["val_ic"] == pytest.approx(0.045)

        df = history.query_model_snapshots(limit=1)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["snapshot_date"] == "2025-02-01"
        assert row["model_type"] == "incremental"
        assert int(row["train_samples"]) == 123
        assert float(row["val_ic"]) == pytest.approx(0.045)


def test_trigger_retrain_skip_and_missing_trainer_errors() -> None:
    with RecommendationHistory(":memory:") as history:
        monitor = PerformanceMonitor(history, {"monitoring": {}})

        no = RetrainDecision(
            should_retrain=False,
            strategy="incremental",
            trigger_reason="ok",
            current_metrics=MonitoringMetrics("2025-01-01", "2025-01-02", 0.1, 0.6, 0.1, 0.0, 2),
            baseline_metrics=None,
        )
        assert monitor.trigger_retrain(no, "2025-01-02")["skipped"] is True

        yes = RetrainDecision(
            should_retrain=True,
            strategy="full",
            trigger_reason="ic_severe_degradation",
            current_metrics=no.current_metrics,
            baseline_metrics=None,
        )
        with pytest.raises(RuntimeError):
            monitor.trigger_retrain(yes, "2025-01-02")


def test_history_pipeline_runs_and_query_roundtrip() -> None:
    with RecommendationHistory(":memory:") as history:
        @dataclass(frozen=True)
        class _Run:
            run_date: str
            status: str
            steps_completed: list[str]
            steps_failed: list[str]
            error_messages: dict[str, str]
            execution_time_seconds: float
            created_at: str

        history.save_pipeline_run(
            _Run(
                run_date="2025-01-02",
                status="success",
                steps_completed=["a", "b"],
                steps_failed=[],
                error_messages={},
                execution_time_seconds=1.25,
                created_at="2025-01-02 09:00:00",
            )
        )
        df = history.query_pipeline_runs()
        assert len(df) == 1
        assert df.iloc[0]["run_date"] == "2025-01-02"
        assert df.iloc[0]["status"] == "success"


def test_monitor_config_parsing_and_internal_edge_branches() -> None:
    with RecommendationHistory(":memory:") as history:
        monitor = PerformanceMonitor(
            history,
            {
                "monitoring": {
                    "rolling_window_days": "bad",
                    "horizon": 5.0,
                    "ic_threshold": "bad",
                    "hit_rate_threshold": "0.55",
                    "retrain_threshold": {"consecutive_low_days": "bad"},
                }
            },
        )
        assert monitor.rolling_window_days == 20
        assert monitor.horizon == 5
        assert monitor.ic_threshold == pytest.approx(0.04)
        assert monitor.hit_rate_threshold == pytest.approx(0.55)
        assert monitor.consecutive_low_days == 5

        with pytest.raises(ValueError):
            monitor._metrics_from_df(pd.DataFrame())

        assert monitor._best_baseline_metrics("2025-01-02", window_days=20) is None

        _seed_validations(history, date(2025, 1, 1), [0.1] * 10)
        assert monitor._best_baseline_metrics("2025-01-10", window_days=20) is None

        empty_baseline = MonitoringMetrics("2025-01-01", "2025-01-01", 0.1, 0.6, 0.0, 0.0, 0)
        current = MonitoringMetrics("2025-01-01", "2025-01-01", 0.1, 0.6, 0.0, 0.0, 1)
        assert monitor.detect_degradation(current, empty_baseline) is False
        assert monitor._degradation_ratio(current, empty_baseline) == 0.0


def test_consecutive_low_checks_handle_insufficient_data() -> None:
    with RecommendationHistory(":memory:") as history:
        monitor = PerformanceMonitor(history, {"monitoring": {"horizon": 5}})
        assert monitor.check_consecutive_low_performance("2025-01-01", threshold_ic=0.04, consecutive_days=5) is False
        assert monitor._check_consecutive_low_hit_rate("2025-01-01", threshold_hit_rate=0.55, consecutive_days=5) is False

        dates = _seed_validations(history, date(2025, 1, 1), [0.01, 0.01, 0.01], [0.5, 0.5, 0.5])
        assert monitor.check_consecutive_low_performance(dates[-1], threshold_ic=0.04, consecutive_days=5) is False
        assert monitor._check_consecutive_low_hit_rate(dates[-1], threshold_hit_rate=0.55, consecutive_days=5) is False


def test_make_retrain_decision_reason_branches_low_ic_low_hit_degrade_and_strategy_normalization() -> None:
    with RecommendationHistory(":memory:") as history:
        # low_ic branch (avoid consecutive_low by requiring more days than available)
        dates = _seed_validations(history, date(2025, 1, 1), [0.03] * 20, [0.60] * 20)
        monitor_low_ic = PerformanceMonitor(
            history,
            {"monitoring": {"rolling_window_days": 20, "horizon": 5, "ic_threshold": 0.04, "retrain_threshold": {"consecutive_low_days": 50}}},
        )
        d1 = monitor_low_ic.make_retrain_decision(dates[-1])
        assert d1.should_retrain is True
        assert d1.trigger_reason == "ic_below_threshold"

    with RecommendationHistory(":memory:") as history2:
        # low_hit branch (avoid consecutive_low_hit by requiring more days than available)
        dates2 = _seed_validations(history2, date(2025, 2, 1), [0.06] * 20, [0.50] * 20)
        monitor_low_hit = PerformanceMonitor(
            history2,
            {"monitoring": {"rolling_window_days": 20, "horizon": 5, "hit_rate_threshold": 0.55, "retrain_threshold": {"consecutive_low_days": 50}}},
        )
        d2 = monitor_low_hit.make_retrain_decision(dates2[-1])
        assert d2.should_retrain is True
        assert d2.trigger_reason == "hit_rate_below_threshold"

    with RecommendationHistory(":memory:") as history3:
        # degrade branch (baseline 0.10 vs current 0.06 -> ratio 0.4, not severe)
        ics3 = [0.10] * 20 + [0.06] * 20
        hits3 = [0.60] * 40
        dates3 = _seed_validations(history3, date(2025, 3, 1), ics3, hits3)
        monitor_degrade = PerformanceMonitor(
            history3,
            {"monitoring": {"rolling_window_days": 20, "horizon": 5, "ic_threshold": 0.04, "retrain_threshold": {"ic_degrade_ratio": 0.3, "consecutive_low_days": 5}}},
        )
        d3 = monitor_degrade.make_retrain_decision(dates3[-1])
        assert d3.should_retrain is True
        assert d3.trigger_reason == "ic_degradation"

    with RecommendationHistory(":memory:") as history4:
        # strategy normalization branch when user config is unknown
        dates4 = _seed_validations(history4, date(2025, 4, 1), [0.08] * 25, [0.60] * 25)
        monitor_norm = PerformanceMonitor(history4, {"monitoring": {"rolling_window_days": 20, "horizon": 5, "retrain_strategy": "weird"}})
        d4 = monitor_norm.make_retrain_decision(dates4[-1])
        assert d4.should_retrain is False
        assert d4.strategy == "incremental"


def test_trigger_retrain_records_snapshot_even_without_val_ic() -> None:
    with RecommendationHistory(":memory:") as history:
        decision = RetrainDecision(
            should_retrain=True,
            strategy="incremental",
            trigger_reason="hit_rate_below_threshold",
            current_metrics=MonitoringMetrics("2025-01-01", "2025-01-20", 0.08, 0.5, 0.0, 0.0, 20),
            baseline_metrics=None,
        )

        def inc_trainer(_current_date: str, _d: RetrainDecision) -> Mapping[str, Any]:
            return {"checkpoint": "models/latest_mtl.pt", "train_samples": "12"}

        monitor = PerformanceMonitor(history, {"monitoring": {}}, incremental_trainer=inc_trainer)
        result = monitor.trigger_retrain(decision, current_date="2025-05-01")
        assert result["model_path"] == "models/latest_mtl.pt"
        assert result["train_samples"] == 12
        assert "val_ic" not in result

        df = history.query_model_snapshots(limit=1)
        assert len(df) == 1
        val = df.iloc[0]["val_ic"]
        assert pd.isna(val)
