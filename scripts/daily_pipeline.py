#!/usr/bin/env python
"""Production daily pipeline entrypoint (Phase 3).

Usage:
  python scripts/daily_pipeline.py --date 20250117 --config configs/pipeline.yaml
  python scripts/daily_pipeline.py --date 20250117 --config configs/pipeline.yaml --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import yaml

# Keep consistent with other scripts: allow running from repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ashare_lab.features import (  # noqa: E402
    AmountChange,
    BollingerDeviation,
    MACDHist,
    PriceSlope,
    Return1D,
    Return10D,
    Return20D,
    Return5D,
    RSI,
    VolumeRatio,
)
from ashare_lab.models.transformer import create_mtl_model  # noqa: E402
from ashare_lab.pipeline import DailyPipelineOrchestrator  # noqa: E402
from ashare_lab.recommendation import (  # noqa: E402
    ODPSourceAdapter,
    TushareSourceAdapter,
)
from ashare_lab.recommendation.validator import HS300IndexCalendarSource  # noqa: E402
from ashare_lab.universe import is_allowed_a_share_symbol  # noqa: E402

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="生产级日频流水线（数据刷新→推荐→持久化→验证→记录）")
    p.add_argument("--date", required=True, help="目标交易日 YYYYMMDD")
    p.add_argument("--config", default="inputs/configs/pipeline.toml", help="流水线配置文件路径")
    p.add_argument("--data-source-config", default="inputs/configs/data_source.toml", help="数据源配置文件路径")
    p.add_argument("--model", default=None, help="模型 checkpoint 路径（生产模式）")
    p.add_argument("--model-config", default="inputs/configs/profiles/model_mtl.toml", help="模型结构配置文件（生产模式）")
    p.add_argument("--skip-training", action="store_true", help="预留：跳过增量训练（Task 3.2）")
    p.add_argument("--dry-run", action="store_true", help="使用合成数据快速运行（不访问外部数据源）")
    p.add_argument("--symbols", nargs="*", default=None, help="可选：覆盖默认 universe（6位代码或带后缀）")
    return p.parse_args(argv)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"YAML config must be a mapping: {path}")
    return raw


def _configure_logging(config_path: str | Path) -> None:
    cfg = _load_yaml(config_path)
    logging_cfg = cfg.get("logging") or {}
    level_name = str(logging_cfg.get("level") or "INFO").upper()
    fmt = str(logging_cfg.get("format") or "%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    log_file = logging_cfg.get("file")

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        log_path = PROJECT_ROOT / str(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(level=getattr(logging, level_name, logging.INFO), format=fmt, handlers=handlers, force=True)


class StaticUniverseFilter:
    def __init__(self, items: list[dict[str, str]]):
        self._items = list(items)

    def get_tradable_symbols(self, date: str) -> list[dict[str, str]]:  # noqa: ARG002
        return list(self._items)

    def is_allowed_a_share_symbol(self, symbol: str) -> bool:
        return is_allowed_a_share_symbol(symbol)


class DataSourceFeatureBuilder:
    """Build per-symbol feature sequences via injected data_source."""

    def __init__(self, data_source: Any, feature_fns: Iterable[Any], seq_len: int = 30) -> None:
        self.data_source = data_source
        self.feature_fns = list(feature_fns)
        self.seq_len = int(seq_len)

    def build_sequences(self, symbols: list[str], date: str) -> dict[str, Any]:
        import numpy as np
        import pandas as pd

        try:
            import torch
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("PyTorch (torch) is required for production model inference") from exc

        target = pd.to_datetime(date).normalize()
        # buffer for feature lookbacks (e.g., Return60D) and trading day gaps
        start = (target - pd.Timedelta(days=220)).strftime("%Y-%m-%d")
        end = target.strftime("%Y-%m-%d")

        bars_by_symbol = self.data_source.fetch_daily_bars(symbols, start_date=start, end_date=end)

        xs: list[np.ndarray] = []
        meta: dict[str, dict[str, Any]] = {}
        for symbol in symbols:
            df = bars_by_symbol.get(symbol)
            if df is None or df.empty:
                xs.append(np.zeros((self.seq_len, len(self.feature_fns)), dtype="float32"))
                meta[symbol] = {"volume": 0.0, "is_suspended": True}
                continue

            hist = df.loc[df.index < target].copy()
            if hist.empty or len(hist) < self.seq_len:
                xs.append(np.zeros((self.seq_len, len(self.feature_fns)), dtype="float32"))
                meta[symbol] = {"volume": float(hist["volume"].iloc[-1]) if not hist.empty else 0.0, "is_suspended": True}
                continue

            feats: dict[str, Any] = {}
            for f in self.feature_fns:
                feats[f.name] = f.compute(hist)
            feat_df = pd.DataFrame(feats, index=hist.index).tail(self.seq_len).fillna(0.0)

            xs.append(feat_df.to_numpy(dtype="float32", copy=False))

            last_bar = hist.iloc[-1]
            symbol_meta: dict[str, Any] = {k: float(v) for k, v in feat_df.iloc[-1].to_dict().items()}
            symbol_meta["volume"] = float(last_bar.get("volume", 0.0))
            symbol_meta["amount"] = float(last_bar.get("amount", 0.0))
            meta[symbol] = symbol_meta

        X = torch.from_numpy(np.stack(xs, axis=0))
        return {"x": X, "meta": meta}


class DummyDryRunModel:
    def __call__(self, x: Any) -> dict[str, Any]:
        import numpy as np

        n = int(getattr(x, "shape", [0])[0])
        base = np.linspace(0.03, 0.01, num=max(n, 1), dtype="float32")
        return {"pred_3d": base, "pred_5d": base * 0.9, "pred_10d": base * 0.8}


class DummyDryRunFeatureBuilder:
    def __init__(self, n_feat: int = 10, seq_len: int = 30) -> None:
        self.n_feat = int(n_feat)
        self.seq_len = int(seq_len)

    def build_sequences(self, symbols: list[str], date: str) -> dict[str, Any]:  # noqa: ARG002
        import numpy as np

        xs = np.zeros((len(symbols), self.seq_len, self.n_feat), dtype="float32")
        meta = {s: {"volume": 1.0, "amount": 1.0, "name": ""} for s in symbols}
        return {"x": xs, "meta": meta}


def _build_data_source(data_source_config_path: str | Path) -> tuple[Any, Any]:
    cfg = _load_yaml(data_source_config_path)
    default_source = str(cfg.get("default_source") or "tushare")
    sources = cfg.get("sources") or {}
    selected = sources.get(default_source) or {}
    cache_dir = Path(str(selected.get("cache_dir") or "inputs/data/cache"))
    cache_dir = (PROJECT_ROOT / cache_dir).resolve()

    if default_source == "tushare":
        token_env = str(selected.get("token_env") or "TUSHARE_TOKEN")
        token = os.environ.get(token_env) or None
        data_source = TushareSourceAdapter(cache_dir=cache_dir, adjust="qfq", refresh=False, token=token)
    elif default_source == "odp":
        data_source = ODPSourceAdapter(
            cache_dir=cache_dir,
            provider=str(selected.get("provider") or "yfinance"),
            interval=str(selected.get("interval") or "1d"),
            refresh=False,
            base_url=str(selected.get("base_url") or "").strip() or None,
            prefer_rest=bool(selected.get("prefer_rest", False)),
        )
    else:
        raise ValueError(f"不支持的数据源: {default_source}")

    calendar_source = HS300IndexCalendarSource(cache_dir=cache_dir, refresh=False)
    return data_source, calendar_source


def _load_model(model_config_path: str | Path, checkpoint_path: str | Path):
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyTorch (torch) is required to run the production pipeline") from exc

    cfg = _load_yaml(model_config_path)
    model_cfg = cfg.get("model") or {}
    model = create_mtl_model(
        input_dim=int(model_cfg.get("input_dim", 10)),
        d_model=int(model_cfg.get("d_model", 128)),
        n_heads=int(model_cfg.get("n_heads", 4)),
        n_layers=int(model_cfg.get("n_layers", 4)),
        d_ff=int(model_cfg.get("d_ff", 512)),
        dropout=float(model_cfg.get("dropout", 0.1)),
        max_seq_len=int(model_cfg.get("max_seq_len", 60)),
        min_seq_len=int(model_cfg.get("min_seq_len", 30)),
        loss_weights=tuple(model_cfg.get("loss_weights", [1.0, 1.0, 1.0])),
    )

    ckpt_path = Path(checkpoint_path)
    if not ckpt_path.is_absolute():
        ckpt_path = PROJECT_ROOT / ckpt_path
    if not ckpt_path.exists():
        raise FileNotFoundError(f"model checkpoint not found: {ckpt_path}")

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    state = ckpt.get("model_state_dict") if isinstance(ckpt, dict) else ckpt
    if not isinstance(state, dict):
        raise ValueError(f"invalid checkpoint: {ckpt_path}")

    model.load_state_dict(state, strict=False)
    model.eval()
    return model


def _default_universe_items() -> list[dict[str, str]]:
    return [
        {"symbol": "000001", "name": "平安银行"},
        {"symbol": "000002", "name": "万科A"},
        {"symbol": "600519", "name": "贵州茅台"},
    ]


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    _configure_logging(args.config)

    if args.dry_run:
        universe_items = [{"symbol": s, "name": ""} for s in (args.symbols or [x["symbol"] for x in _default_universe_items()])]
        universe_filter = StaticUniverseFilter(universe_items)
        feature_builder = DummyDryRunFeatureBuilder()
        model = DummyDryRunModel()
        # dry-run skips external refresh + validation; keep adapters unused
        data_source, calendar_source = _build_data_source(args.data_source_config)
    else:
        data_source, calendar_source = _build_data_source(args.data_source_config)
        universe_items = [{"symbol": s, "name": ""} for s in (args.symbols or [x["symbol"] for x in _default_universe_items()])]
        universe_filter = StaticUniverseFilter(universe_items)
        model = _load_model(args.model_config, args.model)
        feature_builder = DataSourceFeatureBuilder(
            data_source=data_source,
            feature_fns=[
                Return1D(),
                Return5D(),
                Return10D(),
                Return20D(),
                RSI(),
                MACDHist(),
                BollingerDeviation(),
                VolumeRatio(),
                AmountChange(),
                PriceSlope(window=20),
            ],
            seq_len=30,
        )

    orchestrator = DailyPipelineOrchestrator(
        config_path=args.config,
        model=model,
        feature_builder=feature_builder,
        universe_filter=universe_filter,
        data_source=data_source,
        calendar_source=calendar_source,
    )

    result = orchestrator.run(args.date, skip_training=bool(args.skip_training), dry_run=bool(args.dry_run))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
