"""Production-grade daily pipeline orchestrator (Phase 3).

Canonical implementation for `ashare_lab.pipeline.orchestrator`.

Five stages:
1) data refresh
2) recommendation generation
3) persistence
4) validation (previous trading day)
5) run metadata recording
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

from ashare_lab.recommendation import RecommendationEngine, RecommendationHistory, RecommendationValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineRun:
    run_date: str  # YYYY-MM-DD
    status: str  # success / partial / failed
    steps_completed: list[str]
    steps_failed: list[str]
    error_messages: dict[str, str]
    execution_time_seconds: float
    created_at: str


@dataclass(frozen=True, slots=True)
class _PipelineSettings:
    default_top_n: int = 10
    default_horizons: tuple[int, ...] = (3, 5, 10)
    recommendation_dir: Path = Path("data/recommendations")
    report_dir: Path = Path("data/recommendations/validation")
    db_path: Path = Path("data/recommendations.db")
    run_meta_path: Path = Path("logs/pipeline_runs.jsonl")


@dataclass(frozen=True, slots=True)
class _ErrorHandlingSettings:
    retry_attempts: int = 3
    retry_backoff_seconds: tuple[int, ...] = (2, 5, 10)
    allow_stale_data: bool = True
    allow_training_skip: bool = True
    allow_validation_skip: bool = False


def _coerce_path(value: Any, default: Path) -> Path:
    if value in (None, ""):
        return default
    return Path(str(value))


def _load_pipeline_settings(config: Mapping[str, Any]) -> tuple[_PipelineSettings, _ErrorHandlingSettings]:
    pipeline = dict(config.get("pipeline") or {})
    error_handling = dict(config.get("error_handling") or {})

    settings = _PipelineSettings(
        default_top_n=int(pipeline.get("default_top_n", 10)),
        default_horizons=tuple(int(x) for x in (pipeline.get("default_horizons") or [3, 5, 10])),
        recommendation_dir=_coerce_path(pipeline.get("recommendation_dir"), Path("data/recommendations")),
        report_dir=_coerce_path(pipeline.get("report_dir"), Path("data/recommendations/validation")),
        db_path=_coerce_path(pipeline.get("db_path"), Path("data/recommendations.db")),
        run_meta_path=_coerce_path(pipeline.get("run_meta_path"), Path("logs/pipeline_runs.jsonl")),
    )

    retry_backoff = error_handling.get("retry_backoff_seconds") or [2, 5, 10]
    eh = _ErrorHandlingSettings(
        retry_attempts=int(error_handling.get("retry_attempts", 3)),
        retry_backoff_seconds=tuple(int(x) for x in retry_backoff),
        allow_stale_data=bool(error_handling.get("allow_stale_data", True)),
        allow_training_skip=bool(error_handling.get("allow_training_skip", True)),
        allow_validation_skip=bool(error_handling.get("allow_validation_skip", False)),
    )
    return settings, eh


def _to_iso_date(date_like: str) -> str:
    s = str(date_like).strip()
    if not s:
        raise ValueError("date is required")
    # accept YYYYMMDD or YYYY-MM-DD
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")
    return datetime.fromisoformat(s).date().strftime("%Y-%m-%d")


def _to_yyyymmdd(date_like: str) -> str:
    iso = _to_iso_date(date_like)
    return datetime.fromisoformat(iso).strftime("%Y%m%d")


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_seconds: list[int] | tuple[int, ...] = (2, 5, 10),
    reraise: bool = True,
):
    """Retry a callable with backoff.

    - max_attempts includes the first attempt.
    - backoff_seconds is a schedule; if attempts exceed its length, the last value is reused.
    """

    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    schedule = [int(x) for x in backoff_seconds] if backoff_seconds else [0]
    if any(x < 0 for x in schedule):
        raise ValueError("backoff_seconds must be non-negative")

    def decorator(func: Callable[..., Any]):
        import functools

        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - retry wrapper
                    last_exc = exc
                    if attempt >= max_attempts:
                        break
                    delay = schedule[min(attempt - 1, len(schedule) - 1)]
                    logger.warning(
                        "retry_with_backoff: attempt %s/%s failed: %s (sleep %ss)",
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    if delay:
                        time.sleep(delay)
            if reraise and last_exc is not None:
                raise last_exc
            return None

        return wrapped

    return decorator


@contextmanager
def _temporary_attr(obj: Any, name: str, value: Any):
    if obj is None or not hasattr(obj, name):
        yield
        return
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        try:
            setattr(obj, name, old)
        except Exception:  # pragma: no cover - defensive restore
            pass


def _recommendation_to_row(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
        return dict(item.to_dict())
    if hasattr(item, "__dict__"):
        return dict(item.__dict__)
    if isinstance(item, Mapping):
        return dict(item)
    raise TypeError(f"Unsupported recommendation type: {type(item)!r}")


class DailyPipelineOrchestrator:
    """Orchestrate production daily pipeline with dependency injection."""

    def __init__(
        self,
        config_path: str | Path,
        model: Any,
        feature_builder: Any,
        universe_filter: Any,
        data_source: Any,
        calendar_source: Any,
    ) -> None:
        self.config_path = Path(config_path)
        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, Mapping):
            raise ValueError("pipeline config must be a mapping")

        self.pipeline, self.error_handling = _load_pipeline_settings(raw)

        self.model = model
        self.feature_builder = feature_builder
        self.universe_filter = universe_filter
        self.data_source = data_source
        self.calendar_source = calendar_source

        self._step_logs: dict[str, dict[str, Any]] = {}

    def run(self, target_date: str, skip_training: bool = False, dry_run: bool = False) -> PipelineRun:
        del skip_training  # reserved for task-3.2 integration

        started = time.monotonic()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_date = _to_iso_date(target_date)
        run_yyyymmdd = _to_yyyymmdd(target_date)

        steps_completed: list[str] = []
        steps_failed: list[str] = []
        error_messages: dict[str, str] = {}

        recommendations: dict[str, list[Any]] | None = None
        status = "success"
        proceed = True

        def fail(step: str, exc: Exception, allow_continue: bool) -> bool:
            nonlocal status
            steps_failed.append(step)
            error_messages[step] = str(exc)
            self._log_step(step, "failed", error=exc)
            if allow_continue:
                status = "partial"
                return True
            status = "failed"
            return False

        # 1) data refresh
        step = "data_refresh"
        if proceed:
            try:
                if not dry_run:
                    refresher = retry_with_backoff(
                        max_attempts=self.error_handling.retry_attempts,
                        backoff_seconds=list(self.error_handling.retry_backoff_seconds),
                        reraise=True,
                    )(self._refresh_data_once)
                    refresher(run_date, run_yyyymmdd)
                self._log_step(step, "success")
                steps_completed.append(step)
            except Exception as exc:  # noqa: BLE001
                proceed = fail(step, exc, allow_continue=self._graceful_degrade(step, exc))

        # 2) recommendation generation
        step = "recommendation_generation"
        if proceed:
            try:
                engine = RecommendationEngine(self.model, self.feature_builder, self.universe_filter)
                recommendations = engine.generate_recommendations(run_yyyymmdd, top_n=self.pipeline.default_top_n)
                self._log_step(step, "success")
                steps_completed.append(step)
            except Exception as exc:  # noqa: BLE001
                proceed = fail(step, exc, allow_continue=False)

        # 3) persistence
        step = "persistence"
        history: RecommendationHistory | None = None
        if proceed:
            try:
                history = RecommendationHistory(self.pipeline.db_path)
                payload = {"date": run_date, **(recommendations or {})}
                history.save_recommendations(payload)
                self._save_recommendation_artifacts(run_yyyymmdd, run_date, recommendations or {})
                self._log_step(step, "success")
                steps_completed.append(step)
            except Exception as exc:  # noqa: BLE001
                proceed = fail(step, exc, allow_continue=False)

        # 4) validation (previous trading day)
        step = "validation"
        if proceed:
            try:
                if dry_run:
                    prev_date = None
                else:
                    prev_date = self._previous_trading_day(run_date)

                if prev_date and history is not None:
                    rec_df = history.query_recommendations(start_date=prev_date, end_date=prev_date)
                    if rec_df is None or rec_df.empty:
                        logger.info("No previous recommendations found for %s, skip validation", prev_date)
                    else:
                        rec_items = [
                            {
                                "symbol": str(row["symbol"]),
                                "predicted_return": float(row["score"]),
                                "rank": int(row["rank"]),
                            }
                            for _, row in rec_df.iterrows()
                        ]
                        validator = RecommendationValidator(self.data_source, calendar_source=self.calendar_source)
                        validate_call = retry_with_backoff(
                            max_attempts=self.error_handling.retry_attempts,
                            backoff_seconds=list(self.error_handling.retry_backoff_seconds),
                            reraise=True,
                        )(validator.validate)
                        result = validate_call(
                            {"date": prev_date, "recommendations": rec_items},
                            validation_horizon=5,
                            recommendation_date=prev_date,
                        )
                        history.save_validation_results(prev_date, result, horizon=5)
                        self._save_validation_report(prev_date, result, horizon=5)

                self._log_step(step, "success")
                steps_completed.append(step)
            except Exception as exc:  # noqa: BLE001
                proceed = fail(step, exc, allow_continue=self._graceful_degrade(step, exc))

        if history is not None:
            try:
                history.close()
            except Exception:  # pragma: no cover - defensive close
                pass

        # 5) record run metadata
        step = "record_run"
        try:
            steps_completed.append(step)
            pipeline_run = self._finalize_run(
                run_date, status, steps_completed, steps_failed, error_messages, started, created_at
            )
            self._record_run(pipeline_run)
            self._log_step(step, "success")
        except Exception as exc:  # noqa: BLE001
            if step in steps_completed:
                steps_completed.remove(step)
            # Do not fail the pipeline because of logging; record as a step failure.
            steps_failed.append(step)
            error_messages[step] = str(exc)
            self._log_step(step, "failed", error=exc)
            if status == "success":
                status = "partial"
        return self._finalize_run(
            run_date, status, steps_completed, steps_failed, error_messages, started, created_at
        )

    def _graceful_degrade(self, step_name: str, error: Exception) -> bool:
        del error
        if step_name == "data_refresh":
            return bool(self.error_handling.allow_stale_data)
        if step_name == "validation":
            return bool(self.error_handling.allow_validation_skip)
        if step_name == "training":
            return bool(self.error_handling.allow_training_skip)
        return False

    def _refresh_data_once(self, run_date_iso: str, run_yyyymmdd: str) -> None:
        del run_yyyymmdd
        symbols = self._get_universe_symbols(run_date_iso)
        if not symbols:
            raise ValueError("universe is empty")

        with _temporary_attr(self.data_source, "refresh", True):
            self.data_source.fetch_daily_bars(symbols, start_date=run_date_iso, end_date=run_date_iso)
        with _temporary_attr(self.calendar_source, "refresh", True):
            self.calendar_source.fetch_hs300_daily(start_date=run_date_iso, end_date=run_date_iso)

    def _get_universe_symbols(self, run_date_iso: str) -> list[str]:
        run_yyyymmdd = _to_yyyymmdd(run_date_iso)
        getter = getattr(self.universe_filter, "get_tradable_symbols", None)
        if not callable(getter):
            raise ValueError("universe_filter must provide get_tradable_symbols(date)")
        raw = getter(run_yyyymmdd)
        if raw is None:
            return []

        symbols: list[str] = []
        if isinstance(raw, Mapping):
            symbols = [str(k) for k in raw.keys()]
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            for item in raw:
                if isinstance(item, str):
                    symbols.append(item)
                elif isinstance(item, Mapping):
                    sym = item.get("symbol") or item.get("code") or item.get("代码")
                    if sym is not None:
                        symbols.append(str(sym))
                elif isinstance(item, tuple) and len(item) == 2:
                    symbols.append(str(item[0]))
        else:
            symbols = [str(raw)]

        return [s for s in symbols if s]

    def _previous_trading_day(self, run_date_iso: str) -> str | None:
        import pandas as pd

        current = pd.to_datetime(run_date_iso).normalize()
        start = (current - timedelta(days=30)).strftime("%Y-%m-%d")
        end = current.strftime("%Y-%m-%d")
        df = self.calendar_source.fetch_hs300_daily(start, end)
        if df is None or df.empty:
            return None
        idx = pd.to_datetime(df.index).normalize()
        prev = idx[idx < current]
        if prev.empty:
            return None
        return prev.max().strftime("%Y-%m-%d")

    def _save_recommendation_artifacts(
        self, run_yyyymmdd: str, run_date_iso: str, recommendations: Mapping[str, Sequence[Any]]
    ) -> None:
        out_dir = self.pipeline.recommendation_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "date": run_date_iso,
            "3d": [_recommendation_to_row(x) for x in recommendations.get("3d", [])],
            "5d": [_recommendation_to_row(x) for x in recommendations.get("5d", [])],
            "10d": [_recommendation_to_row(x) for x in recommendations.get("10d", [])],
        }
        (out_dir / f"{run_yyyymmdd}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        for horizon in ("3d", "5d", "10d"):
            items = payload.get(horizon) or []
            csv_path = out_dir / f"{run_yyyymmdd}_{horizon}.csv"
            self._write_csv(csv_path, items)

        md_path = out_dir / f"{run_yyyymmdd}.md"
        md_path.write_text(self._to_markdown(payload), encoding="utf-8")

    def _save_validation_report(self, rec_date: str, validation_result: Any, horizon: int) -> None:
        out_dir = self.pipeline.report_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        if hasattr(validation_result, "validation_date"):
            validation_date = str(getattr(validation_result, "validation_date"))
            result_dict = asdict(validation_result) if hasattr(validation_result, "__dataclass_fields__") else None
        elif isinstance(validation_result, Mapping):
            validation_date = str(validation_result.get("validation_date", ""))
            result_dict = dict(validation_result)
        else:
            validation_date = ""
            result_dict = {"result": str(validation_result)}

        payload = {
            "rec_date": rec_date,
            "validation_date": validation_date,
            "horizon": int(horizon),
            "result": result_dict,
        }
        (out_dir / f"validation_{rec_date}_h{horizon}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _record_run(self, pipeline_run: PipelineRun) -> None:
        path = self.pipeline.run_meta_path
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(pipeline_run), ensure_ascii=False, sort_keys=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()

        logger.info("PipelineRun: %s", line)

    def _finalize_run(
        self,
        run_date: str,
        status: str,
        steps_completed: list[str],
        steps_failed: list[str],
        error_messages: dict[str, str],
        started: float,
        created_at: str,
    ) -> PipelineRun:
        elapsed = time.monotonic() - started
        return PipelineRun(
            run_date=run_date,
            status=status,
            steps_completed=list(steps_completed),
            steps_failed=list(steps_failed),
            error_messages=dict(error_messages),
            execution_time_seconds=float(elapsed),
            created_at=created_at,
        )

    def _log_step(self, step_name: str, status: str, error: Exception | None = None) -> None:
        payload = {"status": status, "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        if error is not None:
            payload["error"] = str(error)
        self._step_logs[step_name] = payload
        if error is None:
            logger.info("step=%s status=%s", step_name, status)
        else:
            logger.warning("step=%s status=%s error=%s", step_name, status, error)

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        import csv

        if not rows:
            path.write_text("", encoding="utf-8")
            return
        # stable header order
        preferred = ["rank", "symbol", "name", "predicted_return", "confidence", "reason"]
        fieldnames = [c for c in preferred if c in rows[0]]
        for key in rows[0].keys():
            if key not in fieldnames:
                fieldnames.append(key)

        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    @staticmethod
    def _to_markdown(payload: Mapping[str, Any]) -> str:
        lines: list[str] = []
        lines.append("# Daily Recommendations\n\n")
        lines.append(f"**Date:** {payload.get('date', '')}\n\n")
        for horizon in ("3d", "5d", "10d"):
            items = payload.get(horizon) or []
            lines.append(f"## {horizon.upper()}\n\n")
            lines.append("| rank | symbol | name | predicted_return | confidence | reason |\n")
            lines.append("|---:|---|---|---:|---:|---|\n")
            for item in items:
                rank = item.get("rank", "")
                sym = item.get("symbol", "")
                name = item.get("name", "")
                pr = item.get("predicted_return", "")
                conf = item.get("confidence", "")
                reason = str(item.get("reason", "")).replace("\n", " ")
                lines.append(f"| {rank} | {sym} | {name} | {pr} | {conf} | {reason} |\n")
            lines.append("\n")
        return "".join(lines)
