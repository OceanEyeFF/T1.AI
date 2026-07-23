"""R4 minimal derived builder (WT-R4-A4-T2).

Cache-only by default: reads ``tushare_qfq`` partitions, computes M1 features via
``ashare_lab.features`` (no second formula truth), writes
``inputs/data/derived/{family}/{ts_code}/year=*/part.parquet``.

Does **not** call TuShare. Empty/missing cache → skip symbol (no live fill).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_infra.lake.r4_contract import (
    R4_ADJUST_DEFAULT,
    R4_CACHE_ROOT,
    R4_DERIVED_FAMILY_MOMENTUM,
    R4_DERIVED_FAMILY_TECHNICAL,
    R4_DERIVED_MINIMAL_FAMILIES,
    R4_DERIVED_ROOT,
    R4_HISTORY_START,
    r4_derived_required_columns,
)
from ashare_infra.lake.r4_derived_io import (
    read_r4_qfq_cache,
    write_r4_derived_parts,
)
from ashare_lab.features.momentum import Return5D, Return10D, Return20D
from ashare_lab.features.technical import RSI
from ashare_lab.symbols import symbol_to_ts_code


@dataclass
class DerivedBuildResult:
    """Per-symbol build outcome."""

    ts_code: str
    status: str  # built | skipped_empty_cache | skipped_empty_features
    rows_by_family: dict[str, int] = field(default_factory=dict)
    parts_written: list[str] = field(default_factory=list)
    note: str | None = None


def _ensure_ohlcv_index(bars: pd.DataFrame) -> pd.DataFrame:
    """Normalize to DatetimeIndex named date with OHLCV columns for features."""
    if bars is None or bars.empty:
        return pd.DataFrame()
    out = bars.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        if "date" in out.columns:
            out["date"] = pd.to_datetime(out["date"])
            out = out.set_index("date")
        else:
            raise ValueError("bars require DatetimeIndex or date column")
    out = out.sort_index()
    out.index.name = "date"
    if "close" not in out.columns:
        raise ValueError("bars require close column for derived features")
    return out


def compute_r4_minimal_families(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute M1 family frames from OHLCV bars using lab features.

    Returns mapping family → DataFrame with DatetimeIndex and required columns
    (without the ``date`` column; date is the index).
    """
    frame = _ensure_ohlcv_index(bars)
    if frame.empty:
        return {
            R4_DERIVED_FAMILY_MOMENTUM: pd.DataFrame(
                columns=[c for c in r4_derived_required_columns("momentum") if c != "date"]
            ),
            R4_DERIVED_FAMILY_TECHNICAL: pd.DataFrame(
                columns=[c for c in r4_derived_required_columns("technical") if c != "date"]
            ),
        }

    momentum_features = [Return5D(), Return10D(), Return20D()]
    technical_features = [RSI(period=14)]

    mom: dict[str, pd.Series] = {}
    for feat in momentum_features:
        mom[feat.name] = feat.compute(frame)
    tech: dict[str, pd.Series] = {}
    for feat in technical_features:
        tech[feat.name] = feat.compute(frame)

    momentum_df = pd.DataFrame(mom, index=frame.index)
    momentum_df.index.name = "date"
    technical_df = pd.DataFrame(tech, index=frame.index)
    technical_df.index.name = "date"
    return {
        R4_DERIVED_FAMILY_MOMENTUM: momentum_df,
        R4_DERIVED_FAMILY_TECHNICAL: technical_df,
    }


def build_r4_derived_symbol(
    symbol: str,
    *,
    cache_dir: Path | str | None = None,
    derived_root: Path | str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> DerivedBuildResult:
    """Build M1 derived parts for one symbol from cache only (zero live).

    ``start``/``end`` (YYYYMMDD or ISO) optionally slice bars before compute.
    Missing cache → ``skipped_empty_cache`` (does not fetch).
    """
    ts_code = symbol_to_ts_code(symbol)
    cache = Path(cache_dir) if cache_dir is not None else R4_CACHE_ROOT
    droot = Path(derived_root) if derived_root is not None else R4_DERIVED_ROOT

    bars = read_r4_qfq_cache(ts_code, cache_dir=cache)
    if bars.empty:
        return DerivedBuildResult(
            ts_code=ts_code,
            status="skipped_empty_cache",
            note=f"no {R4_ADJUST_DEFAULT} cache under {cache / 'tushare_qfq' / ts_code}",
        )

    bars = _ensure_ohlcv_index(bars)
    if start is not None or end is not None:
        lo = pd.to_datetime(start or R4_HISTORY_START)
        hi = pd.to_datetime(end or "20991231")
        bars = bars.loc[(bars.index >= lo) & (bars.index <= hi)]
    elif R4_HISTORY_START:
        lo = pd.to_datetime(R4_HISTORY_START)
        bars = bars.loc[bars.index >= lo]

    if bars.empty:
        return DerivedBuildResult(
            ts_code=ts_code,
            status="skipped_empty_cache",
            note="cache present but empty after history/start slice",
        )

    families = compute_r4_minimal_families(bars)
    rows_by_family: dict[str, int] = {}
    parts: list[str] = []
    any_rows = False
    for fam in sorted(R4_DERIVED_MINIMAL_FAMILIES):
        fam_df = families[fam]
        # Drop rows that are all-NaN for feature cols (warm-up); keep partial NaNs.
        feat_cols = [c for c in fam_df.columns]
        if feat_cols:
            fam_df = fam_df.dropna(how="all", subset=feat_cols)
        rows_by_family[fam] = int(len(fam_df))
        if fam_df.empty:
            continue
        any_rows = True
        written = write_r4_derived_parts(fam_df, fam, ts_code, root=droot)
        parts.extend(str(p) for p in written)

    if not any_rows:
        return DerivedBuildResult(
            ts_code=ts_code,
            status="skipped_empty_features",
            rows_by_family=rows_by_family,
            note="features produced no rows after warm-up dropna",
        )

    return DerivedBuildResult(
        ts_code=ts_code,
        status="built",
        rows_by_family=rows_by_family,
        parts_written=parts,
    )


def build_r4_derived_batch(
    symbols: list[str] | tuple[str, ...],
    *,
    cache_dir: Path | str | None = None,
    derived_root: Path | str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """Build derived parts for many symbols (cache-only). Returns summary dict."""
    results: list[DerivedBuildResult] = []
    for sym in symbols:
        results.append(
            build_r4_derived_symbol(
                sym,
                cache_dir=cache_dir,
                derived_root=derived_root,
                start=start,
                end=end,
            )
        )
    built = [r for r in results if r.status == "built"]
    skipped = [r for r in results if r.status != "built"]
    return {
        "n_symbols": len(results),
        "n_built": len(built),
        "n_skipped": len(skipped),
        "results": results,
    }


__all__ = [
    "DerivedBuildResult",
    "build_r4_derived_batch",
    "build_r4_derived_symbol",
    "compute_r4_minimal_families",
]
