from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_lab.dataset import load_sequence_parquet


def _legacy_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label_3d": [0.01, 0.02],
            "label_5d": [0.02, 0.03],
            "label_10d": [0.03, 0.04],
            "return_1d_t0": [0.1, 0.2],
            "return_1d_t1": [0.2, 0.3],
        }
    )


def test_legacy_loader_remains_importable_but_is_explicitly_deprecated(tmp_path) -> None:
    path = tmp_path / "legacy.parquet"
    _legacy_frame().to_parquet(path, index=False)

    with pytest.deprecated_call(match="load_sequence_parquet"):
        X, y, info = load_sequence_parquet(path)

    assert tuple(X.shape) == (2, 2, 1)
    assert tuple(y.shape) == (2, 3)
    assert info["deprecated"] is True


def test_legacy_loader_refuses_nonfinite_features_instead_of_zero_imputing(tmp_path) -> None:
    path = tmp_path / "nonfinite.parquet"
    frame = _legacy_frame()
    frame.loc[0, "return_1d_t1"] = np.nan
    frame.to_parquet(path, index=False)

    with pytest.deprecated_call(match="load_sequence_parquet"), pytest.raises(ValueError, match="non-finite"):
        load_sequence_parquet(path)
