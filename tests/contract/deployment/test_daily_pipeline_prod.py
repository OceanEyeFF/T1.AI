import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ashare_lab.pipeline.orchestrator import DailyPipelineOrchestrator, retry_with_backoff
from ashare_lab.recommendation import RecommendationHistory
from tests.support.toml_utils import dump_mapping_toml


class FakeUniverseFilter:
    def __init__(self, symbols: list[str]):
        self._symbols = list(symbols)

    def get_tradable_symbols(self, date: str):  # noqa: ARG002
        return [{"symbol": s, "name": f"N{s}"} for s in self._symbols]

    def is_allowed_a_share_symbol(self, symbol: str) -> bool:  # noqa: ARG002
        return True


class FakeFeatureBuilder:
    def __init__(self, meta_overrides: dict[str, dict] | None = None):
        self.meta_overrides = meta_overrides or {}

    def build_sequences(self, symbols: list[str], date: str):  # noqa: ARG002
        x = np.zeros((len(symbols), 30, 2), dtype="float32")
        meta = {}
        for idx, s in enumerate(symbols):
            meta[s] = {
                "name": f"N{s}",
                "volume": 100.0 + idx,
                "return_20d": 0.1,
                "rsi_14": 55.0,
                "volume_ratio": 1.2,
            }
            meta[s].update(self.meta_overrides.get(s, {}))
        return {"x": x, "meta": meta}


class FakeModel:
    def __init__(self, scores: list[float]):
        self.scores = list(scores)

    def __call__(self, x):  # noqa: ARG002
        arr = np.asarray(self.scores, dtype="float32")
        return {"pred_3d": arr, "pred_5d": arr * 0.9, "pred_10d": arr * 0.8}


class FakeDailyBarsSource:
    def __init__(self, raise_on_fetch: bool = False):
        self.refresh = False
        self.raise_on_fetch = bool(raise_on_fetch)
        self.calls: list[tuple] = []

    def fetch_daily_bars(self, symbols, start_date: str, end_date: str):
        self.calls.append((tuple(symbols), start_date, end_date, bool(self.refresh)))
        if self.raise_on_fetch:
            raise RuntimeError("boom_fetch_daily_bars")

        start = pd.to_datetime(start_date).normalize()
        end = pd.to_datetime(end_date).normalize()
        dates = pd.date_range(start, end, freq="B")
        out = {}
        for i, sym in enumerate(symbols):
            close = 10.0 + i + np.linspace(0.0, 1.0, num=len(dates))
            df = pd.DataFrame(
                {
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1000,
                    "amount": 1000,
                },
                index=dates,
            )
            df.index.name = "date"
            out[str(sym)] = df
        return out


class FakeCalendarSource:
    def __init__(self, empty: bool = False, raise_on_fetch: bool = False):
        self.refresh = False
        self.empty = bool(empty)
        self.raise_on_fetch = bool(raise_on_fetch)
        self.calls: list[tuple] = []

    def fetch_hs300_daily(self, start_date: str, end_date: str):
        self.calls.append((start_date, end_date, bool(self.refresh)))
        if self.raise_on_fetch:
            raise RuntimeError("boom_fetch_hs300")
        if self.empty:
            df = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])
            df.index.name = "date"
            return df
        start = pd.to_datetime(start_date).normalize()
        end = pd.to_datetime(end_date).normalize()
        dates = pd.date_range(start, end, freq="B")
        close = 4000.0 + np.linspace(0.0, 10.0, num=len(dates))
        df = pd.DataFrame(
            {
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1,
                "amount": 1,
            },
            index=dates,
        )
        df.index.name = "date"
        return df


def _write_pipeline_toml(tmp_path: Path, **overrides) -> Path:
    cfg = {
        "pipeline": {
            "default_top_n": 3,
            "default_horizons": [3, 5, 10],
            "recommendation_dir": str(tmp_path / "recs"),
            "report_dir": str(tmp_path / "reports"),
            "db_path": str(tmp_path / "recs.db"),
            "run_meta_path": str(tmp_path / "pipeline_runs.jsonl"),
        },
        "error_handling": {
            "retry_attempts": 3,
            "retry_backoff_seconds": [0, 0, 0],
            "allow_stale_data": True,
            "allow_training_skip": True,
            "allow_validation_skip": False,
        },
    }
    # shallow override is enough for tests
    for k, v in overrides.items():
        if k in cfg and isinstance(cfg[k], dict) and isinstance(v, dict):
            cfg[k].update(v)
        else:
            cfg[k] = v

    path = tmp_path / "pipeline.toml"
    path.write_text(dump_mapping_toml(cfg), encoding="utf-8")
    return path


