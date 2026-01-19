"""Parquet sequence dataset loader.

This module loads flattened sequence datasets produced by `scripts/build_sequence_dataset.py`.

Expected parquet schema:
- label columns: label_3d, label_5d, label_10d (float; NaNs allowed)
- feature columns: {feature_base}_t{0..seq_len-1} (flattened sequence)
- optional meta columns: date, symbol, mask (ignored)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch

__all__ = ["load_sequence_parquet"]


def _infer_label_columns(df: pd.DataFrame) -> list[str]:
    cols: list[tuple[int, str]] = []
    for c in df.columns:
        if isinstance(c, str) and c.startswith("label_") and c.endswith("d"):
            mid = c[len("label_") : -1]
            if mid.isdigit():
                cols.append((int(mid), c))
    cols = sorted(cols, key=lambda x: x[0])
    return [c for _, c in cols]


def _infer_feature_bases(df: pd.DataFrame, seq_len: int) -> list[str]:
    # Expect flattened columns: {base}_t{t}. Find bases that have t0..t{seq_len-1}.
    bases: set[str] = set()
    for c in df.columns:
        if not isinstance(c, str):
            continue  # pragma: no cover
        if c.endswith("_t0"):
            bases.add(c[: -len("_t0")])

    out: list[str] = []
    for base in sorted(bases):
        ok = True
        for t in range(seq_len):
            if f"{base}_t{t}" not in df.columns:
                ok = False
                break
        if ok:
            out.append(base)
    return out


def _infer_seq_len(df: pd.DataFrame) -> int | None:
    # Look for suffix _t{n}; return max+1.
    max_t: int | None = None
    for c in df.columns:
        if not isinstance(c, str):
            continue  # pragma: no cover
        if "_t" not in c:
            continue
        t_str = c.rsplit("_t", 1)[1]
        if not t_str.isdigit():
            continue
        t = int(t_str)
        if max_t is None or t > max_t:
            max_t = t
    return None if max_t is None else (max_t + 1)


def load_sequence_parquet(path: Path, seq_len: int | None = None) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """Load a flattened sequence dataset split from parquet.

    Returns:
        X: [N, seq_len, n_feat] float32
        y: [N, 3] float32 (NaNs preserved)
        info: dict with inferred columns and shapes
    """
    df = pd.read_parquet(path)
    inferred_len = _infer_seq_len(df)
    if seq_len is None:
        if inferred_len is None:
            raise ValueError(f"cannot infer seq_len from columns in {path}")
        seq_len = inferred_len
    else:
        if inferred_len is not None and inferred_len != seq_len:
            raise ValueError(f"seq_len mismatch: config={seq_len}, data={inferred_len} ({path})")

    label_cols = _infer_label_columns(df)
    if label_cols[:3] != ["label_3d", "label_5d", "label_10d"]:
        # tolerate additional labels, but require these 3 to exist
        required = {"label_3d", "label_5d", "label_10d"}
        if not required.issubset(set(label_cols)):
            raise ValueError(f"parquet must contain labels {sorted(required)}; got {label_cols}")
        label_cols = ["label_3d", "label_5d", "label_10d"]

    bases = _infer_feature_bases(df, seq_len)
    if not bases:
        raise ValueError(f"no flattened feature columns like '*_t0' found in {path}")

    feature_cols = [f"{base}_t{t}" for t in range(seq_len) for base in bases]
    X_flat = df[feature_cols].to_numpy(dtype=np.float32, copy=False)
    X = X_flat.reshape(X_flat.shape[0], seq_len, len(bases))
    y = df[label_cols].to_numpy(dtype=np.float32, copy=False)

    return (
        torch.from_numpy(X),
        torch.from_numpy(y),
        {"seq_len": seq_len, "input_dim": len(bases), "feature_bases": bases, "label_cols": label_cols},
    )
