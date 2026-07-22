"""MS-R4 A1-bound DataLake factory (cache-first TuShare primary).

Consumers should prefer ``make_r4_datalake`` for R4 lake work so defaults stay
aligned with ``WT-R4-A1-lake-source-contract`` (frozen_for_A2):

- primary source: tushare
- adjust: qfq
- cache_root: inputs/data/cache
- universe: custom_research_liquidity_quality_v1 @ 1 (61)
- history_start: 2023-01-01
- refresh: False (R1 audit reuse; A3 owns limited-live)

Approved L2 rate caps live in ``inputs/configs/tushare_rate_limits.toml``
(promoted from WT-R4-A1 ``accept_recommended``).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from ashare_infra.lake import DataLake

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Locked from WT-R4-A1 (frozen_for_A2)
R4_CONTRACT_ID = "MS-R4-001-lake-source-v0"
R4_PRIMARY_SOURCE = "tushare"
R4_ADJUST_DEFAULT = "qfq"
R4_CACHE_ROOT = Path("inputs/data/cache")
R4_HISTORY_START = "2023-01-01"
R4_STOCK_POOL_ID = "custom_research_liquidity_quality_v1"
R4_STOCK_POOL_VERSION = "1"
R4_SYMBOLS_COUNT = 61
R4_POOL_REGISTRY = Path("inputs/pools/research_liquidity_quality/")
R4_RATE_LIMITS_CONFIG = Path("inputs/configs/tushare_rate_limits.toml")

# Fallback mirrors approved A1 caps if config file is absent.
_R4_CAPS_FALLBACK = {"rpm": 180, "daily_api_calls_per_api": 80000}


def make_r4_datalake(
    cache_dir: Path | str | None = None,
    *,
    refresh: bool = False,
    tushare_token: str | None = None,
) -> DataLake:
    """Build a cache-first DataLake with R4/A1 defaults (TuShare primary, qfq)."""
    root = Path(cache_dir) if cache_dir is not None else R4_CACHE_ROOT
    return DataLake(
        cache_dir=root,
        default_source=R4_PRIMARY_SOURCE,  # type: ignore[arg-type]
        refresh=refresh,
        tushare_token=tushare_token,
    )


@lru_cache(maxsize=1)
def load_r4_rate_limits(
    config_path: str | None = None,
) -> dict[str, Any]:
    """Load approved L2 rate caps from repo config (A1 → fixed file).

    Returns a dict with at least ``approved_caps.rpm`` and
    ``approved_caps.daily_api_calls_per_api``. Does not perform live calls.
    """
    path = Path(config_path) if config_path else R4_RATE_LIMITS_CONFIG
    if not path.is_file():
        return {
            "status": "fallback",
            "approved_caps": dict(_R4_CAPS_FALLBACK),
            "config_path": str(path),
        }
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    caps = payload.get("approved_caps") or {}
    rpm = int(caps.get("rpm", _R4_CAPS_FALLBACK["rpm"]))
    daily = int(
        caps.get("daily_api_calls_per_api", _R4_CAPS_FALLBACK["daily_api_calls_per_api"])
    )
    return {
        "status": str(payload.get("status", "unknown")),
        "contract_id": payload.get("contract_id"),
        "approval_choice": payload.get("approval_choice"),
        "account_points": payload.get("account_points"),
        "applies_to": payload.get("applies_to"),
        "approved_caps": {"rpm": rpm, "daily_api_calls_per_api": daily},
        "config_path": str(path),
        "raw": payload,
    }


def r4_approved_rpm() -> int:
    return int(load_r4_rate_limits()["approved_caps"]["rpm"])


def r4_approved_daily_per_api() -> int:
    return int(load_r4_rate_limits()["approved_caps"]["daily_api_calls_per_api"])


__all__ = [
    "R4_ADJUST_DEFAULT",
    "R4_CACHE_ROOT",
    "R4_CONTRACT_ID",
    "R4_HISTORY_START",
    "R4_POOL_REGISTRY",
    "R4_PRIMARY_SOURCE",
    "R4_RATE_LIMITS_CONFIG",
    "R4_STOCK_POOL_ID",
    "R4_STOCK_POOL_VERSION",
    "R4_SYMBOLS_COUNT",
    "load_r4_rate_limits",
    "make_r4_datalake",
    "r4_approved_daily_per_api",
    "r4_approved_rpm",
]