def test_retry_with_backoff_retries_and_sleeps(monkeypatch):
    sleeps: list[int] = []
    monkeypatch.setattr("ashare_lab.pipeline.orchestrator.core.time.sleep", lambda s: sleeps.append(int(s)))

    calls = {"n": 0}

    @retry_with_backoff(max_attempts=3, backoff_seconds=[2, 5, 10], reraise=True)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("fail")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3
    assert sleeps == [2, 5]


def test_retry_with_backoff_invalid_params():
    with pytest.raises(ValueError):
        retry_with_backoff(max_attempts=0)
    with pytest.raises(ValueError):
        retry_with_backoff(max_attempts=1, backoff_seconds=[-1])


def test_retry_with_backoff_reraise_false_returns_none():
    calls = {"n": 0}

    @retry_with_backoff(max_attempts=2, backoff_seconds=[0], reraise=False)
    def always_fail():
        calls["n"] += 1
        raise RuntimeError("nope")

    assert always_fail() is None
    assert calls["n"] == 2


def test_orchestrator_end_to_end_success_with_validation(tmp_path):
    config_path = _write_pipeline_toml(tmp_path, error_handling={"allow_validation_skip": False})

    universe = FakeUniverseFilter(["000001", "000002", "600519"])
    feature_builder = FakeFeatureBuilder()
    model = FakeModel([0.12, 0.08, 0.05])
    data_source = FakeDailyBarsSource()
    calendar_source = FakeCalendarSource()

    # Pre-populate previous day's recommendations so validation can run.
    run_date = "2026-01-13"
    prev_date = "2026-01-12"
    with RecommendationHistory(tmp_path / "recs.db") as history:
        history.save_recommendations(
            {
                "date": prev_date,
                "5d": [
                    {"symbol": "000001", "predicted_return": 0.02, "rank": 1},
                    {"symbol": "000002", "predicted_return": 0.01, "rank": 2},
                ],
            }
        )

    orch = DailyPipelineOrchestrator(
        config_path=config_path,
        model=model,
        feature_builder=feature_builder,
        universe_filter=universe,
        data_source=data_source,
        calendar_source=calendar_source,
    )

    result = orch.run(run_date)

    assert result.status == "success"
    assert result.run_date == run_date
    assert result.steps_failed == []
    assert result.steps_completed == [
        "data_refresh",
        "recommendation_generation",
        "persistence",
        "validation",
        "record_run",
    ]

    rec_dir = tmp_path / "recs"
    assert (rec_dir / "20260113.json").exists()
    assert (rec_dir / "20260113_3d.csv").exists()
    assert (rec_dir / "20260113_5d.csv").exists()
    assert (rec_dir / "20260113_10d.csv").exists()
    assert (rec_dir / "20260113.md").exists()

    assert (tmp_path / "reports" / f"validation_{prev_date}_h5.json").exists()
    assert (tmp_path / "pipeline_runs.jsonl").exists()

    # Ensure run metadata is JSON-serializable.
    json.loads(json.dumps(asdict(result), ensure_ascii=False))


def test_orchestrator_graceful_degrade_on_data_refresh_failure(tmp_path):
    config_path = _write_pipeline_toml(tmp_path, error_handling={"allow_stale_data": True})

    universe = FakeUniverseFilter(["000001", "000002", "600519"])
    feature_builder = FakeFeatureBuilder()
    model = FakeModel([0.12, 0.08, 0.05])
    data_source = FakeDailyBarsSource(raise_on_fetch=True)
    calendar_source = FakeCalendarSource()

    orch = DailyPipelineOrchestrator(
        config_path=config_path,
        model=model,
        feature_builder=feature_builder,
        universe_filter=universe,
        data_source=data_source,
        calendar_source=calendar_source,
    )

    result = orch.run("20260113")
    assert result.status == "partial"
    assert "data_refresh" in result.steps_failed
    assert "recommendation_generation" in result.steps_completed
    assert (tmp_path / "recs" / "20260113.json").exists()
    assert (tmp_path / "pipeline_runs.jsonl").exists()


