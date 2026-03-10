"""Shared schema for the primary 3d/5d/10d trend heads.

This module centralizes the canonical horizon order for the main trend line,
so labels, predictions and weight keys do not drift across model/data scripts.
"""

from __future__ import annotations

import re
from typing import Iterable

PRIMARY_TREND_HORIZONS: tuple[int, ...] = (3, 5, 10)
PRIMARY_TREND_LABEL_COLS: tuple[str, ...] = tuple(f"label_{h}d" for h in PRIMARY_TREND_HORIZONS)
PRIMARY_TREND_PRED_COLS: tuple[str, ...] = tuple(f"pred_{h}d" for h in PRIMARY_TREND_HORIZONS)
PRIMARY_TREND_WEIGHT_KEYS: tuple[str, ...] = tuple(f"w{h}" for h in PRIMARY_TREND_HORIZONS)

PRIMARY_TREND_WEIGHT_BY_LABEL: dict[str, str] = dict(zip(PRIMARY_TREND_LABEL_COLS, PRIMARY_TREND_WEIGHT_KEYS))
PRIMARY_TREND_WEIGHT_BY_PRED: dict[str, str] = dict(zip(PRIMARY_TREND_PRED_COLS, PRIMARY_TREND_WEIGHT_KEYS))

_PLAIN_LABEL_RE = re.compile(r"label_(\d+)d$")
_SUFFIX_LABEL_RE = re.compile(r"label_(\d+)d_(.+)$")


def label_col_for_horizon(horizon: int) -> str:
    return f"label_{int(horizon)}d"


def pred_col_for_horizon(horizon: int) -> str:
    return f"pred_{int(horizon)}d"


def pred_col_from_label(label_col: str) -> str:
    if not str(label_col).startswith("label_"):
        raise ValueError(f"invalid label column: {label_col}")
    return f"pred_{str(label_col)[6:]}"


def target_name_from_label(label_col: str) -> str:
    if not str(label_col).startswith("label_"):
        raise ValueError(f"invalid label column: {label_col}")
    return str(label_col)[6:]


def target_name_from_pred(pred_col: str) -> str:
    if not str(pred_col).startswith("pred_"):
        raise ValueError(f"invalid prediction column: {pred_col}")
    return str(pred_col)[5:]


def label_sort_key(col: str) -> tuple[int, int, str]:
    text = str(col)
    plain = _PLAIN_LABEL_RE.fullmatch(text)
    if plain is not None:
        return (0, int(plain.group(1)), "")
    suffix = _SUFFIX_LABEL_RE.fullmatch(text)
    if suffix is not None:
        return (1, int(suffix.group(1)), str(suffix.group(2)))
    return (2, 10**9, text)


def infer_label_cols(columns: Iterable[object]) -> list[str]:
    labels = [str(col) for col in columns if isinstance(col, str) and col.startswith("label_")]
    if not labels:
        return []

    ordered = sorted(labels, key=label_sort_key)
    if not all(col in labels for col in PRIMARY_TREND_LABEL_COLS):
        return ordered

    extras = [col for col in ordered if col not in PRIMARY_TREND_LABEL_COLS]
    return list(PRIMARY_TREND_LABEL_COLS) + extras
