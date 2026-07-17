"""Local stock_basic meta helpers for DataLake (no network).

Canonical layout under a lake ``cache_dir``::

    {cache_dir}/meta/stock_basic.csv      # preferred for fixtures / small dumps
    {cache_dir}/meta/stock_basic.parquet # also accepted

R4 may later redefine the on-disk constant; this module only reads local files.
Live TuShare ``stock_basic`` pull is out of scope for WT-INFRA-001.5.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ashare_infra.guard.scope import MetaSource, SymbolLifecycle

STOCK_BASIC_DIRNAME = "meta"
STOCK_BASIC_STEM = "stock_basic"
STOCK_BASIC_SUFFIXES = (".csv", ".parquet")


def stock_basic_dir(cache_dir: Path | str) -> Path:
    return Path(cache_dir) / STOCK_BASIC_DIRNAME


def stock_basic_stem_path(cache_dir: Path | str) -> Path:
    """Path without suffix: ``{cache_dir}/meta/stock_basic``."""
    return stock_basic_dir(cache_dir) / STOCK_BASIC_STEM


def resolve_stock_basic_path(
    cache_dir: Path | str,
    path: Path | str | None = None,
) -> Path:
    """Resolve an existing local stock_basic file.

    Raises ``FileNotFoundError`` when missing — never fetches over the network.
    """
    if path is not None:
        resolved = Path(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"stock_basic path not found: {resolved}")
        return resolved

    stem = stock_basic_stem_path(cache_dir)
    tried: list[str] = []
    for suffix in STOCK_BASIC_SUFFIXES:
        candidate = stem.with_suffix(suffix)
        tried.append(str(candidate))
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "stock_basic not found under "
        f"{stem.parent} (tried: {', '.join(tried)}). "
        "WT-INFRA-001.5 only loads local cache/fixture meta; no network pull."
    )


def _parse_day(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat", "null"}:
        return None
    return pd.Timestamp(text).date()


def _normalize_symbol(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        raise ValueError(f"invalid stock_basic symbol: {value!r}")
    # Accept ts_code like 600000.SH → 600000
    if "." in text:
        text = text.split(".", 1)[0]
    return text


def normalize_stock_basic(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize to columns ``symbol``, ``list_date``, ``delist_date``."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "list_date", "delist_date"])

    frame = df.copy()
    cols = {c.lower(): c for c in frame.columns}
    symbol_col = cols.get("symbol") or cols.get("ts_code") or cols.get("code")
    list_col = cols.get("list_date") or cols.get("list_dt")
    delist_col = cols.get("delist_date") or cols.get("delist_dt")
    if symbol_col is None:
        raise ValueError(
            "stock_basic frame requires a symbol/ts_code/code column; "
            f"got {list(frame.columns)}"
        )
    if list_col is None:
        raise ValueError(
            "stock_basic frame requires a list_date column; "
            f"got {list(frame.columns)}"
        )

    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "symbol": _normalize_symbol(row[symbol_col]),
                "list_date": _parse_day(row[list_col]),
                "delist_date": (
                    _parse_day(row[delist_col]) if delist_col is not None else None
                ),
            }
        )
    return pd.DataFrame(rows)


def read_stock_basic(path: Path | str) -> pd.DataFrame:
    """Read CSV or parquet and normalize columns."""
    resolved = Path(path)
    suffix = resolved.suffix.lower()
    if suffix == ".csv":
        raw = pd.read_csv(resolved, dtype=str).fillna("")
    elif suffix in {".parquet", ".pq"}:
        raw = pd.read_parquet(resolved)
    else:
        raise ValueError(
            f"unsupported stock_basic format {suffix!r}; use .csv or .parquet"
        )
    return normalize_stock_basic(raw)


def stock_basic_to_lifecycle_map(
    df: pd.DataFrame,
    *,
    evidence_ref: str,
    source_kind: str = "stock_basic",
) -> dict[str, SymbolLifecycle]:
    """Map normalized stock_basic rows to ``SymbolLifecycle``."""
    normalized = normalize_stock_basic(df)
    out: dict[str, SymbolLifecycle] = {}
    for row in normalized.itertuples(index=False):
        out[str(row.symbol)] = SymbolLifecycle(
            list_date=row.list_date,
            delist_date=row.delist_date,
            source=MetaSource(kind=source_kind, evidence_ref=evidence_ref),
        )
    return out
