from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import torch

from ashare_lab.recommendation.engine import (
    RecommendationEngine,
    _confidence_map,
    _normalize_meta,
    _normalize_symbols_with_names,
    _to_1d_float_list,
    save_as_csv,
    save_as_json,
    save_as_markdown,
)
from ashare_lab.universe import is_allowed_a_share_symbol


def _make_symbols(n: int, start: int = 600000) -> list[str]:
    return [str(start + i).zfill(6) for i in range(n)]


class DummyUniverseFilter:
    def __init__(self, items: list[dict[str, str]]):
        self._items = items

    def get_tradable_symbols(self, date: str):  # noqa: ARG002 - API matches spec
        return list(self._items)

    def is_allowed_a_share_symbol(self, symbol: str) -> bool:
        return is_allowed_a_share_symbol(symbol)


class DummyFeatureBuilder:
    def __init__(self, meta: dict[str, dict]):
        self._meta = meta
        self.last_symbols: list[str] | None = None

    def build_sequences(self, symbols: list[str], date: str):  # noqa: ARG002 - API matches spec
        self.last_symbols = list(symbols)
        x = torch.zeros(len(symbols), 30, 6, dtype=torch.float32)
        meta = {s: dict(self._meta.get(s, {})) for s in symbols}
        return {"x": x, "meta": meta}

    def get_tradable_symbols(self, date: str):  # noqa: ARG002 - fallback universe API
        # Provide a minimal fallback path for tests.
        return [{"symbol": s, "name": self._meta.get(s, {}).get("name", "")} for s in self._meta.keys()]


class DummyMTLModel:
    def __init__(self, preds: dict[str, torch.Tensor], as_tuple: bool = False):
        self._preds = preds
        self._as_tuple = as_tuple

    def __call__(self, x):  # noqa: ARG002 - ignore x in deterministic dummy
        if self._as_tuple:
            return self._preds, {}
        return self._preds


def test_generate_recommendations_topn_and_independence():
    symbols = _make_symbols(25)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    # Add forbidden ones that must be filtered out
    st_symbol = "600999"
    items += [
        {"symbol": "688001", "name": "科创测试"},
        {"symbol": "300001", "name": "创业测试"},
        {"symbol": "830799", "name": "北交测试"},
        {"symbol": st_symbol, "name": "ST测试"},
    ]

    meta = {s: {"name": f"测试{s}"} for s in symbols}
    # Make one clearly strong for reasons
    meta[symbols[0]] |= {"rsi_14": 75.0, "return_20d": 0.20, "volume_ratio": 1.60, "volume": 1000}
    # Make another partially strong
    meta[symbols[1]] |= {"rsi_14": 60.0, "return_20d": 0.06, "volume_ratio": 1.2, "volume": 1000}
    # Make one suspended (should be filtered)
    meta[symbols[2]] |= {"volume": 0}

    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    # Independent rankings per horizon
    base = torch.linspace(0.0, 0.24, steps=len(symbols))
    preds = {
        "pred_3d": base.clone(),  # top should be last symbols
        "pred_5d": base.flip(0).clone(),  # top should be first symbols
        "pred_10d": (base.roll(5)).clone(),
    }
    # Add invalid prediction for one symbol (filtered across all horizons)
    preds["pred_3d"][5] = float("nan")
    preds["pred_5d"][5] = float("nan")
    preds["pred_10d"][5] = float("nan")

    model = DummyMTLModel(preds)
    engine = RecommendationEngine(model, fb, uf)
    recs = engine.generate_recommendations("20250115", top_n=10)

    assert set(recs.keys()) == {"3d", "5d", "10d"}
    assert all(len(v) == 10 for v in recs.values())

    # All items are allowed A-share symbols and not ST by name
    for horizon, items in recs.items():
        assert horizon in {"3d", "5d", "10d"}
        for r in items:
            assert is_allowed_a_share_symbol(r.symbol)
            assert "ST" not in r.name.upper()
            assert 0.0 <= r.confidence <= 1.0

    # Ensure feature_builder was called with filtered universe (forbidden not passed)
    assert fb.last_symbols is not None
    assert "688001" not in fb.last_symbols
    assert "300001" not in fb.last_symbols
    assert "830799" not in fb.last_symbols
    assert st_symbol not in fb.last_symbols  # ST by name excluded

    # Suspended symbol filtered
    assert symbols[2] not in {r.symbol for r in recs["3d"]}
    # NaN prediction symbol filtered
    assert symbols[5] not in {r.symbol for r in recs["3d"]}

    # Horizon independence: at least one difference between lists
    top3d = {r.symbol for r in recs["3d"]}
    top5d = {r.symbol for r in recs["5d"]}
    assert top3d != top5d


