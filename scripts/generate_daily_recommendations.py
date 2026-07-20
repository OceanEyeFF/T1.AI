#!/usr/bin/env python
"""Generate daily 3×Top-N recommendation lists.

This script loads a trained MTLTransformer checkpoint and uses RecommendationEngine to generate
three independent Top-N rankings for 3/5/10 trading-day horizons.

Outputs (default):
  - output/recommendations/{date}.json
  - output/recommendations/{date}_3d.csv
  - output/recommendations/{date}_5d.csv
  - output/recommendations/{date}_10d.csv
  - output/recommendations/{date}.md

Args:
    --date: Recommendation date in YYYYMMDD.
    --model: Model checkpoint path (default: models/best_mtl.pt).
    --output: Output directory (default: output/recommendations).
    --top-n: Number of items per horizon list (default: 10).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:
    import torch
except Exception as exc:  # pragma: no cover - torch is expected in this repo
    raise RuntimeError("PyTorch (torch) is required to run this script") from exc

# Add project root to sys.path (keep consistent with other scripts in this repo).
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ashare_infra.lake import DataLake
from ashare_lab.features import (  # noqa: E402
    AmountChange,
    Return1D,
    Return20D,
    Return5D,
    VolumeChange,
    VolumeRatio,
)
from ashare_lab.features.technical import (  # noqa: E402
    RSI,
    MACDHist,
    BollingerDeviation,
)
from ashare_lab.features.price_slope import PriceSlope  # noqa: E402
from ashare_lab.models.transformer import create_mtl_model  # noqa: E402
from ashare_lab.recommendation.engine import Recommendation, RecommendationEngine  # noqa: E402
from ashare_lab.symbols import symbol_to_ts_code  # noqa: E402
from ashare_lab.universe import is_allowed_a_share_symbol  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成指定日期的 3×Top-N 股票推荐榜单")
    parser.add_argument("--date", required=True, help="推荐日期（YYYYMMDD）")
    parser.add_argument("--model", default=None, help="模型 checkpoint 路径")
    parser.add_argument("--output", default="outputs/predictions", help="输出目录")
    parser.add_argument("--top-n", type=int, default=10, help="每个时间跨度推荐数量")
    return parser.parse_args(argv)


def _parse_yyyymmdd(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"--date must be in YYYYMMDD format, got: {date_str!r}") from exc


def _latest_cached_bars_path(symbol: str, cache_dir: Path) -> Path | None:
    candidates = sorted(cache_dir.glob(f"{symbol}_daily_*.csv"), reverse=True)
    return candidates[0] if candidates else None


def _load_cached_daily_bars(symbol: str, cache_dir: Path) -> pd.DataFrame:
    """Load daily bars via DataLake (TuShare partitioned cache under cache_dir)."""
    ts_code = symbol_to_ts_code(symbol)
    lake = DataLake(cache_dir=cache_dir, default_source="tushare")
    df = lake.load_daily_bars(
        ts_code, "20000101", "20991231", source="tushare", adjust="qfq"
    )

    if df.empty:
        raise FileNotFoundError(f"missing cached daily bars for {symbol}")

    if "date" in df.columns:
        df = df.set_index("date")
    df = df.sort_index()
    return df


def _load_selected_universe() -> list[dict[str, str]]:
    """Load a practical universe list for the MVP.

    Priority:
      1) data/cache/selected_stocks_20210701.csv (small, already cached bars in this repo)
      2) infer from TuShare cached directories (tushare_qfq/{ts_code}/ then tushare/{ts_code}/)
    """
    selected_csv = PROJECT_ROOT / "data" / "cache" / "selected_stocks_20210701.csv"
    if selected_csv.exists():
        df = pd.read_csv(selected_csv, dtype=str)
        code_col = "code" if "code" in df.columns else "symbol"
        name_col = "name" if "name" in df.columns else "名称"
        items: dict[str, str] = {}
        for _, row in df.iterrows():
            code = str(row.get(code_col, "")).strip().zfill(6)
            name = str(row.get(name_col, "")).strip()
            if not code or code == "000000":
                continue
            if code not in items:
                items[code] = name
        return [{"symbol": k, "name": v} for k, v in sorted(items.items())]

    symbols: set[str] = set()
    for subdir in ("tushare_qfq", "tushare"):
        cache_dir = PROJECT_ROOT / "data" / "cache" / subdir
        if not cache_dir.exists():
            continue
        for p in cache_dir.iterdir():
            if not p.is_dir():
                continue
            ts_code = p.name
            symbol = ts_code.split(".")[0] if "." in ts_code else ts_code
            if symbol.isdigit() and len(symbol) == 6:
                symbols.add(symbol)
    return [{"symbol": s, "name": ""} for s in sorted(symbols)]


class LocalUniverseFilter:
    """Universe provider for RecommendationEngine."""

    def __init__(self, items: list[dict[str, str]]):
        self._items = list(items)

    def get_tradable_symbols(self, date: str) -> list[dict[str, str]]:  # noqa: ARG002
        return list(self._items)

    def is_allowed_a_share_symbol(self, symbol: str) -> bool:
        return is_allowed_a_share_symbol(symbol)


class LocalFeatureBuilder:
    """Build per-symbol feature sequences for a given date."""

    def __init__(self, cache_dir: Path, feature_fns: Iterable[Any], seq_len: int):
        self.cache_dir = cache_dir
        self.feature_fns = list(feature_fns)
        self.seq_len = int(seq_len)
        self.last_meta: dict[str, dict[str, Any]] | None = None

    def build_sequences(self, symbols: list[str], date: str) -> dict[str, Any]:
        """Build x and meta for RecommendationEngine."""
        target = pd.to_datetime(_parse_yyyymmdd(date))
        xs: list[torch.Tensor] = []
        meta: dict[str, dict[str, Any]] = {}

        for symbol in symbols:
            bars = _load_cached_daily_bars(symbol, self.cache_dir)
            history = bars.loc[bars.index < target].copy()
            if history.empty or len(history) < self.seq_len:
                # Not enough history, mark as suspended so it will be filtered out.
                x = torch.zeros(self.seq_len, len(self.feature_fns), dtype=torch.float32)
                xs.append(x)
                meta[symbol] = {"volume": 0.0, "is_suspended": True}
                continue

            feats = self._compute_features(history)
            feats = feats.tail(self.seq_len)
            feats = feats.fillna(0.0)

            x = torch.from_numpy(feats.to_numpy(dtype="float32", copy=False))
            xs.append(x)

            last_dt = feats.index[-1]
            last_row = feats.iloc[-1].to_dict()
            last_bar = history.loc[last_dt]
            last_bar_row = last_bar.iloc[-1] if isinstance(last_bar, pd.DataFrame) else last_bar
            symbol_meta: dict[str, Any] = {
                **{k: float(v) for k, v in last_row.items() if _is_number(v)},
                "volume": float(last_bar_row.get("volume", 0.0)),
                "amount": float(last_bar_row.get("amount", 0.0)),
            }
            meta[symbol] = symbol_meta

        X = torch.stack(xs, dim=0)
        self.last_meta = meta
        return {"x": X, "meta": meta}

    def _compute_features(self, bars: pd.DataFrame) -> pd.DataFrame:
        out: dict[str, pd.Series] = {}
        for f in self.feature_fns:
            out[f.name] = f.compute(bars)
        return pd.DataFrame(out, index=bars.index)


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except Exception:
        return False
    return True


def _infer_model_params(state: dict[str, Any]) -> dict[str, int]:
    w = state.get("input_projection.weight")
    if w is None:
        raise ValueError("checkpoint missing input_projection.weight")

    d_model, input_dim = int(w.shape[0]), int(w.shape[1])

    # infer n_layers from transformer_encoder.layers.{i}.*
    layer_ids: set[int] = set()
    for key in state.keys():
        if not key.startswith("transformer_encoder.layers."):
            continue
        parts = key.split(".")
        if len(parts) < 3 or not parts[2].isdigit():
            continue
        layer_ids.add(int(parts[2]))
    n_layers = len(layer_ids) if layer_ids else 4

    lin1 = state.get("transformer_encoder.layers.0.linear1.weight")
    d_ff = int(lin1.shape[0]) if lin1 is not None else 512

    pe = state.get("pos_encoder.pe")
    max_seq_len = int(pe.shape[1]) if pe is not None else 512

    return {
        "input_dim": input_dim,
        "d_model": d_model,
        "n_layers": n_layers,
        "d_ff": d_ff,
        "max_seq_len": max_seq_len,
    }


def load_mtl_checkpoint_model(model_path: Path, device: torch.device) -> torch.nn.Module:
    """Load MTLTransformer model from checkpoint with inferred architecture."""
    if not model_path.exists():
        raise FileNotFoundError(f"model checkpoint not found: {model_path}")

    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    state = ckpt.get("model_state_dict")
    if not isinstance(state, dict):
        raise ValueError(f"invalid checkpoint: missing model_state_dict in {model_path}")

    params = _infer_model_params(state)
    # n_heads is not encoded in state shapes; use a safe default that divides d_model.
    n_heads = 4 if params["d_model"] % 4 == 0 else 1
    min_seq_len = 20
    max_seq_len = max(params["max_seq_len"], min_seq_len)

    model = create_mtl_model(
        input_dim=params["input_dim"],
        d_model=params["d_model"],
        n_layers=params["n_layers"],
        n_heads=n_heads,
        d_ff=params["d_ff"],
        dropout=0.1,
        max_seq_len=max_seq_len,
        min_seq_len=min_seq_len,
        loss_weights=tuple(ckpt.get("config", {}).get("loss_weights", (1.0, 1.0, 1.0))),
    )
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()
    return model


class InferenceWrapper:
    """Wrap torch model to ensure no-grad inference and CPU/GPU compatibility."""

    def __init__(self, model: torch.nn.Module, device: torch.device):
        self.model = model
        self.device = device

    def __call__(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        with torch.inference_mode():
            x = x.to(self.device)
            out = self.model(x)
            if not isinstance(out, dict):
                raise ValueError("model output must be a dict for inference")
            return {k: v.detach().cpu() for k, v in out.items()}


def _reason_from_meta(symbol_meta: dict[str, Any] | None) -> str | None:
    if not symbol_meta:
        return None

    parts: list[str] = []
    mom20 = symbol_meta.get("return_20d")
    vol_ratio = symbol_meta.get("volume_ratio_5d")
    vol_change = symbol_meta.get("volume_change")
    amt_change = symbol_meta.get("amount_change")

    if _is_number(mom20):
        parts.append(f"20日动量 {float(mom20):.1%}")
    if _is_number(vol_ratio):
        parts.append(f"量比 {float(vol_ratio):.2f}x")
    if _is_number(vol_change):
        parts.append(f"成交量变化 {float(vol_change):.1%}")
    if _is_number(amt_change):
        parts.append(f"成交额变化 {float(amt_change):.1%}")

    return " | ".join(parts) if parts else None


def _rec_to_dict(
    rec: Recommendation,
    meta_map: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    meta = (meta_map or {}).get(rec.symbol, {})
    reason = _reason_from_meta(meta) or rec.reason
    return {
        "rank": rec.rank,
        "symbol": rec.symbol,
        "name": rec.name,
        "predicted_return": float(rec.predicted_return),
        "confidence": float(rec.confidence),
        "reason": reason,
    }


def _write_json(
    date: str,
    recs: dict[str, list[Recommendation]],
    path: Path,
    meta_map: dict[str, dict[str, Any]] | None,
) -> None:
    payload = {
        "date": date,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "3d": [_rec_to_dict(r, meta_map) for r in recs.get("3d", [])],
        "5d": [_rec_to_dict(r, meta_map) for r in recs.get("5d", [])],
        "10d": [_rec_to_dict(r, meta_map) for r in recs.get("10d", [])],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(
    recs: list[Recommendation],
    path: Path,
    meta_map: dict[str, dict[str, Any]] | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["rank", "symbol", "name", "predicted_return", "confidence", "reason"],
        )
        writer.writeheader()
        for r in recs:
            meta = (meta_map or {}).get(r.symbol, {})
            reason = _reason_from_meta(meta) or r.reason
            writer.writerow(
                {
                    "rank": r.rank,
                    "symbol": r.symbol,
                    "name": r.name,
                    "predicted_return": r.predicted_return,
                    "confidence": r.confidence,
                    "reason": reason,
                }
            )


def _write_markdown(
    date: str,
    recs: dict[str, list[Recommendation]],
    path: Path,
    meta_map: dict[str, dict[str, Any]] | None,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("# 多时间跨度股票推荐榜单\n\n")
    lines.append(f"**推荐日期：** {date}\n\n")
    lines.append(f"**生成时间：** {now}\n\n")

    for horizon in ("3d", "5d", "10d"):
        items = recs.get(horizon, [])
        lines.append(f"## {horizon.upper()} 推荐（{horizon}）\n\n")
        lines.append("| 排名 | 代码 | 名称 | 预测收益 | 置信度 | 推荐理由 |\n")
        lines.append("|------|------|------|----------|--------|----------|\n")
        for r in items:
            meta = (meta_map or {}).get(r.symbol, {})
            reason = _reason_from_meta(meta) or r.reason
            reason = reason.replace("|", "｜").replace(chr(10), " ")
            lines.append(
                f"| {r.rank} | {r.symbol} | {r.name} | {r.predicted_return:.2%} | "
                f"{r.confidence:.2f} | {reason} |\n"
            )
        lines.append("\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _ = _parse_yyyymmdd(args.date)

    model_path = Path(args.model)
    output_dir = Path(args.output)
    cache_dir = PROJECT_ROOT / "data" / "cache"

    if args.top_n <= 0:
        raise ValueError("--top-n must be positive")

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = load_mtl_checkpoint_model(model_path, device=device)
        model_runner = InferenceWrapper(model, device=device)

        features = [
            # Momentum features (3)
            Return1D(),
            Return5D(),
            Return20D(),
            # Volume features (3)
            VolumeRatio(window=5),
            VolumeChange(),
            AmountChange(),
            # Technical indicators (3)
            RSI(period=14),
            MACDHist(),
            BollingerDeviation(window=20),
            # Trend features (2)
            PriceSlope(window=5),
            PriceSlope(window=20),
        ]

        universe_items = _load_selected_universe()

        # Attach names to meta so RecommendationEngine can display them.
        feature_builder = LocalFeatureBuilder(cache_dir=cache_dir, feature_fns=features, seq_len=20)
        universe_filter = LocalUniverseFilter(universe_items)

        engine = RecommendationEngine(model_runner, feature_builder, universe_filter)
        recs = engine.generate_recommendations(args.date, top_n=int(args.top_n))

        json_path = output_dir / f"{args.date}.json"
        md_path = output_dir / f"{args.date}.md"
        csv_paths = {
            "3d": output_dir / f"{args.date}_3d.csv",
            "5d": output_dir / f"{args.date}_5d.csv",
            "10d": output_dir / f"{args.date}_10d.csv",
        }

        meta_map = feature_builder.last_meta
        _write_json(args.date, recs, json_path, meta_map)
        _write_markdown(args.date, recs, md_path, meta_map)
        for horizon, p in csv_paths.items():
            _write_csv(recs.get(horizon, []), p, meta_map)

        print("✅ 推荐榜单生成成功")
        print(f"  - JSON: {json_path}")
        for horizon, p in csv_paths.items():
            print(f"  - CSV({horizon}): {p}")
        print(f"  - Markdown: {md_path}")
        return 0
    except Exception as exc:
        print("❌ 推荐榜单生成失败")
        print(f"Error: {exc}")
        print(traceback.format_exc())
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
