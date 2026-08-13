"""MS-R4 A1-bound DataLake factory (cache-first TuShare primary).

Consumers should prefer ``make_r4_datalake`` for R4 lake work so defaults stay
aligned with the R4 A1 lake-source contract (frozen for A2+; worktrack artifacts removed):

- primary source: tushare
- adjust: qfq
- cache_root: inputs/data/cache
- universe: custom_research_liquidity_quality_v1 @ 1 (60; 601989 停牌剔除 2026-08-13)
- history_start: 2023-01-01
- refresh: False (R1 audit reuse; A3 owns limited-live)

Approved L2 rate caps live in ``inputs/configs/tushare_rate_limits.toml``
(promoted from WT-R4-A1 ``accept_recommended``). Runtime enforce is via
``ashare_infra.data.tushare_rate_limit`` (wired into ``fetch_tushare_*``).

Derived minimal layout (WT-R4-A4-T1) is also frozen here:
``inputs/data/derived/{family}/{ts_code}/year={YYYY}/part.parquet``
(M1: momentum return_5/10/20d + technical rsi_14). Builder=T2; load via DataLake=T3.
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
R4_SYMBOLS_COUNT = 60
R4_POOL_REGISTRY = Path("inputs/pools/research_liquidity_quality/")
R4_RATE_LIMITS_CONFIG = Path("inputs/configs/tushare_rate_limits.toml")

# Soft80 (A1 G1): experiment accepts 61 < soft_target; hard_cap 100 already met.
R4_SOFT_TARGET = 80
R4_HARD_CAP = 100
R4_SOFT80_STATUS = "accepted_residual"  # WT-R4-A3-T4 D1=C; zero live

# Index / ETF anchor: qfq required; stock daily_basic/moneyflow N/A (A3 T3/T4).
R4_INDEX_ANCHOR = "510300.SH"
R4_INDEX_REQUIRED_NAMESPACES = frozenset({"tushare_qfq"})
R4_INDEX_OPTIONAL_NAMESPACES = frozenset({"tushare_daily_basic", "tushare_moneyflow"})

# Keep in registry v1@1, but default trial/runtime subset excludes upstream-exhausted.
# Bare codes and ts_codes both accepted by helpers.
R4_TRIAL_EXCLUDE_SYMBOLS = frozenset({"601989", "601989.SH"})

# ---------------------------------------------------------------------------
# Derived minimal contract (WT-R4-A4-T1; A4_Q1/Q2 locked at Init)
# Layout mirrors cache: {derived_root}/{family}/{ts_code}/year={YYYY}/part.parquet
# Builder=T2; DataLake.load_derived*=T3; T1 froze constants + path helpers.
# ---------------------------------------------------------------------------
R4_DERIVED_CONTRACT_ID = "MS-R4-001-derived-minimal-v0"
R4_DERIVED_ROOT = Path("inputs/data/derived")
R4_DERIVED_SOURCE_NAMESPACE = "tushare_qfq"  # cache-only input; refresh=False
R4_DERIVED_MINIMAL_SET = "M1_ret_rsi"
R4_DERIVED_FAMILY_MOMENTUM = "momentum"
R4_DERIVED_FAMILY_TECHNICAL = "technical"
R4_DERIVED_MINIMAL_FAMILIES = frozenset(
    {R4_DERIVED_FAMILY_MOMENTUM, R4_DERIVED_FAMILY_TECHNICAL}
)
# Align column names with ashare_lab.features (Return5D/10D/20D, RSI(14)).
R4_DERIVED_MOMENTUM_COLUMNS: tuple[str, ...] = (
    "date",
    "return_5d",
    "return_10d",
    "return_20d",
)
R4_DERIVED_TECHNICAL_COLUMNS: tuple[str, ...] = ("date", "rsi_14")
R4_DERIVED_OPTIONAL_COLUMNS: tuple[str, ...] = ("atr_14",)  # A4_Q1 optional
R4_DERIVED_DEFERRED_FAMILIES = frozenset(
    {"macd", "bollinger", "volatility", "market_state"}
)
R4_DERIVED_PART_FILENAME = "part.parquet"

# Fallback mirrors approved A1 caps if config file is absent.
_R4_CAPS_FALLBACK = {"rpm": 180, "daily_api_calls_per_api": 80000}


def _normalize_symbol_key(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def is_r4_trial_excluded(symbol: str) -> bool:
    """True if symbol is excluded from the default R4 trial subset."""
    key = _normalize_symbol_key(symbol)
    if not key:
        return False
    bare = key.split(".", 1)[0]
    return key in R4_TRIAL_EXCLUDE_SYMBOLS or bare in R4_TRIAL_EXCLUDE_SYMBOLS


def filter_r4_trial_symbols(symbols: list[str] | tuple[str, ...]) -> list[str]:
    """Return symbols for trial runs: registry order preserved, excludes applied."""
    return [s for s in symbols if not is_r4_trial_excluded(s)]


def r4_derived_required_columns(family: str) -> tuple[str, ...]:
    """Required on-disk columns for a minimal derived family (includes ``date``)."""
    name = str(family or "").strip()
    if name == R4_DERIVED_FAMILY_MOMENTUM:
        return R4_DERIVED_MOMENTUM_COLUMNS
    if name == R4_DERIVED_FAMILY_TECHNICAL:
        return R4_DERIVED_TECHNICAL_COLUMNS
    raise ValueError(
        f"unknown derived family={family!r}; "
        f"minimal set is {sorted(R4_DERIVED_MINIMAL_FAMILIES)}"
    )


def r4_derived_symbol_dir(
    family: str,
    ts_code: str,
    *,
    root: Path | str | None = None,
) -> Path:
    """``{root}/{family}/{ts_code}`` under the derived root."""
    base = Path(root) if root is not None else R4_DERIVED_ROOT
    fam = str(family or "").strip()
    code = str(ts_code or "").strip()
    if not fam or not code:
        raise ValueError("family and ts_code are required")
    return base / fam / code


def r4_derived_part_path(
    family: str,
    ts_code: str,
    year: int | str,
    *,
    root: Path | str | None = None,
) -> Path:
    """``{root}/{family}/{ts_code}/year={YYYY}/part.parquet``."""
    y = int(year)
    return (
        r4_derived_symbol_dir(family, ts_code, root=root)
        / f"year={y}"
        / R4_DERIVED_PART_FILENAME
    )


def make_r4_datalake(
    cache_dir: Path | str | None = None,
    *,
    refresh: bool = False,
    tushare_token: str | None = None,
    derived_root: Path | str | None = None,
) -> DataLake:
    """Build a cache-first DataLake with R4/A1 defaults (TuShare primary, qfq).

    ``derived_root`` defaults to ``R4_DERIVED_ROOT`` for ``load_derived*``.
    """
    root = Path(cache_dir) if cache_dir is not None else R4_CACHE_ROOT
    droot = Path(derived_root) if derived_root is not None else R4_DERIVED_ROOT
    return DataLake(
        cache_dir=root,
        default_source=R4_PRIMARY_SOURCE,  # type: ignore[arg-type]
        refresh=refresh,
        tushare_token=tushare_token,
        derived_root=droot,
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
    "R4_DERIVED_CONTRACT_ID",
    "R4_DERIVED_DEFERRED_FAMILIES",
    "R4_DERIVED_FAMILY_MOMENTUM",
    "R4_DERIVED_FAMILY_TECHNICAL",
    "R4_DERIVED_MINIMAL_FAMILIES",
    "R4_DERIVED_MINIMAL_SET",
    "R4_DERIVED_MOMENTUM_COLUMNS",
    "R4_DERIVED_OPTIONAL_COLUMNS",
    "R4_DERIVED_PART_FILENAME",
    "R4_DERIVED_ROOT",
    "R4_DERIVED_SOURCE_NAMESPACE",
    "R4_DERIVED_TECHNICAL_COLUMNS",
    "R4_HARD_CAP",
    "R4_HISTORY_START",
    "R4_INDEX_ANCHOR",
    "R4_INDEX_OPTIONAL_NAMESPACES",
    "R4_INDEX_REQUIRED_NAMESPACES",
    "R4_POOL_REGISTRY",
    "R4_PRIMARY_SOURCE",
    "R4_RATE_LIMITS_CONFIG",
    "R4_SOFT80_STATUS",
    "R4_SOFT_TARGET",
    "R4_STOCK_POOL_ID",
    "R4_STOCK_POOL_VERSION",
    "R4_SYMBOLS_COUNT",
    "R4_TRIAL_EXCLUDE_SYMBOLS",
    "filter_r4_trial_symbols",
    "is_r4_trial_excluded",
    "load_r4_rate_limits",
    "make_r4_datalake",
    "r4_approved_daily_per_api",
    "r4_approved_rpm",
    "r4_derived_part_path",
    "r4_derived_required_columns",
    "r4_derived_symbol_dir",
]
