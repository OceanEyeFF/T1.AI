"""Tests for SequenceDatasetBuilder.

Focus:
  - output shapes
  - strict time alignment (no leakage)
  - NaN label preservation with mask
  - walk-forward split boundaries
  - multi-stock support
  - empty/boundary cases
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.dataset.sequence_builder import SequenceDatasetBuilder


def _make_single_series(
    n_days: int, n_feat: int = 4, n_label: int = 3
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    features = pd.DataFrame(
        {f"f{i}": np.arange(n_days, dtype=np.float32) + i * 100 for i in range(n_feat)},
        index=dates,
    )
    labels = pd.DataFrame(
        {f"label_{i}": np.arange(n_days, dtype=np.float32) + i * 0.01 for i in range(n_label)},
        index=dates,
    )
    return features, labels


def _make_multi_asset(
    symbols: list[str], n_days: int, n_feat: int = 3, n_label: int = 3
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    frames_f: list[pd.DataFrame] = []
    frames_y: list[pd.DataFrame] = []
    for k, sym in enumerate(symbols):
        base = (k + 1) * 1000
        feats = pd.DataFrame(
            {f"f{i}": base + np.arange(n_days, dtype=np.float32) + i * 10 for i in range(n_feat)},
            index=dates,
        )
        labs = pd.DataFrame(
            {f"y{i}": np.arange(n_days, dtype=np.float32) + i for i in range(n_label)},
            index=dates,
        )
        frames_f.append(feats.assign(symbol=sym).reset_index().set_index(["index", "symbol"]))
        frames_y.append(labs.assign(symbol=sym).reset_index().set_index(["index", "symbol"]))
    features = pd.concat(frames_f).rename_axis(index=["date", "symbol"]).sort_index()
    labels = pd.concat(frames_y).rename_axis(index=["date", "symbol"]).sort_index()
    return features, labels


class TestSequenceDatasetBuilder:
    def test_sequence_shape_single_series(self) -> None:
        features, labels = _make_single_series(n_days=40, n_feat=5, n_label=3)
        builder = SequenceDatasetBuilder(seq_len=30, stride=1)
        X, y = builder.build_sequences(features, labels)

        assert X.shape == (10, 30, 5)
        assert y.shape == (10, 3)
        assert builder.sample_meta_ is not None
        assert len(builder.sample_meta_) == 10
        assert builder.mask_ is not None
        assert builder.mask_.shape == (10,)

    def test_time_alignment_no_future_leakage(self) -> None:
        features, labels = _make_single_series(n_days=35, n_feat=1, n_label=3)
        builder = SequenceDatasetBuilder(seq_len=30, stride=1)
        X, y = builder.build_sequences(features, labels)

        # sample 0 predicts label at date index 30, using features [0..29]
        assert y[0, 0] == pytest.approx(labels.iloc[30, 0])
        assert X[0, 0, 0] == pytest.approx(features.iloc[0, 0])
        assert X[0, -1, 0] == pytest.approx(features.iloc[29, 0])
        # must not include feature at t=30 (future relative to label timestamp)
        assert X[0, -1, 0] != pytest.approx(features.iloc[30, 0])

    def test_nan_labels_preserved_and_masked(self) -> None:
        features, labels = _make_single_series(n_days=45, n_feat=2, n_label=3)
        # inject NaN at a label date that will produce a sample
        nan_date = labels.index[35]
        labels.loc[nan_date, "label_1"] = np.nan

        builder = SequenceDatasetBuilder(seq_len=30, stride=1)
        X, y = builder.build_sequences(features, labels)

        assert X.shape[0] == 15
        assert builder.sample_meta_ is not None

        row = builder.sample_meta_.index[builder.sample_meta_["date"] == nan_date][0]
        assert np.isnan(y[row, 1])
        assert builder.mask_ is not None
        assert bool(builder.mask_[row]) is False
        assert bool(builder.sample_meta_.loc[row, "mask"]) is False

    def test_walk_forward_split_non_overlapping_dates(self) -> None:
        features, labels = _make_multi_asset(["AAA", "BBB"], n_days=80, n_feat=2, n_label=3)
        builder = SequenceDatasetBuilder(seq_len=10, stride=1)
        X, y = builder.build_sequences(features, labels)
        splits = builder.split_walk_forward(X, y, train_ratio=0.7, valid_ratio=0.15)

        assert builder.sample_meta_ is not None
        dates = pd.to_datetime(builder.sample_meta_["date"])
        unique_dates = np.array(sorted(pd.unique(dates)))

        train_cut = max(1, int(len(unique_dates) * 0.7))
        valid_cut = max(train_cut, int(len(unique_dates) * (0.7 + 0.15)))
        train_dates = set(unique_dates[:train_cut].tolist())
        valid_dates = set(unique_dates[train_cut:valid_cut].tolist())
        test_dates = set(unique_dates[valid_cut:].tolist())

        assert train_dates.isdisjoint(valid_dates)
        assert train_dates.isdisjoint(test_dates)
        assert valid_dates.isdisjoint(test_dates)

        m_train = dates.isin(train_dates).to_numpy()
        m_valid = dates.isin(valid_dates).to_numpy()
        m_test = ~(m_train | m_valid)

        assert splits["train"]["X"].shape[0] == int(m_train.sum())
        assert splits["valid"]["X"].shape[0] == int(m_valid.sum())
        assert splits["test"]["X"].shape[0] == int(m_test.sum())

    def test_multi_stock_sequences_concatenated(self) -> None:
        features, labels = _make_multi_asset(["AAA", "BBB"], n_days=50, n_feat=3, n_label=3)
        builder = SequenceDatasetBuilder(seq_len=20, stride=2)
        X, y = builder.build_sequences(features, labels)

        # per symbol: samples = (n_days - seq_len) / stride rounded up
        per_symbol = (50 - 20 + (2 - 1)) // 2
        assert X.shape == (per_symbol * 2, 20, 3)
        assert y.shape == (per_symbol * 2, 3)

        assert builder.sample_meta_ is not None
        counts = builder.sample_meta_["symbol"].value_counts().to_dict()
        assert counts["AAA"] == per_symbol
        assert counts["BBB"] == per_symbol

        # ensure sequences never mix symbols (AAA features are around 1000+, BBB around 2000+)
        sym0 = builder.sample_meta_.iloc[0]["symbol"]
        if sym0 == "AAA":
            assert float(X[0, 0, 0]) < 2000.0
        else:
            assert float(X[0, 0, 0]) >= 2000.0

    def test_accept_date_symbol_columns(self) -> None:
        features, labels = _make_multi_asset(["AAA"], n_days=40, n_feat=2, n_label=3)
        # convert to columns
        f2 = features.reset_index()
        y2 = labels.reset_index()
        builder = SequenceDatasetBuilder(seq_len=10, stride=1)
        X, y = builder.build_sequences(f2, y2)
        assert X.shape[1:] == (10, 2)
        assert y.shape[1] == 3

    def test_accept_multiindex_reorder_levels(self) -> None:
        features, labels = _make_multi_asset(["AAA"], n_days=35, n_feat=2, n_label=3)
        # swap to (symbol, date) order to hit reorder_levels path
        f2 = features.copy()
        y2 = labels.copy()
        f2.index = f2.index.reorder_levels(["symbol", "date"])
        y2.index = y2.index.reorder_levels(["symbol", "date"])
        f2.index = f2.index.set_names(["symbol", "date"])
        y2.index = y2.index.set_names(["symbol", "date"])

        builder = SequenceDatasetBuilder(seq_len=10, stride=1)
        X, y = builder.build_sequences(f2, y2)
        assert X.shape[1:] == (10, 2)
        assert y.shape[1] == 3
        assert builder.sample_meta_ is not None
        assert set(builder.sample_meta_["symbol"]) == {"AAA"}

    def test_empty_and_boundary_cases(self) -> None:
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        features = pd.DataFrame({"f0": np.arange(10, dtype=np.float32)}, index=dates)
        labels = pd.DataFrame({"y0": np.arange(10, dtype=np.float32)}, index=dates)

        builder = SequenceDatasetBuilder(seq_len=10, stride=1)
        X, y = builder.build_sequences(features, labels)
        assert X.shape == (0, 10, 1)
        assert y.shape == (0, 1)

        empty_features = pd.DataFrame({"f0": pd.Series(dtype=float)}, index=pd.DatetimeIndex([]))
        empty_labels = pd.DataFrame({"y0": pd.Series(dtype=float)}, index=pd.DatetimeIndex([]))
        builder = SequenceDatasetBuilder(seq_len=5, stride=1)
        X, y = builder.build_sequences(empty_features, empty_labels)
        assert X.shape == (0, 5, 1)
        assert y.shape == (0, 1)

    def test_split_walk_forward_fallback_by_count(self) -> None:
        builder = SequenceDatasetBuilder(seq_len=5, stride=1)
        X = np.zeros((10, 5, 2), dtype=np.float32)
        y = np.zeros((10, 3), dtype=np.float32)
        splits = builder.split_walk_forward(X, y, train_ratio=0.6, valid_ratio=0.2)
        assert splits["train"]["X"].shape[0] == 6
        assert splits["valid"]["X"].shape[0] == 2
        assert splits["test"]["X"].shape[0] == 2

        empty_X = np.zeros((0, 5, 2), dtype=np.float32)
        empty_y = np.zeros((0, 3), dtype=np.float32)
        empty_splits = builder.split_walk_forward(empty_X, empty_y)
        assert empty_splits["train"]["X"].shape[0] == 0
        assert empty_splits["valid"]["X"].shape[0] == 0
        assert empty_splits["test"]["X"].shape[0] == 0

    def test_invalid_inputs(self) -> None:
        with pytest.raises(ValueError):
            SequenceDatasetBuilder(seq_len=0, stride=1)
        with pytest.raises(ValueError):
            SequenceDatasetBuilder(seq_len=10, stride=0)

        builder = SequenceDatasetBuilder(seq_len=5, stride=1)
        with pytest.raises(TypeError):
            builder.build_sequences(features=np.zeros((3, 2)), labels=pd.DataFrame({"y": [1, 2, 3]}))  # type: ignore[arg-type]

        # mismatched index type
        features, labels = _make_single_series(n_days=20, n_feat=2, n_label=1)
        mi = pd.MultiIndex.from_product([labels.index, ["X"]], names=["date", "symbol"])
        labels2 = pd.DataFrame({"label_0": labels["label_0"].to_numpy()}, index=mi)
        with pytest.raises(ValueError):
            builder.build_sequences(features, labels2)

        with pytest.raises(ValueError):
            builder.split_walk_forward(np.zeros((3, 2), dtype=np.float32), np.zeros((3, 1), dtype=np.float32))
