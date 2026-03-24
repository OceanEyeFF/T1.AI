"""Shared runtime metadata helpers for experiment/report contracts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

DEFAULT_EVALUATION_WINDOW_ID = "fixed_20230101_20250701"
DEFAULT_STOCK_POOL_VERSION = "v1"
CANONICAL_CONFIG_STATUS_CHOICES = ("baseline", "candidate", "frozen")
CONFIG_STATUS_ALIASES = {
    "baseline": "baseline",
    "candidate": "candidate",
    "candidate-best": "candidate",
    "frozen": "frozen",
    "frozen-best": "frozen",
}
PARSER_CONFIG_STATUS_CHOICES = tuple(CONFIG_STATUS_ALIASES.keys())


def canonicalize_config_status(config_status: str) -> str:
    text = str(config_status).strip()
    if text not in CONFIG_STATUS_ALIASES:
        raise ValueError(
            f"unsupported config_status: {config_status}. "
            f"allowed: {sorted(PARSER_CONFIG_STATUS_CHOICES)}"
        )
    return CONFIG_STATUS_ALIASES[text]


def load_dataset_metadata(dataset_dir: str | Path) -> dict[str, Any]:
    path = Path(dataset_dir) / "metadata.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _dataset_config(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    value = metadata.get("dataset_config")
    return value if isinstance(value, Mapping) else {}


def _feature_config(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    value = metadata.get("feature_config")
    return value if isinstance(value, Mapping) else {}


def _pool_scope_from_stock_pool_id(stock_pool_id: str) -> str:
    text = str(stock_pool_id).strip()
    if text.startswith("custom_"):
        return text.removeprefix("custom_")
    return text


def _infer_stock_pool_id_from_symbols_source(dataset_cfg: Mapping[str, Any]) -> str:
    explicit = dataset_cfg.get("stock_pool_id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    symbols_source = str(dataset_cfg.get("symbols_csv", "")).lower()
    if "csi300" in symbols_source:
        return "csi300"

    quick_match = re.search(r"quick(\d+)", symbols_source)
    if quick_match:
        return f"custom_quick{quick_match.group(1)}"

    sector_match = re.search(r"sector(?:s)?[_-]?(\d+)", symbols_source)
    if sector_match:
        return f"custom_sector{sector_match.group(1)}"

    num_symbols = dataset_cfg.get("num_symbols")
    if isinstance(num_symbols, int) and num_symbols > 0:
        return f"custom_symbols{num_symbols}"
    return "csi300"


def _infer_dataset_type_abbr(dataset_dir: Path, dataset_meta: Mapping[str, Any]) -> str:
    dataset_type = dataset_meta.get("dataset_type")
    if isinstance(dataset_type, str):
        lowered = dataset_type.strip().lower()
        if lowered in {"sequence", "seq"}:
            return "seq"
        if lowered in {"market_state", "market-state", "mkt"}:
            return "mkt"
        if lowered == "panel":
            return "panel"

    name = dataset_dir.name.lower()
    if "market_state" in name or "_mkt_" in name:
        return "mkt"
    return "seq"


def infer_dataset_id(
    *,
    dataset_dir: str | Path,
    dataset_metadata: Mapping[str, Any],
    dataset_id: str,
    stock_pool_id: str,
) -> str:
    if str(dataset_id).strip():
        return str(dataset_id).strip()

    existing = dataset_metadata.get("dataset_id")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()

    dataset_cfg = _dataset_config(dataset_metadata)
    feature_cfg = _feature_config(dataset_metadata)
    start_date = str(dataset_cfg.get("start_date", "")).strip()
    end_date = str(dataset_cfg.get("end_date", "")).strip()
    num_features = feature_cfg.get("num_features")
    if start_date and end_date and isinstance(num_features, int) and num_features > 0:
        scope = _pool_scope_from_stock_pool_id(stock_pool_id)
        type_abbr = _infer_dataset_type_abbr(Path(dataset_dir), dataset_metadata)
        return f"{type_abbr}_{scope}_{num_features}d_{start_date}_{end_date}"

    return Path(dataset_dir).name


def resolve_experiment_context(
    *,
    dataset_dir: str | Path,
    model_track: str,
    config_profile: str,
    config_status: str,
    stock_pool_id: str = "",
    stock_pool_version: str = "",
    evaluation_window_id: str = "",
    dataset_id: str = "",
) -> dict[str, str]:
    dataset_meta = load_dataset_metadata(dataset_dir)
    dataset_cfg = _dataset_config(dataset_meta)
    resolved_stock_pool_id = (
        str(stock_pool_id).strip() or _infer_stock_pool_id_from_symbols_source(dataset_cfg)
    )
    resolved_stock_pool_version = (
        str(stock_pool_version).strip()
        or str(dataset_cfg.get("stock_pool_version", "")).strip()
        or DEFAULT_STOCK_POOL_VERSION
    )
    resolved_dataset_id = infer_dataset_id(
        dataset_dir=dataset_dir,
        dataset_metadata=dataset_meta,
        dataset_id=dataset_id,
        stock_pool_id=resolved_stock_pool_id,
    )
    resolved_evaluation_window_id = (
        str(evaluation_window_id).strip() or DEFAULT_EVALUATION_WINDOW_ID
    )
    return {
        "model_track": str(model_track).strip(),
        "config_profile": str(config_profile).strip(),
        "config_status": canonicalize_config_status(config_status),
        "stock_pool_id": resolved_stock_pool_id,
        "stock_pool_version": resolved_stock_pool_version,
        "evaluation_window_id": resolved_evaluation_window_id,
        "dataset_id": resolved_dataset_id,
    }


def _profile_tag_from_config_profile(config_profile: str, backbone: str) -> str:
    text = str(config_profile).strip()
    prefix = f"{backbone}_"
    if text.startswith(prefix):
        remainder = text[len(prefix) :]
        if "_" in remainder:
            return remainder.split("_", 1)[1]
        if remainder:
            return remainder
    return text or backbone


def build_default_report_path(
    *,
    backbone: str,
    model_track: str,
    config_profile: str,
    generated_at: datetime,
    reports_root: str | Path = "output/reports",
) -> Path:
    date_tag = generated_at.strftime("%Y%m%d")
    profile_tag = _profile_tag_from_config_profile(config_profile, backbone)
    return Path(reports_root) / model_track / f"{backbone}_{profile_tag}_{date_tag}.json"


def build_effective_config_payload(
    *,
    context: Mapping[str, str],
    seed: int,
    script: str,
    config_file: str,
    generated_at: datetime,
    args_mapping: Mapping[str, Any],
) -> dict[str, Any]:
    date_tag = generated_at.strftime("%Y%m%d")
    return {
        "experiment_id": f"{context['config_profile']}_{context['model_track']}_{date_tag}",
        "model_track": context["model_track"],
        "config_profile": context["config_profile"],
        "config_status": context["config_status"],
        "stock_pool_id": context["stock_pool_id"],
        "stock_pool_version": context["stock_pool_version"],
        "evaluation_window_id": context["evaluation_window_id"],
        "dataset_id": context["dataset_id"],
        "seed": int(seed),
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "script": script,
        "config_file": config_file or None,
        "args": dict(args_mapping),
    }
