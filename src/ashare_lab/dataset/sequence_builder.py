"""Sequence dataset builder.

This module converts feature/label DataFrames into fixed-length time series samples:
`X` with shape ``[N, seq_len, n_feat]`` and `y` with shape ``[N, n_label]``.

Key design (per phase-1 MVP spec):
  - Sliding window: fixed ``seq_len`` and step ``stride`` to generate samples.
  - Time alignment: sample whose label timestamp is ``t`` only uses features from
    ``[t-seq_len, ..., t-1]`` (no future leakage).
  - NaN labels are kept (for later masking during training).
  - Walk-forward split: train/valid/test are split strictly by time order.

Note:
    The repository also contains a same-named package directory
    ``src/ashare_lab/dataset/sequence_builder/`` to support the pytest-cov command in the spec:
    ``--cov=src/ashare_lab/dataset/sequence_builder``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class _GroupView:
    symbol: str
    dates: pd.DatetimeIndex
    features: pd.DataFrame
    labels: pd.DataFrame


class SequenceDatasetBuilder:
    """Build sequence dataset from tabular features/labels.

    Args:
        seq_len: Sequence length (number of timesteps per sample).
        stride: Sliding window step. ``stride=1`` means daily slide.

    Attributes:
        feature_columns_: Feature column names used in the latest build.
        label_columns_: Label column names used in the latest build.
        sample_meta_: Sample metadata of the latest build. Columns: ``date``, ``symbol``, ``mask``.
        mask_: Boolean mask of shape ``[N]`` indicating whether all label values are non-NaN.
    """

    def __init__(self, seq_len: int = 30, stride: int = 1) -> None:
        if seq_len <= 0:
            raise ValueError("seq_len must be a positive integer")
        if stride <= 0:
            raise ValueError("stride must be a positive integer")

        self.seq_len = int(seq_len)
        self.stride = int(stride)

        self.feature_columns_: list[str] | None = None
        self.label_columns_: list[str] | None = None
        self.sample_meta_: pd.DataFrame | None = None
        self.mask_: np.ndarray | None = None

    def build_sequences(
        self,
        features: pd.DataFrame,
        labels: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build sliding-window sequences.

        Time alignment:
            For a sample with label timestamp ``t`` (the row ``labels.loc[t]``),
            the input sequence is ``features.loc[t-seq_len : t-1]`` (exclusive of ``t``).

        Args:
            features: Feature DataFrame.
                - Single-series: indexed by date with shape ``[T, n_feat]``.
                - Multi-asset: indexed by MultiIndex (date, symbol) or columns ``date``/``symbol``.
            labels: Label DataFrame aligned by the same index (single-series or multi-asset),
                with shape ``[T, n_label]`` (typically 3 horizons).

        Returns:
            (X, y)
            - X: ``np.ndarray`` with shape ``[N, seq_len, n_feat]``
            - y: ``np.ndarray`` with shape ``[N, n_label]`` (NaNs preserved)

        Raises:
            TypeError: If inputs are not DataFrames.
            ValueError: If index cannot be aligned or not enough data to build sequences.
        """
        if not isinstance(features, pd.DataFrame):
            raise TypeError("features must be a pandas DataFrame")
        if not isinstance(labels, pd.DataFrame):
            raise TypeError("labels must be a pandas DataFrame")
        if features.shape[1] == 0:
            raise ValueError("features must contain at least one column")
        if labels.shape[1] == 0:
            raise ValueError("labels must contain at least one column")

        feats = self._normalize_index(features, require_symbol=False)
        labs = self._normalize_index(labels, require_symbol=False)

        feats, labs = self._align_features_labels(feats, labs)

        self.feature_columns_ = list(feats.columns)
        self.label_columns_ = list(labs.columns)

        group_views = list(self._iter_groups(feats, labs))
        if not group_views:
            return self._empty_arrays(n_feat=len(feats.columns), n_label=len(labs.columns))

        x_parts: list[np.ndarray] = []
        y_parts: list[np.ndarray] = []
        meta_parts: list[pd.DataFrame] = []

        for gv in group_views:
            X_g, y_g, meta_g = self._build_one_group(gv)
            if X_g.size == 0:
                continue
            x_parts.append(X_g)
            y_parts.append(y_g)
            meta_parts.append(meta_g)

        if not x_parts:
            return self._empty_arrays(n_feat=len(feats.columns), n_label=len(labs.columns))

        X = np.concatenate(x_parts, axis=0)
        y = np.concatenate(y_parts, axis=0)

        sample_meta = pd.concat(meta_parts, ignore_index=True)
        mask = ~np.isnan(y).any(axis=1)
        sample_meta["mask"] = mask

        self.sample_meta_ = sample_meta
        self.mask_ = mask
        return X, y

    def split_walk_forward(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """Split dataset into train/valid/test using walk-forward (time-ordered) split.

        Splitting rule:
            - If ``sample_meta_`` is available (from the latest ``build_sequences`` call),
              split by unique dates to guarantee no time overlap.
            - Otherwise, split by contiguous sample order.

        Args:
            X: Features array with shape ``[N, seq_len, n_feat]``.
            y: Labels array with shape ``[N, n_label]``.
            train_ratio: Ratio for train split.
            valid_ratio: Ratio for validation split.

        Returns:
            A dict with keys: ``train``, ``valid``, ``test``. Each contains ``X`` and ``y``.

        Raises:
            ValueError: If ratios are invalid or input shapes mismatch.
        """
        if X.ndim != 3:
            raise ValueError("X must have shape [N, seq_len, n_feat]")
        if y.ndim != 2:
            raise ValueError("y must have shape [N, n_label]")
        if X.shape[0] != y.shape[0]:
            raise ValueError("X and y must have the same number of samples")
        if not (0.0 < train_ratio < 1.0):
            raise ValueError("train_ratio must be in (0, 1)")
        if not (0.0 <= valid_ratio < 1.0):
            raise ValueError("valid_ratio must be in [0, 1)")
        if train_ratio + valid_ratio >= 1.0:
            raise ValueError("train_ratio + valid_ratio must be < 1")

        n = X.shape[0]
        if n == 0:
            return {
                "train": {"X": X, "y": y},
                "valid": {"X": X, "y": y},
                "test": {"X": X, "y": y},
            }

        if self.sample_meta_ is not None and "date" in self.sample_meta_.columns:
            dates = pd.to_datetime(self.sample_meta_["date"])
            unique_dates = np.array(sorted(pd.unique(dates)))
            n_dates = len(unique_dates)

            if n_dates == 0:
                return self._split_by_count(X, y, train_ratio, valid_ratio)

            train_cut = max(1, int(n_dates * train_ratio))
            valid_cut = max(train_cut, int(n_dates * (train_ratio + valid_ratio)))
            train_cut = min(train_cut, n_dates)
            valid_cut = min(valid_cut, n_dates)

            train_dates = set(unique_dates[:train_cut].tolist())
            valid_dates = set(unique_dates[train_cut:valid_cut].tolist())

            is_train = dates.isin(train_dates).to_numpy()
            is_valid = dates.isin(valid_dates).to_numpy()
            is_test = ~(is_train | is_valid)

            return {
                "train": {"X": X[is_train], "y": y[is_train]},
                "valid": {"X": X[is_valid], "y": y[is_valid]},
                "test": {"X": X[is_test], "y": y[is_test]},
            }

        return self._split_by_count(X, y, train_ratio, valid_ratio)

    def _split_by_count(
        self, X: np.ndarray, y: np.ndarray, train_ratio: float, valid_ratio: float
    ) -> Dict[str, Dict[str, np.ndarray]]:
        n = X.shape[0]
        train_end = int(n * train_ratio)
        valid_end = int(n * (train_ratio + valid_ratio))
        return {
            "train": {"X": X[:train_end], "y": y[:train_end]},
            "valid": {"X": X[train_end:valid_end], "y": y[train_end:valid_end]},
            "test": {"X": X[valid_end:], "y": y[valid_end:]},
        }

    def _build_one_group(self, gv: _GroupView) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        f_values = gv.features.to_numpy(dtype=np.float32, copy=False)
        y_values = gv.labels.to_numpy(dtype=np.float32, copy=False)
        t = f_values.shape[0]

        n_samples = t - self.seq_len
        if n_samples <= 0:
            X_empty, y_empty = self._empty_arrays(n_feat=f_values.shape[1], n_label=y_values.shape[1])
            meta_empty = pd.DataFrame(columns=["date", "symbol", "mask"])
            return X_empty, y_empty, meta_empty

        windows = np.lib.stride_tricks.sliding_window_view(
            f_values, window_shape=(self.seq_len, f_values.shape[1])
        )
        windows = windows.reshape(windows.shape[0], self.seq_len, f_values.shape[1])

        X_g = windows[:n_samples : self.stride]
        y_g = y_values[self.seq_len : t : self.stride]
        dates_g = gv.dates[self.seq_len : t : self.stride]

        meta_g = pd.DataFrame({"date": dates_g, "symbol": gv.symbol})
        return X_g, y_g, meta_g

    def _iter_groups(self, feats: pd.DataFrame, labs: pd.DataFrame) -> Iterator[_GroupView]:
        if isinstance(feats.index, pd.MultiIndex):
            feats = feats.sort_index()
            labs = labs.sort_index()
            for symbol, fdf in feats.groupby(level="symbol", sort=False):
                ldf = labs.xs(symbol, level="symbol", drop_level=False)
                fdf_ = fdf.droplevel("symbol")
                ldf_ = ldf.droplevel("symbol")
                dates = pd.DatetimeIndex(fdf_.index)
                yield _GroupView(symbol=str(symbol), dates=dates, features=fdf_, labels=ldf_)
            return

        feats = feats.sort_index()
        labs = labs.sort_index()
        dates = pd.DatetimeIndex(feats.index)
        yield _GroupView(symbol="__single__", dates=dates, features=feats, labels=labs)

    def _normalize_index(self, df: pd.DataFrame, require_symbol: bool) -> pd.DataFrame:
        if isinstance(df.index, pd.MultiIndex):
            if df.index.nlevels != 2:
                raise ValueError("MultiIndex input must have exactly 2 levels (date, symbol)")
            level_names = list(df.index.names)

            date_level = 0
            if "date" in level_names:
                date_level = level_names.index("date")
            else:
                for i, lvl in enumerate(df.index.levels):
                    if pd.api.types.is_datetime64_any_dtype(lvl.dtype):
                        date_level = i
                        break

            symbol_level = 1 - date_level
            if date_level != 0:
                df = df.reorder_levels([date_level, symbol_level]).copy()

            df.index = df.index.set_names(["date", "symbol"])
            df = df.sort_index()

            df = df.copy()
            dates = pd.to_datetime(df.index.get_level_values("date"))
            symbols = df.index.get_level_values("symbol")
            df.index = pd.MultiIndex.from_arrays([dates, symbols], names=["date", "symbol"])
            return df.sort_index()

        if {"date", "symbol"}.issubset(df.columns):
            tmp = df.copy()
            tmp["date"] = pd.to_datetime(tmp["date"])
            tmp["symbol"] = tmp["symbol"].astype(str)
            tmp = tmp.set_index(["date", "symbol"]).sort_index()
            return tmp

        if require_symbol:
            raise ValueError("multi-asset input requires MultiIndex or 'date'/'symbol' columns")

        tmp = df.copy()
        try:
            tmp.index = pd.to_datetime(tmp.index)
        except Exception as e:  # pragma: no cover
            raise ValueError("index must be datetime-like for single-series input") from e
        tmp.index.name = tmp.index.name or "date"
        return tmp.sort_index()

    def _align_features_labels(self, feats: pd.DataFrame, labs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        if isinstance(feats.index, pd.MultiIndex) != isinstance(labs.index, pd.MultiIndex):
            raise ValueError("features and labels must use the same index type")

        common_idx = feats.index.intersection(labs.index)
        feats_aligned = feats.loc[common_idx].sort_index()
        labs_aligned = labs.loc[common_idx].sort_index()
        return feats_aligned, labs_aligned

    def _empty_arrays(self, n_feat: int, n_label: int) -> tuple[np.ndarray, np.ndarray]:
        X = np.zeros((0, self.seq_len, n_feat), dtype=np.float32)
        y = np.zeros((0, n_label), dtype=np.float32)
        return X, y
