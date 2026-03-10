"""Recommendation engine for multi-horizon stock ranking.

The engine relies on dependency injection:
- ``model``: typically :class:`ashare_lab.models.transformer.MTLTransformer` (or compatible callable).
- ``feature_builder``: builds model input tensors and per-symbol metadata used for explanations.
- ``universe_filter``: provides the universe list and/or an A-share symbol filter.

It generates 3 independent Top-N lists for 3/5/10 trading-day horizons, with basic sanity filtering
for non-finite/extreme predictions and suspended stocks (volume=0).
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from ashare_lab.trend_schema import PRIMARY_TREND_HORIZONS, PRIMARY_TREND_PRED_COLS

from .trend_aggregation import (
    AggregatedTrendScore,
    TrendAggregationConfig,
    aggregate_primary_trend_scores,
    rank_primary_trend_scores,
)

try:  # torch is a project dependency, but keep import optional for lightweight unit tests.
    import torch
except Exception:  # pragma: no cover - defensive import
    torch = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Single ranked recommendation item."""

    rank: int
    symbol: str
    name: str
    predicted_return: float
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return asdict(self)


class RecommendationEngine:
    """Generate multi-horizon Top-N recommendation lists.

    Args:
        model: A callable model. For MTLTransformer, calling ``model(x)`` returns a mapping
            with keys ``pred_3d``, ``pred_5d``, ``pred_10d``.
        feature_builder: Builds model input and per-symbol feature metadata.
            Expected to provide ``build_sequences(symbols, date)``.
        universe_filter: Provides tradable symbols and/or A-share filtering.
            If it has ``get_tradable_symbols(date)``, that will be used as the universe source.
            If it has ``is_allowed_a_share_symbol(symbol)``, it will be used for symbol filtering.
    """

    def __init__(self, model: Any, feature_builder: Any, universe_filter: Any):
        if model is None:
            raise ValueError("model must not be None")
        if feature_builder is None:
            raise ValueError("feature_builder must not be None")
        if universe_filter is None:
            raise ValueError("universe_filter must not be None")

        self.model = model
        self.feature_builder = feature_builder
        self.universe_filter = universe_filter

    def generate_recommendations(self, date: str, top_n: int = 10) -> dict[str, list[Recommendation]]:
        """Generate three independent Top-N lists.

        Args:
            date: Recommendation date, typically ``YYYYMMDD``.
            top_n: Number of items per list.

        Returns:
            A mapping: ``{"3d": [...], "5d": [...], "10d": [...]}``.

        Raises:
            ValueError: If universe/features/predictions are invalid.
            RuntimeError: If model inference fails.
        """
        if top_n <= 0:
            raise ValueError("top_n must be positive")

        symbols_with_names = self._get_universe(date)
        filtered = [(s, n) for s, n in symbols_with_names if self._is_allowed_symbol(s, n)]
        if not filtered:
            raise ValueError("No tradable symbols after filtering")

        symbols = [s for s, _ in filtered]
        names = {s: n for s, n in filtered}

        x, meta = self._build_features(symbols, date)
        predictions = self._infer(x)

        pred_by_horizon = {
            f"{horizon}d": predictions[pred_col]
            for horizon, pred_col in zip(PRIMARY_TREND_HORIZONS, PRIMARY_TREND_PRED_COLS)
        }

        valid_mask = self._valid_prediction_mask(symbols, meta, pred_by_horizon)
        valid_symbols = [s for s, ok in zip(symbols, valid_mask) if ok]
        if len(valid_symbols) < top_n:
            raise ValueError(f"Not enough valid symbols for Top-{top_n}: got {len(valid_symbols)}")

        out: dict[str, list[Recommendation]] = {}
        for horizon, pred_values in pred_by_horizon.items():
            all_scores = [
                (s, float(v))
                for s, v, ok in zip(symbols, _to_1d_float_list(pred_values), valid_mask)
                if ok
            ]
            all_scores_sorted = sorted(all_scores, key=lambda kv: kv[1], reverse=True)
            top = all_scores_sorted[:top_n]
            conf = _confidence_map(all_scores, top)

            recs: list[Recommendation] = []
            for rank, (symbol, score) in enumerate(top, start=1):
                symbol_meta = meta.get(symbol, {})
                recs.append(
                    Recommendation(
                        rank=rank,
                        symbol=symbol,
                        name=str(symbol_meta.get("name") or names.get(symbol) or ""),
                        predicted_return=score,
                        confidence=conf[symbol],
                        reason=self._extract_reason(symbol, symbol_meta),
                    )
                )
            out[horizon] = recs

        return out

    def generate_trend_recommendations(
        self,
        date: str,
        top_n: int = 10,
        *,
        aggregation_config: TrendAggregationConfig | None = None,
    ) -> tuple[list[Recommendation], dict[str, AggregatedTrendScore]]:
        """Generate a single aggregated main-line trend ranking."""
        if top_n <= 0:
            raise ValueError("top_n must be positive")

        symbols_with_names = self._get_universe(date)
        filtered = [(s, n) for s, n in symbols_with_names if self._is_allowed_symbol(s, n)]
        if not filtered:
            raise ValueError("No tradable symbols after filtering")

        symbols = [s for s, _ in filtered]
        names = {s: n for s, n in filtered}

        x, meta = self._build_features(symbols, date)
        predictions = self._infer(x)

        pred_by_horizon = {
            f"{horizon}d": predictions[pred_col]
            for horizon, pred_col in zip(PRIMARY_TREND_HORIZONS, PRIMARY_TREND_PRED_COLS)
        }
        valid_mask = self._valid_prediction_mask(symbols, meta, pred_by_horizon)

        valid_symbols = [s for s, ok in zip(symbols, valid_mask) if ok]
        if len(valid_symbols) < top_n:
            raise ValueError(f"Not enough valid symbols for Top-{top_n}: got {len(valid_symbols)}")

        filtered_predictions = {
            pred_col: [value for value, ok in zip(_to_1d_float_list(predictions[pred_col]), valid_mask) if ok]
            for pred_col in PRIMARY_TREND_PRED_COLS
        }
        filtered_meta = {symbol: meta.get(symbol, {}) for symbol in valid_symbols}

        aggregated = aggregate_primary_trend_scores(valid_symbols, filtered_predictions, aggregation_config)
        ranked = rank_primary_trend_scores(aggregated)
        selected = ranked[:top_n]

        all_scores = [(item.symbol, float(item.aggregate_score)) for item in ranked if math.isfinite(item.aggregate_score)]
        top_scores = [(item.symbol, float(item.aggregate_score)) for item in selected if math.isfinite(item.aggregate_score)]
        conf = _confidence_map(all_scores, top_scores)

        recs: list[Recommendation] = []
        diagnostics: dict[str, AggregatedTrendScore] = {}
        for rank, item in enumerate(selected, start=1):
            diagnostics[item.symbol] = item
            symbol_meta = filtered_meta.get(item.symbol, {})
            reason = self._extract_reason(item.symbol, symbol_meta)
            contrib = item.weighted_contributions
            reason = (
                f"主线聚合(3d={contrib['3d']:.2f}, 5d={contrib['5d']:.2f}, 10d={contrib['10d']:.2f}) | {reason}"
            )
            recs.append(
                Recommendation(
                    rank=rank,
                    symbol=item.symbol,
                    name=str(symbol_meta.get("name") or names.get(item.symbol) or ""),
                    predicted_return=float(item.aggregate_score),
                    confidence=float(conf.get(item.symbol, 0.5)),
                    reason=reason,
                )
            )

        return recs, diagnostics

    def _get_universe(self, date: str) -> list[tuple[str, str]]:
        """Get universe as a list of (symbol, name)."""
        getter = getattr(self.universe_filter, "get_tradable_symbols", None)
        if callable(getter):
            raw = getter(date)
        else:
            fallback = getattr(self.feature_builder, "get_tradable_symbols", None) or getattr(
                self.feature_builder, "get_universe", None
            )
            if not callable(fallback):
                raise ValueError(
                    "universe_filter must provide get_tradable_symbols(date) or feature_builder must "
                    "provide get_tradable_symbols/get_universe"
                )
            raw = fallback(date)

        return _normalize_symbols_with_names(raw)

    def _is_allowed_symbol(self, symbol: str, name: str | None) -> bool:
        """Apply hard constraints: A-share code rule + ST exclusion (by name if available)."""
        checker = getattr(self.universe_filter, "is_allowed_a_share_symbol", None)
        if callable(checker) and not bool(checker(symbol)):
            return False

        if name and "ST" in name.upper():
            return False

        return True

    def _build_features(self, symbols: list[str], date: str) -> tuple[Any, dict[str, dict[str, Any]]]:
        """Build model input and feature meta.

        The feature_builder is expected to provide one of:
        - build_sequences(symbols, date) -> x
        - build_sequences(symbols, date) -> (x, meta)
        - build_sequences(symbols, date) -> {"x": x, "meta": meta}
        """
        builder = getattr(self.feature_builder, "build_sequences", None)
        if callable(builder):
            built = builder(symbols, date)
        elif callable(self.feature_builder):
            built = self.feature_builder(symbols, date)
        else:
            raise ValueError("feature_builder must be callable or provide build_sequences(symbols, date)")

        if isinstance(built, Mapping):
            x = built.get("x")
            meta = built.get("meta", {})
            return x, _normalize_meta(meta, symbols)

        if isinstance(built, tuple) and len(built) == 2:
            x, meta = built
            return x, _normalize_meta(meta, symbols)

        return built, {s: {} for s in symbols}

    def _infer(self, x: Any) -> Mapping[str, Any]:
        """Run model forward pass and validate output keys."""
        try:
            preds = self.model(x) if callable(self.model) else self.model.forward(x)
        except Exception as exc:
            raise RuntimeError(f"Model inference failed: {exc}") from exc

        # MTLTransformer may return (preds, losses)
        if isinstance(preds, tuple) and preds and isinstance(preds[0], Mapping):
            preds = preds[0]

        if not isinstance(preds, Mapping):
            raise ValueError("Model output must be a mapping with prediction heads")

        for key in PRIMARY_TREND_PRED_COLS:
            if key not in preds:
                raise ValueError(f"Model output missing required key: {key}")

        return preds

    def _valid_prediction_mask(
        self,
        symbols: Sequence[str],
        meta: Mapping[str, Mapping[str, Any]],
        pred_by_horizon: Mapping[str, Any],
        max_abs_return: float = 0.5,
    ) -> list[bool]:
        """Filter out invalid predictions and suspended stocks."""
        preds_lists = {h: _to_1d_float_list(v) for h, v in pred_by_horizon.items()}
        n = len(symbols)
        for h, values in preds_lists.items():
            if len(values) != n:
                raise ValueError(f"Prediction length mismatch for {h}: {len(values)} != {n}")

        mask: list[bool] = []
        for idx, symbol in enumerate(symbols):
            m = meta.get(symbol, {})

            if _is_suspended(m):
                mask.append(False)
                continue

            ok = True
            for h in (f"{horizon}d" for horizon in PRIMARY_TREND_HORIZONS):
                value = preds_lists[h][idx]
                if not math.isfinite(value):
                    ok = False
                    break
                if abs(value) > max_abs_return:
                    ok = False
                    break
            mask.append(ok)
        return mask

    def _extract_reason(self, symbol: str, features: Mapping[str, Any]) -> str:
        """Extract a human-readable reason from key features.

        Args:
            symbol: Stock symbol.
            features: Per-symbol feature mapping, such as rsi_14/return_20d/volume_ratio.

        Returns:
            A reason string.
        """
        del symbol  # reserved for future symbol-specific rules
        reasons: list[str] = []

        rsi = _pick_float(features, ("rsi_14", "rsi14", "rsi"))
        if rsi is not None:
            if rsi > 70:
                reasons.append(f"RSI超买但仍强势({rsi:.1f})")
            elif rsi > 50:
                reasons.append(f"RSI中性偏强({rsi:.1f})")

        mom = _pick_float(features, ("return_20d", "ret_20d", "momentum_20d", "mom_20d"))
        if mom is not None:
            if mom > 0.15:
                reasons.append(f"20日动量强劲({mom:.1%})")
            elif mom > 0.05:
                reasons.append(f"20日动量温和({mom:.1%})")

        vol_ratio = _pick_float(features, ("volume_ratio", "vol_ratio", "volume_ratio_5d"))
        if vol_ratio is not None and vol_ratio > 1.5:
            reasons.append(f"成交量放大({vol_ratio:.2f}倍)")

        return " | ".join(reasons) if reasons else "技术指标综合评分较高"


