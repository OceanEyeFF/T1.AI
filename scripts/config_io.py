"""Config I/O helpers for script-level JSON/TOML argument loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <=3.10 fallback
    import tomli as tomllib


def load_mapping_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON/TOML config file as a mapping."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {p}")

    suffix = p.suffix.lower()
    if suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
    elif suffix == ".toml":
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"unsupported config format: {p} (only .json/.toml)")

    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {p}")
    return dict(data)


def extract_arg_overrides(
    *,
    config_path: str | Path,
    allowed_keys: set[str],
    section_candidates: tuple[str, ...] = (),
) -> tuple[dict[str, Any], str | None]:
    """Extract argparse-style overrides from config.

    Supported shapes:
    1) flat mapping: { "lr": 1e-4, ... }
    2) with section: { "run_lstm_rolling_retrain_dim19_regime": { ... } }
    3) generic args section: { "args": { ... } }
    """
    raw = load_mapping_config(config_path)
    selected: Mapping[str, Any] = raw
    selected_section: str | None = None

    for sec in section_candidates:
        sec_value = raw.get(sec)
        if isinstance(sec_value, dict):
            selected = sec_value
            selected_section = sec
            break

    if selected_section is None:
        args_value = raw.get("args")
        if isinstance(args_value, dict):
            selected = args_value
            selected_section = "args"

    unknown = sorted(k for k in selected.keys() if k not in allowed_keys)
    if unknown:
        raise ValueError(
            f"unknown config keys in {config_path}: {unknown}. "
            f"allowed keys: {sorted(allowed_keys)}"
        )

    return ({k: selected[k] for k in selected.keys() if k in allowed_keys}, selected_section)


def dump_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
