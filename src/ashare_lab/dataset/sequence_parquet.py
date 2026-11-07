"""Deprecated compatibility loader for legacy flattened sequence parquet files.

New training must consume a dataset's embedded Feature Contract instead.  This
shim remains so external callers receive an explicit deprecation path rather
than an unexpected import failure.  Unlike the retired implementation it never
silently replaces non-finite features with zero.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ashare_lab.trend_schema import PRIMARY_TREND_LABEL_COLS, infer_label_cols

__all__ = ["load_sequence_parquet"]


def _infer_feature_bases(df: pd.DataFrame, seq_len: int) -> list[str]:
    bases = sorted(
        column[: -len("_t0")]
        for column in df.columns
        if isinstance(column, str) and column.endswith("_t0")
    )
    return [
        base for base in bases if all(f"{base}_t{step}" in df.columns for step in range(seq_len))
    ]


def _infer_seq_len(df: pd.DataFrame) -> int | None:
    steps: list[int] = []
    for column in df.columns:
        if not isinstance(column, str) or "_t" not in column:
            continue
        suffix = column.rsplit("_t", 1)[1]
        if suffix.isdigit():
            steps.append(int(suffix))
    return None if not steps else max(steps) + 1


def load_sequence_parquet(
    path: str | Path, seq_len: int | None = None
) -> tuple[torch.Tensor, torch.Tensor, dict[str, object]]:
    """Load a legacy split while preserving missing labels and rejecting bad X.

    Deprecated callers should migrate to ``FeatureContractLoader`` plus the
    dataset metadata produced by ``build_sequence_dataset.py``.
    """

    warnings.warn(
        "load_sequence_parquet is deprecated; use a versioned Feature Contract and dataset metadata instead",
        DeprecationWarning,
        stacklevel=2,
    )
    parquet_path = Path(path)
    df = pd.read_parquet(parquet_path)
    inferred_len = _infer_seq_len(df)
    if seq_len is None:
        if inferred_len is None:
            raise ValueError(f"cannot infer seq_len from columns in {parquet_path}")
        seq_len = inferred_len
    elif inferred_len is not None and inferred_len != seq_len:
        raise ValueError(f"seq_len mismatch: config={seq_len}, data={inferred_len} ({parquet_path})")
    if seq_len <= 0:
        raise ValueError("seq_len must be > 0")

    available_labels = infer_label_cols(df.columns)
    if not set(PRIMARY_TREND_LABEL_COLS).issubset(available_labels):
        raise ValueError(
            f"parquet must contain labels {list(PRIMARY_TREND_LABEL_COLS)!r}; got {available_labels!r}"
        )
    feature_bases = _infer_feature_bases(df, seq_len)
    if not feature_bases:
        raise ValueError(f"no complete flattened feature columns found in {parquet_path}")
    feature_columns = [f"{base}_t{step}" for step in range(seq_len) for base in feature_bases]
    values = df[feature_columns].to_numpy(dtype=np.float32, copy=True)
    X = values.reshape(values.shape[0], seq_len, len(feature_bases))
    if not np.isfinite(X).all():
        raise ValueError(
            "legacy parquet contains non-finite features; migrate to a Feature Contract "
            "instead of silently zero-imputing them"
        )
    labels = df[list(PRIMARY_TREND_LABEL_COLS)].to_numpy(dtype=np.float32, copy=True)
    return (
        torch.from_numpy(X),
        torch.from_numpy(labels),
        {
            "seq_len": seq_len,
            "input_dim": len(feature_bases),
            "feature_bases": feature_bases,
            "label_cols": list(PRIMARY_TREND_LABEL_COLS),
            "deprecated": True,
        },
    )