def save_as_json(recommendations: Mapping[str, Sequence[Recommendation]], output_path: str | Path) -> Path:
    """Save recommendations to a structured JSON file."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "3d": [r.to_dict() for r in recommendations.get("3d", [])],
        "5d": [r.to_dict() for r in recommendations.get("5d", [])],
        "10d": [r.to_dict() for r in recommendations.get("10d", [])],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def save_as_csv(recommendations: Mapping[str, Sequence[Recommendation]], output_dir: str | Path) -> dict[str, Path]:
    """Save recommendations to Excel-compatible CSV files (one per horizon)."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for horizon, recs in recommendations.items():
        out_path = out_dir / f"recommendations_{horizon}.csv"
        with out_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["rank", "symbol", "name", "predicted_return", "confidence", "reason"],
            )
            writer.writeheader()
            for rec in recs:
                writer.writerow(rec.to_dict())
        paths[str(horizon)] = out_path

    return paths


def save_as_markdown(
    recommendations: Mapping[str, Sequence[Recommendation]],
    output_path: str | Path,
    title: str = "多时间跨度股票推荐榜单",
) -> Path:
    """Save recommendations to a Markdown table document."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"# {title}\n\n")
    lines.append(f"**生成时间：** {now}\n\n")

    for horizon in ("3d", "5d", "10d"):
        recs = recommendations.get(horizon, [])
        lines.append(f"## {horizon.upper()} 推荐（{horizon}）\n\n")
        lines.append("| 排名 | 代码 | 名称 | 预测收益 | 置信度 | 推荐理由 |\n")
        lines.append("|------|------|------|----------|--------|----------|\n")
        for rec in recs:
            lines.append(
                f"| {rec.rank} | {rec.symbol} | {rec.name} | {rec.predicted_return:.2%} | "
                f"{rec.confidence:.2f} | {rec.reason.replace(chr(10), ' ')} |\n"
            )
        lines.append("\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    return out_path


def _normalize_symbols_with_names(raw: Any) -> list[tuple[str, str]]:
    """Normalize universe data to list[(symbol, name)]."""
    if raw is None:
        return []

    if isinstance(raw, Mapping):
        return [(str(k), str(v)) for k, v in raw.items()]

    if isinstance(raw, str):
        return [(raw, "")]

    if isinstance(raw, Sequence):
        out: list[tuple[str, str]] = []
        for item in raw:
            if isinstance(item, str):
                out.append((item, ""))
            elif isinstance(item, Mapping):
                symbol = item.get("symbol") or item.get("code") or item.get("代码")
                name = item.get("name") or item.get("名称") or ""
                if symbol is None:
                    raise ValueError("Universe item mapping missing 'symbol'/'code'")
                out.append((str(symbol), str(name)))
            elif isinstance(item, tuple) and len(item) == 2:
                out.append((str(item[0]), str(item[1])))
            else:
                raise ValueError(f"Unsupported universe item type: {type(item)!r}")
        return out

    raise ValueError(f"Unsupported universe type: {type(raw)!r}")


def _normalize_meta(meta: Any, symbols: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Normalize meta to dict[symbol, dict]."""
    if meta is None:
        return {s: {} for s in symbols}

    if isinstance(meta, Mapping):
        out: dict[str, dict[str, Any]] = {}
        for s in symbols:
            val = meta.get(s, {})
            out[s] = dict(val) if isinstance(val, Mapping) else {}
        return out

    raise ValueError(f"Unsupported meta type: {type(meta)!r}")