def test_extract_reason_includes_key_features():
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}"} for s in symbols}
    meta[symbols[0]] |= {"rsi_14": 75.0, "return_20d": 0.20, "volume_ratio": 1.60, "volume": 1000}
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    preds = {
        "pred_3d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_5d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_10d": torch.linspace(0.0, 0.11, steps=len(symbols)),
    }
    # Make the strong-featured symbol rank highest
    preds["pred_3d"][0] = 0.20
    preds["pred_5d"][0] = 0.20
    preds["pred_10d"][0] = 0.20

    engine = RecommendationEngine(DummyMTLModel(preds), fb, uf)
    recs = engine.generate_recommendations("20250115", top_n=10)
    top = recs["3d"][0]
    assert top.symbol == symbols[0]
    assert "RSI" in top.reason
    assert "动量" in top.reason
    assert "成交量" in top.reason


def test_output_formats_json_csv_markdown(tmp_path: Path):
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}", "volume": 1000} for s in symbols}
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    preds = {
        "pred_3d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_5d": torch.linspace(0.0, 0.11, steps=len(symbols)).flip(0),
        "pred_10d": torch.linspace(0.0, 0.11, steps=len(symbols)).roll(3),
    }

    engine = RecommendationEngine(DummyMTLModel(preds, as_tuple=True), fb, uf)
    recs = engine.generate_recommendations("20250115", top_n=10)

    json_path = save_as_json(recs, tmp_path / "recs.json")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {"date", "3d", "5d", "10d"}
    assert len(payload["3d"]) == 10
    assert payload["3d"][0]["rank"] == 1

    csv_paths = save_as_csv(recs, tmp_path / "csv")
    assert set(csv_paths.keys()) >= {"3d", "5d", "10d"}
    for horizon, p in csv_paths.items():
        with p.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 10
        assert set(rows[0].keys()) == {
            "rank",
            "symbol",
            "name",
            "predicted_return",
            "confidence",
            "reason",
        }
        assert horizon in {"3d", "5d", "10d"}

    md_path = save_as_markdown(recs, tmp_path / "recs.md")
    md = md_path.read_text(encoding="utf-8")
    assert "| 排名 | 代码 | 名称 | 预测收益 | 置信度 | 推荐理由 |" in md
    assert "## 3D 推荐（3d）" in md
    assert "## 5D 推荐（5d）" in md
    assert "## 10D 推荐（10d）" in md


def test_universe_fallback_to_feature_builder():
    symbols = _make_symbols(12)
    meta = {s: {"name": f"测试{s}", "volume": 1000} for s in symbols}
    fb = DummyFeatureBuilder(meta)

    # Use the universe module as universe_filter: it provides is_allowed_a_share_symbol only.
    import ashare_lab.universe as universe_module

    preds = {
        "pred_3d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_5d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_10d": torch.linspace(0.0, 0.11, steps=len(symbols)),
    }
    engine = RecommendationEngine(DummyMTLModel(preds), fb, universe_module)
    recs = engine.generate_recommendations("20250115", top_n=10)
    assert len(recs["3d"]) == 10


def test_error_handling_model_failure_and_invalid_topn():
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}", "volume": 1000} for s in symbols}
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    class FailingModel:
        def __call__(self, x):  # noqa: ARG002
            raise RuntimeError("boom")

    engine = RecommendationEngine(FailingModel(), fb, uf)
    with pytest.raises(RuntimeError, match="Model inference failed"):
        engine.generate_recommendations("20250115", top_n=10)

    engine_ok = RecommendationEngine(
        DummyMTLModel(
            {"pred_3d": torch.zeros(12), "pred_5d": torch.zeros(12), "pred_10d": torch.zeros(12)}
        ),
        fb,
        uf,
    )
    with pytest.raises(ValueError, match="top_n must be positive"):
        engine_ok.generate_recommendations("20250115", top_n=0)


def test_missing_prediction_key_raises():
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}", "volume": 1000} for s in symbols}
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    preds = {"pred_3d": torch.zeros(len(symbols)), "pred_5d": torch.zeros(len(symbols))}
    engine = RecommendationEngine(DummyMTLModel(preds), fb, uf)
    with pytest.raises(ValueError, match="missing required key"):
        engine.generate_recommendations("20250115", top_n=10)


def test_init_none_raises():
    fb = DummyFeatureBuilder({})
    uf = DummyUniverseFilter([])
    with pytest.raises(ValueError, match="model must not be None"):
        RecommendationEngine(None, fb, uf)
    with pytest.raises(ValueError, match="feature_builder must not be None"):
        RecommendationEngine(object(), None, uf)
    with pytest.raises(ValueError, match="universe_filter must not be None"):
        RecommendationEngine(object(), fb, None)


