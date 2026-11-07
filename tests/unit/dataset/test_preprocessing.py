from __future__ import annotations

import numpy as np
import pytest

from ashare_lab.dataset.preprocessing import (
    FeatureQualityError,
    RobustScaleConfig,
    RollingRobustScaler,
    screen_feature_rows,
)


def test_screen_feature_rows_drops_any_nonfinite_sequence() -> None:
    x = np.array(
        [
            [[1.0, 2.0], [3.0, 4.0]],
            [[1.0, np.nan], [3.0, 4.0]],
            [[1.0, 2.0], [np.inf, 4.0]],
        ],
        dtype=np.float32,
    )

    keep, report = screen_feature_rows(x, ["ret", "volume"])

    assert keep.tolist() == [True, False, False]
    assert report.total_rows == 3
    assert report.valid_rows == 1
    assert report.dropped_rows == 2
    assert report.nonfinite_values == 2
    assert report.nonfinite_by_feature == {"ret": 1, "volume": 1}


def test_robust_scaler_uses_train_window_only_and_clips_oos_values() -> None:
    train = np.array(
        [
            [[0.0, 10.0], [1.0, 11.0]],
            [[2.0, 12.0], [3.0, 13.0]],
        ],
        dtype=np.float32,
    )
    oos = np.array([[[1000.0, -1000.0]]], dtype=np.float32)
    scaler = RollingRobustScaler(
        ["small", "large"],
        RobustScaleConfig(lower_clip_quantile=0.0, upper_clip_quantile=1.0),
    )

    scaled_train = scaler.fit_transform(train)
    scaled_oos = scaler.transform(oos)
    state = scaler.to_dict()

    assert np.isfinite(scaled_train).all()
    assert np.isfinite(scaled_oos).all()
    assert state["fit_rows"] == 2
    # The OOS point is clipped by train-only [0, 3] and [10, 13] bounds.
    assert scaled_oos[0, 0, 0] == pytest.approx(scaled_train.max(axis=(0, 1))[0])
    assert scaled_oos[0, 0, 1] == pytest.approx(scaled_train.min(axis=(0, 1))[1])

    restored = RollingRobustScaler.from_dict(state)
    np.testing.assert_allclose(restored.transform(oos), scaled_oos)


def test_robust_scaler_rejects_nonfinite_fit_or_transform_input() -> None:
    clean = np.ones((2, 2, 1), dtype=np.float32)
    bad = clean.copy()
    bad[0, 0, 0] = np.nan
    scaler = RollingRobustScaler(["feature"])

    with pytest.raises(FeatureQualityError, match="screen rows before fit"):
        scaler.fit(bad)

    scaler.fit(clean)
    with pytest.raises(FeatureQualityError, match="screen rows first"):
        scaler.transform(bad)


@pytest.mark.parametrize("min_scale", [float("nan"), float("inf"), float("-inf")])
def test_robust_scaler_config_rejects_nonfinite_min_scale(min_scale: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        RobustScaleConfig(min_scale=min_scale)
