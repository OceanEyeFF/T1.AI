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
    --cache-dir: R4 TuShare cache root (default: inputs/data/cache).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import torch
except Exception as exc:  # pragma: no cover - torch is expected in this repo
    raise RuntimeError("PyTorch (torch) is required to run this script") from exc

# Add project root to sys.path (keep consistent with other scripts in this repo).
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ashare_infra.lake.r4_contract import R4_ADJUST_DEFAULT, R4_CACHE_ROOT, make_r4_datalake
from ashare_lab.dataset.preprocessing import RollingRobustScaler  # noqa: E402
from ashare_lab.features.contract import (  # noqa: E402
    FeatureContract,
    FeatureFactory,
)
from ashare_lab.recommendation.engine import Recommendation, RecommendationEngine  # noqa: E402
from ashare_lab.symbols import symbol_to_ts_code  # noqa: E402
from ashare_lab.universe import is_allowed_a_share_symbol  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成指定日期的 3×Top-N 股票推荐榜单")
    parser.add_argument("--date", required=True, help="推荐日期（YYYYMMDD）")
    parser.add_argument("--model", default=None, help="模型 checkpoint 路径")
    parser.add_argument(
        "--model-config",
        default="inputs/configs/profiles/model_mtl.toml",
        help="模型 profile；其中引用 Feature Contract",
    )
    parser.add_argument("--output", default="outputs/predictions", help="输出目录")
    parser.add_argument("--top-n", type=int, default=10, help="每个时间跨度推荐数量")
    parser.add_argument(
        "--cache-dir",
        default=str(R4_CACHE_ROOT),
        help="R4 TuShare cache root (default: inputs/data/cache)",
    )
    return parser.parse_args(argv)


def _parse_yyyymmdd(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"--date must be in YYYYMMDD format, got: {date_str!r}") from exc


def _load_cached_daily_bars(symbol: str, cache_dir: Path) -> pd.DataFrame:
    """Load daily bars via R4 DataLake (TuShare partitioned cache under cache_dir)."""
    ts_code = symbol_to_ts_code(symbol)
    lake = make_r4_datalake(cache_dir=cache_dir)
    df = lake.load_daily_bars(
        ts_code, "20000101", "20991231", source="tushare", adjust=R4_ADJUST_DEFAULT
    )

    if df.empty:
        raise FileNotFoundError(f"missing cached daily bars for {symbol}")

    if "date" in df.columns:
        df = df.set_index("date")
    df = df.sort_index()
    return df


def _load_selected_universe(cache_dir: Path) -> list[dict[str, str]]:
    """Load a practical universe list for the MVP.

    Priority:
      1) {cache_dir}/selected_stocks_20210701.csv (legacy snapshot)
      2) infer from TuShare cached directories (tushare_qfq/{ts_code}/ then tushare/{ts_code}/)
    """
    legacy_csv = PROJECT_ROOT / "data" / "cache" / "selected_stocks_20210701.csv"
    selected_csv = cache_dir / "selected_stocks_20210701.csv"
    for csv_path in (selected_csv, legacy_csv):
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, dtype=str)
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
        namespace_dir = cache_dir / subdir
        if not namespace_dir.exists():
            continue
        for p in namespace_dir.iterdir():
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
    """Build contract-valid cached-data sequences without zero-imputation."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        feature_contract: FeatureContract,
        scaler: RollingRobustScaler,
    ):
        self.cache_dir = cache_dir
        self.feature_contract = feature_contract
        self.scaler = scaler
        self.seq_len = feature_contract.seq_len
        if tuple(scaler.feature_names) != feature_contract.feature_names:
            raise ValueError("checkpoint scaler feature order does not match Feature Contract")
        self.last_meta: dict[str, dict[str, Any]] | None = None

    def build_sequences(self, symbols: list[str], date: str) -> dict[str, Any]:
        """Build x and meta for RecommendationEngine."""
        target = pd.to_datetime(_parse_yyyymmdd(date))
        xs: list[torch.Tensor] = []
        meta: dict[str, dict[str, Any]] = {}
        accepted_symbols: list[str] = []

        for symbol in symbols:
            try:
                bars = _load_cached_daily_bars(symbol, self.cache_dir)
            except FileNotFoundError:
                meta[symbol] = {
                    "volume": 0.0,
                    "is_suspended": True,
                    "feature_rejection_reason": "missing_daily_bars",
                }
                continue
            history = bars.loc[bars.index < target].copy()
            if history.empty or len(history) < self.seq_len:
                meta[symbol] = {
                    "volume": 0.0 if history.empty else float(history["volume"].iloc[-1]),
                    "is_suspended": True,
                    "feature_rejection_reason": "insufficient_history",
                }
                continue

            feats = FeatureFactory.compute(history, self.feature_contract).tail(self.seq_len)
            if len(feats) != self.seq_len or not np.isfinite(feats.to_numpy(dtype=float, copy=False)).all():
                meta[symbol] = {
                    "volume": float(history["volume"].iloc[-1]),
                    "is_suspended": True,
                    "feature_rejection_reason": "nonfinite_contract_features",
                }
                continue

            raw = feats.to_numpy(dtype=np.float64, copy=False)[None, :, :]
            self.feature_contract.assert_sequence_shape(raw.shape, context=f"cached inference features for {symbol}")
            x = torch.from_numpy(self.scaler.transform(raw)[0])
            xs.append(x)
            accepted_symbols.append(symbol)

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

        if not xs:
            raise ValueError("no symbols have finite feature sequences under the active Feature Contract")
        X = torch.stack(xs, dim=0)
        self.feature_contract.assert_sequence_shape(tuple(X.shape), context="cached inference feature batch")
        self.last_meta = meta
        return {"x": X, "meta": meta, "symbols": accepted_symbols}


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except Exception:
        return False
    return True


def _load_mtl_checkpoint_bundle(
    model_path: Path, device: torch.device, model_config_path: str | Path
) -> tuple[torch.nn.Module, FeatureContract, RollingRobustScaler]:
    """Use the production strict loader rather than inferring model shape from weights."""

    from scripts.daily_pipeline import _load_model

    model, contract, scaler = _load_model(model_config_path, model_path)
    model.to(device)
    model.eval()
    return model, contract, scaler


def load_mtl_checkpoint_model(
    model_path: Path,
    device: torch.device,
    model_config_path: str | Path = "inputs/configs/profiles/model_mtl.toml",
) -> torch.nn.Module:
    """Deprecated compatibility wrapper around the strict manifest loader."""

    warnings.warn(
        "load_mtl_checkpoint_model is deprecated; use the Feature Contract-aware production loader",
        DeprecationWarning,
        stacklevel=2,
    )
    model, _contract, _scaler = _load_mtl_checkpoint_bundle(model_path, device, model_config_path)
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

    if not args.model:
        raise ValueError("--model is required; legacy checkpoints without a Feature Contract manifest are rejected")
    model_path = Path(args.model)
    output_dir = Path(args.output)
    cache_dir = Path(args.cache_dir)

    if args.top_n <= 0:
        raise ValueError("--top-n must be positive")

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, feature_contract, scaler = _load_mtl_checkpoint_bundle(
            model_path, device=device, model_config_path=args.model_config
        )
        model_runner = InferenceWrapper(model, device=device)

        universe_items = _load_selected_universe(cache_dir)

        # Attach names to meta so RecommendationEngine can display them.
        feature_builder = LocalFeatureBuilder(
            cache_dir=cache_dir,
            feature_contract=feature_contract,
            scaler=scaler,
        )
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
