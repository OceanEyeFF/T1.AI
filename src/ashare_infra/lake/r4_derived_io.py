"""R4 derived partition I/O (WT-R4-A4-T2).

Pure filesystem helpers — no feature compute, no TuShare network.
Layout: ``{root}/{family}/{ts_code}/year={YYYY}/part.parquet``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ashare_infra.lake.r4_contract import (
    R4_DERIVED_MINIMAL_FAMILIES,
    R4_DERIVED_PART_FILENAME,
    R4_DERIVED_ROOT,
    R4_DERIVED_SOURCE_NAMESPACE,
    r4_derived_required_columns,
    r4_derived_symbol_dir,
)


def read_r4_qfq_cache(
    ts_code: str,
    *,
    cache_dir: Path | str,
) -> pd.DataFrame:
    """Read ``tushare_qfq`` year parts for ``ts_code`` (DatetimeIndex, no network)."""
    from ashare_infra.data.tushare_source import _read_cached_partitions

    root = Path(cache_dir)
    symbol_dir = root / R4_DERIVED_SOURCE_NAMESPACE / str(ts_code).strip()
    return _read_cached_partitions(symbol_dir)


def write_r4_derived_parts(
    df: pd.DataFrame,
    family: str,
    ts_code: str,
    *,
    root: Path | str | None = None,
) -> list[Path]:
    """Write a derived family frame to year partitions; return written paths.

    ``df`` may use a DatetimeIndex named ``date`` or a ``date`` column.
    Required columns for ``family`` must be present (see ``r4_derived_required_columns``).
    Empty frames write nothing.
    """
    fam = str(family or "").strip()
    if fam not in R4_DERIVED_MINIMAL_FAMILIES:
        raise ValueError(
            f"family={family!r} not in minimal set {sorted(R4_DERIVED_MINIMAL_FAMILIES)}"
        )
    required = r4_derived_required_columns(fam)
    frame = _normalize_derived_frame(df)
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"derived family={fam!r} missing columns: {missing}")

    # Persist only required columns (stable schema); drop extras.
    out = frame.loc[:, list(required)].copy()
    if out.empty:
        return []

    symbol_dir = r4_derived_symbol_dir(fam, ts_code, root=root)
    symbol_dir.mkdir(parents=True, exist_ok=True)
    out["year"] = out["date"].dt.year
    written: list[Path] = []
    for year, year_df in out.groupby("year"):
        year_dir = symbol_dir / f"year={int(year)}"
        year_dir.mkdir(parents=True, exist_ok=True)
        path = year_dir / R4_DERIVED_PART_FILENAME
        year_df.drop(columns=["year"]).to_parquet(path, index=False)
        written.append(path)
    return written


def read_r4_derived_parts(
    family: str,
    ts_code: str,
    *,
    root: Path | str | None = None,
) -> pd.DataFrame:
    """Read all year parts for a derived family/symbol (DatetimeIndex)."""
    symbol_dir = r4_derived_symbol_dir(family, ts_code, root=root)
    if not symbol_dir.is_dir():
        return pd.DataFrame(columns=list(r4_derived_required_columns(family)))

    frames: list[pd.DataFrame] = []
    for part in sorted(symbol_dir.glob(f"year=*/{R4_DERIVED_PART_FILENAME}")):
        df = pd.read_parquet(part)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=list(r4_derived_required_columns(family)))
    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.index.name = "date"
    return combined


def _normalize_derived_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.index, pd.DatetimeIndex):
        if "date" not in out.columns:
            out = out.reset_index()
            if out.columns[0] != "date" and "date" not in out.columns:
                out = out.rename(columns={out.columns[0]: "date"})
    if "date" not in out.columns:
        raise ValueError("derived frame requires a date index or date column")
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)
    return out


__all__ = [
    "read_r4_derived_parts",
    "read_r4_qfq_cache",
    "write_r4_derived_parts",
]