def _to_1d_float_list(values: Any) -> list[float]:
    """Convert a 1D tensor/array/sequence to ``list[float]``."""
    if values is None:
        return []

    if torch is not None and isinstance(values, torch.Tensor):
        return [float(x) for x in values.detach().cpu().reshape(-1).tolist()]

    if hasattr(values, "tolist") and callable(values.tolist):
        out = values.tolist()
        if isinstance(out, list):
            if out and isinstance(out[0], list):  # numpy may nest a single extra dimension
                out = [x for row in out for x in row]
            return [float(x) for x in out]

    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return [float(x) for x in values]

    raise ValueError(f"Unsupported prediction type: {type(values)!r}")


def _pick_float(mapping: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    for key in keys:
        if key in mapping:
            try:
                return float(mapping[key])
            except Exception:  # pragma: no cover - defensive conversion
                return None
    return None


def _is_suspended(meta: Mapping[str, Any]) -> bool:
    if bool(meta.get("is_suspended", False)):
        return True

    for key in ("volume", "vol", "volume_1d"):
        if key in meta:
            try:
                return float(meta[key]) == 0.0
            except Exception:
                return False
    return False


def _confidence_map(
    all_scores: Sequence[tuple[str, float]],
    selected: Sequence[tuple[str, float]],
) -> dict[str, float]:
    """Compute min-max confidence in [0,1] for selected symbols."""
    if not selected:
        return {}

    scores_only = [score for _, score in all_scores]
    lo, hi = min(scores_only), max(scores_only)
    if math.isclose(lo, hi):
        return {symbol: 0.5 for symbol, _ in selected}

    def clamp01(v: float) -> float:
        return float(max(0.0, min(1.0, v)))

    return {symbol: clamp01((score - lo) / (hi - lo)) for symbol, score in selected}
