"""R4 derived partition I/O (WT-R4-A4-T2; post-A4 F1 prune + merge).

Pure filesystem helpers — no feature compute, no TuShare network.
Layout: ``{root}/{family}/{ts_code}/year={YYYY}/part.parquet``.

Rebuild semantics (post-A4):
- Years present in the written frame overwrite ``part.parquet`` (atomic tmp+replace).
- After write, prune ``year=*`` dirs not in the qfq cache year set for that symbol.
- Optional incremental merge: date-union with **new wins** before write+prune.
"""

from __future__ import annotations

import shutil
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


def _parse_year_dirname(name: str) -> int | None:
    if not name.startswith("year="):
        return None
    try:
        return int(name.split("=", 1)[1])
    except ValueError:
        return None


def _list_year_dirs(symbol_dir: Path) -> set[int]:
    if not symbol_dir.is_dir():
        return set()
    years: set[int] = set()
    for child in symbol_dir.iterdir():
        if not child.is_dir():
            continue
        y = _parse_year_dirname(child.name)
        if y is not None:
            years.add(y)
    return years


def list_r4_qfq_cache_years(
    ts_code: str,
    *,
    cache_dir: Path | str,
) -> set[int]:
    """Parse ``year=YYYY`` dirs under ``cache_dir/tushare_qfq/{ts_code}/``."""
    symbol_dir = Path(cache_dir) / R4_DERIVED_SOURCE_NAMESPACE / str(ts_code).strip()
    return _list_year_dirs(symbol_dir)


def list_r4_derived_years(
    family: str,
    ts_code: str,
    *,
    root: Path | str | None = None,
) -> set[int]:
    """Parse ``year=YYYY`` dirs under derived ``{family}/{ts_code}/``."""
    return _list_year_dirs(r4_derived_symbol_dir(family, ts_code, root=root))


def prune_r4_derived_years(
    family: str,
    ts_code: str,
    *,
    keep_years: set[int],
    root: Path | str | None = None,
) -> list[Path]:
    """Remove derived ``year=*`` dirs not in ``keep_years``; return removed paths.

    Also removes empty leftover directories under the symbol dir when no year
    partitions remain.
    """
    symbol_dir = r4_derived_symbol_dir(family, ts_code, root=root)
    if not symbol_dir.is_dir():
        return []

    keep = {int(y) for y in keep_years}
    removed: list[Path] = []
    for child in list(symbol_dir.iterdir()):
        if not child.is_dir():
            continue
        y = _parse_year_dirname(child.name)
        if y is None:
            continue
        if y not in keep:
            shutil.rmtree(child)
            removed.append(child)

    # Drop empty leftovers (empty symbol dir after prune).
    if symbol_dir.is_dir() and not any(symbol_dir.iterdir()):
        symbol_dir.rmdir()
    return removed


def merge_r4_derived_by_date(
    existing: pd.DataFrame,
    new: pd.DataFrame,
) -> pd.DataFrame:
    """Union frames on date index; **new wins** on duplicate dates."""
    left = _to_datetime_index_frame(existing)
    right = _to_datetime_index_frame(new)
    if left.empty:
        return right
    if right.empty:
        return left
    # Concat order: existing then new. Drop duplicates *before* sort so
    # keep="last" reliably prefers new (sort can reorder equal-index rows).
    combined = pd.concat([left, right])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined.index.name = "date"
    return combined


def _to_datetime_index_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.index, pd.DatetimeIndex):
        out = out.sort_index()
        out.index = pd.to_datetime(out.index)
        out.index.name = "date"
        if "date" in out.columns:
            out = out.drop(columns=["date"])
        return out
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"])
        out = out.set_index("date").sort_index()
        out.index.name = "date"
        return out
    raise ValueError("derived frame requires a DatetimeIndex or date column")


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
    Empty frames write nothing. Years present in ``df`` overwrite via atomic
    tmp + replace.
    """
    fam = str(family or "").strip()
    if fam not in R4_DERIVED_MINIMAL_FAMILIES:
        raise ValueError(
            f"family={family!r} not in minimal set {sorted(R4_DERIVED_MINIMAL_FAMILIES)}"
        )
    required = r4_derived_required_columns(fam)
    frame = _normalize_derived_frame(df)
    if frame.empty:
        return []
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
        tmp_path = year_dir / f"{R4_DERIVED_PART_FILENAME}.tmp"
        year_df.drop(columns=["year"]).to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
        written.append(path)
    return written


def read_r4_derived_parts(
    family: str,
    ts_code: str,
    *,
    root: Path | str | None = None,
) -> pd.DataFrame:
    """Read all year parts for a derived family/symbol (DatetimeIndex).

    Corrupt/truncated parts are skipped (fail-open), matching cache
    ``_read_cached_partitions`` F-03 behavior.
    """
    symbol_dir = r4_derived_symbol_dir(family, ts_code, root=root)
    if not symbol_dir.is_dir():
        return pd.DataFrame(columns=list(r4_derived_required_columns(family)))

    frames: list[pd.DataFrame] = []
    for part in sorted(symbol_dir.glob(f"year=*/{R4_DERIVED_PART_FILENAME}")):
        try:
            df = pd.read_parquet(part)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            frames.append(df)
        except FileNotFoundError:
            continue
        except (OSError, ValueError):  # corrupt/truncated part → skip
            continue
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
    "list_r4_derived_years",
    "list_r4_qfq_cache_years",
    "merge_r4_derived_by_date",
    "prune_r4_derived_years",
    "read_r4_derived_parts",
    "read_r4_qfq_cache",
    "write_r4_derived_parts",
]