def test_empty_universe_after_filter_raises():
    # Only forbidden codes + ST names
    uf = DummyUniverseFilter(
        [
            {"symbol": "688001", "name": "科创测试"},
            {"symbol": "300001", "name": "创业测试"},
            {"symbol": "830799", "name": "北交测试"},
            {"symbol": "600000", "name": "ST测试"},
        ]
    )
    fb = DummyFeatureBuilder({})
    preds = {"pred_3d": torch.zeros(1), "pred_5d": torch.zeros(1), "pred_10d": torch.zeros(1)}
    engine = RecommendationEngine(DummyMTLModel(preds), fb, uf)
    with pytest.raises(ValueError, match="No tradable symbols after filtering"):
        engine.generate_recommendations("20250115", top_n=10)


def test_insufficient_valid_symbols_raises():
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}", "volume": 1000} for s in symbols}
    # Mark many as suspended
    for s in symbols[:5]:
        meta[s]["is_suspended"] = True
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)
    preds = {
        "pred_3d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_5d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_10d": torch.linspace(0.0, 0.11, steps=len(symbols)),
    }
    engine = RecommendationEngine(DummyMTLModel(preds), fb, uf)
    with pytest.raises(ValueError, match="Not enough valid symbols"):
        engine.generate_recommendations("20250115", top_n=10)


def test_prediction_length_mismatch_raises():
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    meta = {s: {"name": f"测试{s}", "volume": 1000} for s in symbols}
    fb = DummyFeatureBuilder(meta)
    uf = DummyUniverseFilter(items)

    preds = {
        "pred_3d": torch.zeros(len(symbols)),
        "pred_5d": torch.zeros(len(symbols) - 1),  # mismatch
        "pred_10d": torch.zeros(len(symbols)),
    }
    engine = RecommendationEngine(DummyMTLModel(preds), fb, uf)
    with pytest.raises(ValueError, match="Prediction length mismatch"):
        engine.generate_recommendations("20250115", top_n=10)


def test_feature_builder_variants_and_errors():
    symbols = _make_symbols(12)
    items = [{"symbol": s, "name": f"测试{s}"} for s in symbols]
    uf = DummyUniverseFilter(items)
    preds = {
        "pred_3d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_5d": torch.linspace(0.0, 0.11, steps=len(symbols)),
        "pred_10d": torch.linspace(0.0, 0.11, steps=len(symbols)),
    }
    model = DummyMTLModel(preds)

    class TupleFeatureBuilder:
        def build_sequences(self, symbols_in: list[str], date: str):  # noqa: ARG002
            x = torch.zeros(len(symbols_in), 30, 6)
            meta = None  # exercise _normalize_meta(None, ...)
            return x, meta

    engine = RecommendationEngine(model, TupleFeatureBuilder(), uf)
    recs = engine.generate_recommendations("20250115", top_n=10)
    assert len(recs["3d"]) == 10

    class PlainFeatureBuilder:
        def build_sequences(self, symbols_in: list[str], date: str):  # noqa: ARG002
            return torch.zeros(len(symbols_in), 30, 6)

    engine = RecommendationEngine(model, PlainFeatureBuilder(), uf)
    recs = engine.generate_recommendations("20250115", top_n=10)
    assert len(recs["5d"]) == 10

    def callable_builder(symbols_in: list[str], date: str):  # noqa: ARG001,ARG002
        return {"x": torch.zeros(len(symbols_in), 30, 6), "meta": {}}

    engine = RecommendationEngine(model, callable_builder, uf)
    recs = engine.generate_recommendations("20250115", top_n=10)
    assert len(recs["10d"]) == 10

    class BadMetaBuilder:
        def build_sequences(self, symbols_in: list[str], date: str):  # noqa: ARG002
            return {"x": torch.zeros(len(symbols_in), 30, 6), "meta": ["bad"]}

    engine = RecommendationEngine(model, BadMetaBuilder(), uf)
    with pytest.raises(ValueError, match="Unsupported meta type"):
        engine.generate_recommendations("20250115", top_n=10)

    class NotCallableNoMethod:
        pass

    engine = RecommendationEngine(model, NotCallableNoMethod(), uf)
    with pytest.raises(ValueError, match="feature_builder must be callable"):
        engine.generate_recommendations("20250115", top_n=10)


def test_universe_normalization_and_helpers():
    assert _normalize_symbols_with_names({"600000": "测试"}) == [("600000", "测试")]
    assert _normalize_symbols_with_names([("600000", "测试")]) == [("600000", "测试")]
    assert _normalize_symbols_with_names(["600000"]) == [("600000", "")]
    assert _normalize_symbols_with_names("600000") == [("600000", "")]
    assert _normalize_meta(None, ["600000"]) == {"600000": {}}

    with pytest.raises(ValueError, match="missing 'symbol'"):
        _normalize_symbols_with_names([{"name": "缺少代码"}])
    with pytest.raises(ValueError, match="Unsupported universe type"):
        _normalize_symbols_with_names(123)

    assert _to_1d_float_list([1, 2, 3]) == [1.0, 2.0, 3.0]
    with pytest.raises(ValueError, match="Unsupported prediction type"):
        _to_1d_float_list(object())

    assert _confidence_map([("a", 1.0)], []) == {}