def test_orchestrator_validation_failure_fails_when_not_allowed(tmp_path):
    config_path = _write_pipeline_toml(tmp_path, error_handling={"allow_validation_skip": False})

    universe = FakeUniverseFilter(["000001", "000002", "600519"])
    feature_builder = FakeFeatureBuilder()
    model = FakeModel([0.12, 0.08, 0.05])
    data_source = FakeDailyBarsSource()
    calendar_source = FakeCalendarSource(raise_on_fetch=True)

    orch = DailyPipelineOrchestrator(
        config_path=config_path,
        model=model,
        feature_builder=feature_builder,
        universe_filter=universe,
        data_source=data_source,
        calendar_source=calendar_source,
    )

    # Seed prev day recommendations so validation attempts to fetch HS300.
    with RecommendationHistory(tmp_path / "recs.db") as history:
        history.save_recommendations(
            {"date": "2026-01-12", "5d": [{"symbol": "000001", "predicted_return": 0.1, "rank": 1}]}
        )

    result = orch.run("2026-01-13")
    assert result.status == "failed"
    assert "validation" in result.steps_failed
    # still records run meta even when failed
    assert (tmp_path / "pipeline_runs.jsonl").exists()


def test_orchestrator_record_run_failure_is_tolerated(tmp_path, monkeypatch):
    config_path = _write_pipeline_toml(tmp_path)

    universe = FakeUniverseFilter(["000001", "000002", "600519"])
    feature_builder = FakeFeatureBuilder()
    model = FakeModel([0.12, 0.08, 0.05])
    data_source = FakeDailyBarsSource()
    calendar_source = FakeCalendarSource(empty=True)  # avoid validation work

    orch = DailyPipelineOrchestrator(
        config_path=config_path,
        model=model,
        feature_builder=feature_builder,
        universe_filter=universe,
        data_source=data_source,
        calendar_source=calendar_source,
    )

    monkeypatch.setattr(orch, "_record_run", lambda run: (_ for _ in ()).throw(RuntimeError("boom_record")))
    result = orch.run("2026-01-13")
    assert result.status in {"success", "partial"}
    assert "record_run" in result.steps_failed


def test_internal_helpers_and_branches(tmp_path):
    import ashare_lab.pipeline.orchestrator.core as core

    # invalid config shape
    bad_cfg = tmp_path / "bad.toml"
    bad_cfg.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        DailyPipelineOrchestrator(
            config_path=bad_cfg,
            model=FakeModel([0.1, 0.2, 0.3]),
            feature_builder=FakeFeatureBuilder(),
            universe_filter=FakeUniverseFilter(["000001"]),
            data_source=FakeDailyBarsSource(),
            calendar_source=FakeCalendarSource(),
        )

    cfg = _write_pipeline_toml(tmp_path)
    orch = DailyPipelineOrchestrator(
        config_path=cfg,
        model=FakeModel([0.1, 0.2, 0.3]),
        feature_builder=FakeFeatureBuilder(),
        universe_filter=FakeUniverseFilter(["000001"]),
        data_source=FakeDailyBarsSource(),
        calendar_source=FakeCalendarSource(empty=True),
    )

    assert orch._graceful_degrade("training", RuntimeError("x")) is True
    assert orch._graceful_degrade("unknown_step", RuntimeError("x")) is False

    # _temporary_attr no-op branch (missing attribute)
    class _NoAttr:
        pass

    with core._temporary_attr(_NoAttr(), "missing", True):
        pass

    # _recommendation_to_row mapping + __dict__ + error branches
    assert core._recommendation_to_row({"symbol": "000001"})["symbol"] == "000001"

    class _Obj:
        def __init__(self):
            self.x = 1

    assert core._recommendation_to_row(_Obj())["x"] == 1
    with pytest.raises(TypeError):
        core._recommendation_to_row(123)

    # _write_csv empty rows
    out_csv = tmp_path / "empty.csv"
    orch._write_csv(out_csv, [])
    assert out_csv.read_text(encoding="utf-8") == ""

    # _save_validation_report mapping + else branches
    orch._save_validation_report("2026-01-12", {"validation_date": "2026-01-19", "hit_rate": 1.0}, horizon=5)
    orch._save_validation_report("2026-01-12", "oops", horizon=5)
