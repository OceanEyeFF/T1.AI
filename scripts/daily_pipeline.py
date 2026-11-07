#!/usr/bin/env python
"""Production daily pipeline entrypoint (Phase 3).

Usage:
  python scripts/daily_pipeline.py --date 20250117 --config inputs/configs/pipeline.toml
  python scripts/daily_pipeline.py --date 20250117 --config inputs/configs/pipeline.toml --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping


# Keep consistent with other scripts: allow running from repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ashare_lab.dataset.preprocessing import RollingRobustScaler  # noqa: E402
from ashare_lab.features.contract import (  # noqa: E402
    FeatureContract,
    FeatureContractError,
    FeatureContractLoader,
    FeatureFactory,
)
from ashare_lab.models.artifact_manifest import (  # noqa: E402
    ModelArtifactError,
    validate_model_artifact_manifest,
)
from ashare_lab.models.transformer import create_mtl_model  # noqa: E402
from ashare_lab.pipeline import DailyPipelineOrchestrator  # noqa: E402
from ashare_lab.recommendation import (  # noqa: E402
    ODPSourceAdapter,
    TushareSourceAdapter,
)
from ashare_lab.recommendation.validator import HS300IndexCalendarSource  # noqa: E402
from ashare_lab.universe import is_allowed_a_share_symbol  # noqa: E402
try:  # noqa: E402
    from scripts.config_io import load_mapping_config
except ImportError:  # 直接以脚本运行时 scripts/ 在 sys.path 上
    from config_io import load_mapping_config

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


def _load_config(path: str | Path) -> dict[str, Any]:
    """配置统一走 config_io（TOML；JSON 兼容，YAML 已废弃）。"""
    return load_mapping_config(path)


def _configure_logging(config_path: str | Path) -> None:
    cfg = _load_config(config_path)
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
    """Build contract-valid, scaled sequences without zero-imputation."""

    def __init__(
        self,
        data_source: Any,
        *,
        feature_contract: FeatureContract,
        scaler: RollingRobustScaler,
    ) -> None:
        self.data_source = data_source
        self.feature_contract = feature_contract
        self.scaler = scaler
        self.seq_len = feature_contract.seq_len
        if tuple(scaler.feature_names) != feature_contract.feature_names:
            raise FeatureContractError(
                "inference scaler feature order does not match the active feature contract"
            )

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
        accepted_symbols: list[str] = []
        for symbol in symbols:
            df = bars_by_symbol.get(symbol)
            if df is None or df.empty:
                meta[symbol] = {
                    "volume": 0.0,
                    "is_suspended": True,
                    "feature_rejection_reason": "missing_daily_bars",
                }
                continue

            hist = df.loc[df.index < target].copy()
            if hist.empty or len(hist) < self.seq_len:
                meta[symbol] = {
                    "volume": float(hist["volume"].iloc[-1]) if not hist.empty else 0.0,
                    "is_suspended": True,
                    "feature_rejection_reason": "insufficient_history",
                }
                continue

            feat_df = FeatureFactory.compute(hist, self.feature_contract).tail(self.seq_len)
            if len(feat_df) != self.seq_len or not np.isfinite(feat_df.to_numpy(dtype=float, copy=False)).all():
                meta[symbol] = {
                    "volume": float(hist["volume"].iloc[-1]),
                    "is_suspended": True,
                    "feature_rejection_reason": "nonfinite_contract_features",
                }
                continue

            raw_sequence = feat_df.to_numpy(dtype=np.float64, copy=False)[None, :, :]
            self.feature_contract.assert_sequence_shape(
                raw_sequence.shape, context=f"inference features for {symbol}"
            )
            scaled_sequence = self.scaler.transform(raw_sequence)[0]
            xs.append(scaled_sequence)
            accepted_symbols.append(symbol)

            last_bar = hist.iloc[-1]
            symbol_meta: dict[str, Any] = {k: float(v) for k, v in feat_df.iloc[-1].to_dict().items()}
            symbol_meta["volume"] = float(last_bar.get("volume", 0.0))
            symbol_meta["amount"] = float(last_bar.get("amount", 0.0))
            meta[symbol] = symbol_meta

        if not xs:
            raise ValueError("no symbols have finite feature sequences under the active feature contract")
        X = torch.from_numpy(np.stack(xs, axis=0))
        self.feature_contract.assert_sequence_shape(tuple(X.shape), context="inference feature batch")
        return {"x": X, "meta": meta, "symbols": accepted_symbols}


class DummyDryRunModel:
    def __call__(self, x: Any) -> dict[str, Any]:
        import numpy as np

        n = int(getattr(x, "shape", [0])[0])
        base = np.linspace(0.03, 0.01, num=max(n, 1), dtype="float32")
        return {"pred_3d": base, "pred_5d": base * 0.9, "pred_10d": base * 0.8}


class DummyDryRunFeatureBuilder:
    def __init__(self, n_feat: int = 11, seq_len: int = 20) -> None:
        self.n_feat = int(n_feat)
        self.seq_len = int(seq_len)

    def build_sequences(self, symbols: list[str], date: str) -> dict[str, Any]:  # noqa: ARG002
        import numpy as np

        xs = np.zeros((len(symbols), self.seq_len, self.n_feat), dtype="float32")
        meta = {s: {"volume": 1.0, "amount": 1.0, "name": ""} for s in symbols}
        return {"x": xs, "meta": meta}


def _build_data_source(data_source_config_path: str | Path) -> tuple[Any, Any]:
    cfg = _load_config(data_source_config_path)
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


def _resolve_project_path(path: str | Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else PROJECT_ROOT / resolved


def _transformer_architecture(model_cfg: Mapping[str, Any]) -> dict[str, Any]:
    raw_weights = model_cfg.get("loss_weights", [1.0, 1.0, 1.0])
    if not isinstance(raw_weights, (list, tuple)) or len(raw_weights) != 3:
        raise ModelArtifactError("model.loss_weights must contain exactly three values")
    return {
        "d_model": int(model_cfg.get("d_model", 128)),
        "n_heads": int(model_cfg.get("n_heads", 4)),
        "n_layers": int(model_cfg.get("n_layers", 4)),
        "d_ff": int(model_cfg.get("d_ff", 512)),
        "dropout": float(model_cfg.get("dropout", 0.1)),
        "max_seq_len": int(model_cfg.get("max_seq_len", 512)),
        "min_seq_len": int(model_cfg.get("min_seq_len", 20)),
        "loss_weights": [float(value) for value in raw_weights],
        "loss_type": str(model_cfg.get("loss_type", "l1")),
        "loss_alpha": float(model_cfg.get("loss_alpha", 0.3)),
    }


def _load_model(
    model_config_path: str | Path, checkpoint_path: str | Path | None
) -> tuple[Any, FeatureContract, RollingRobustScaler]:
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyTorch (torch) is required to run the production pipeline") from exc

    cfg = _load_config(model_config_path)
    model_cfg = cfg.get("model")
    if not isinstance(model_cfg, Mapping):
        raise ModelArtifactError("model configuration must contain a [model] mapping")
    model_family = str(model_cfg.get("family", "")).strip()
    if model_family != "transformer":
        raise ModelArtifactError(
            f"daily pipeline only supports model family 'transformer', got {model_family!r}"
        )
    raw_contract_path = model_cfg.get("feature_contract")
    if not isinstance(raw_contract_path, str) or not raw_contract_path.strip():
        raise ModelArtifactError("model.feature_contract is required; model.input_dim is derived")
    feature_contract = FeatureContractLoader.load(_resolve_project_path(raw_contract_path))
    label_mode = str(model_cfg.get("label_mode", "")).strip()
    if label_mode not in {"close_to_close", "next_open_to_open"}:
        raise ModelArtifactError("model.label_mode must be close_to_close or next_open_to_open")
    architecture = _transformer_architecture(model_cfg)
    model = create_mtl_model(
        input_dim=feature_contract.input_dim,
        d_model=architecture["d_model"],
        n_heads=architecture["n_heads"],
        n_layers=architecture["n_layers"],
        d_ff=architecture["d_ff"],
        dropout=architecture["dropout"],
        max_seq_len=architecture["max_seq_len"],
        min_seq_len=architecture["min_seq_len"],
        loss_weights=tuple(architecture["loss_weights"]),
        loss_type=architecture["loss_type"],
        loss_alpha=architecture["loss_alpha"],
    )

    if checkpoint_path is None or not str(checkpoint_path).strip():
        raise ModelArtifactError("--model is required outside --dry-run")
    ckpt_path = Path(checkpoint_path)
    if not ckpt_path.is_absolute():
        ckpt_path = PROJECT_ROOT / ckpt_path
    if not ckpt_path.exists():
        raise FileNotFoundError(f"model checkpoint not found: {ckpt_path}")

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    if not isinstance(ckpt, Mapping):
        raise ModelArtifactError(f"checkpoint must be a mapping with manifest: {ckpt_path}")
    scaler = validate_model_artifact_manifest(
        ckpt.get("manifest"),
        expected_model_family=model_family,
        contract=feature_contract,
        expected_architecture=architecture,
        expected_label_mode=label_mode,
    )
    state = ckpt.get("model_state_dict")
    if not isinstance(state, Mapping):
        raise ValueError(f"invalid checkpoint: {ckpt_path}")
    try:
        model.load_state_dict(state, strict=True)
    except RuntimeError as exc:
        raise ModelArtifactError(f"checkpoint state_dict is incompatible with active model profile: {ckpt_path}") from exc
    model.eval()
    return model, feature_contract, scaler


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
        if not args.model:
            raise ValueError("--model is required outside --dry-run")
        data_source, calendar_source = _build_data_source(args.data_source_config)
        universe_items = [{"symbol": s, "name": ""} for s in (args.symbols or [x["symbol"] for x in _default_universe_items()])]
        universe_filter = StaticUniverseFilter(universe_items)
        model, feature_contract, scaler = _load_model(args.model_config, args.model)
        feature_builder = DataSourceFeatureBuilder(
            data_source=data_source,
            feature_contract=feature_contract,
            scaler=scaler,
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
