"""Leakage-safe feature screening and robust scaling for rolling research.

The preprocessor has two deliberately separate jobs:

* reject sample rows whose *input* sequence contains NaN or +/-inf;
* fit clipping and scaling statistics on a training window only.

Validation and OOS windows must call :meth:`transform` on the fitted object;
they must never call :meth:`fit` themselves.  This keeps distributional
information from later windows out of the training path.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


class FeatureQualityError(ValueError):
    """Raised when an array cannot safely enter model training or scoring."""


@dataclass(frozen=True)
class FeatureQualityReport:
    """Non-finite feature summary at the sample-sequence grain."""

    total_rows: int
    valid_rows: int
    dropped_rows: int
    feature_count: int
    total_feature_values: int
    nonfinite_values: int
    nonfinite_by_feature: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RobustScaleConfig:
    """Training-only robust scaling policy for heavy-tailed market features."""

    lower_clip_quantile: float = 0.005
    upper_clip_quantile: float = 0.995
    min_scale: float = 1e-6

    def __post_init__(self) -> None:
        if not (0.0 <= self.lower_clip_quantile < self.upper_clip_quantile <= 1.0):
            raise ValueError("clip quantiles must satisfy 0 <= lower < upper <= 1")
        if not math.isfinite(self.min_scale) or self.min_scale <= 0.0:
            raise ValueError("min_scale must be finite and > 0")


def _as_sequence_array(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 3:
        raise FeatureQualityError(
            f"expected feature array [rows, seq_len, features], got shape={array.shape}"
        )
    if array.shape[0] == 0 or array.shape[1] == 0 or array.shape[2] == 0:
        raise FeatureQualityError(f"feature array must be non-empty, got shape={array.shape}")
    return array


def screen_feature_rows(
    values: np.ndarray,
    feature_names: Sequence[str],
) -> tuple[np.ndarray, FeatureQualityReport]:
    """Return a keep-mask plus a lossless report of non-finite feature values.

    A sample is valid only when every timestep and every feature is finite.
    Labels are intentionally outside this check: label availability is governed
    by the rolling maturity gate and per-head training policy.
    """

    array = _as_sequence_array(values)
    names = tuple(str(name) for name in feature_names)
    if len(names) != array.shape[2]:
        raise FeatureQualityError(
            f"feature name count={len(names)} does not match array features={array.shape[2]}"
        )
    if len(set(names)) != len(names):
        raise FeatureQualityError("feature names must be unique")

    finite = np.isfinite(array)
    keep_mask = finite.all(axis=(1, 2))
    nonfinite_by_feature = {
        name: int((~finite[:, :, idx]).sum()) for idx, name in enumerate(names)
    }
    report = FeatureQualityReport(
        total_rows=int(array.shape[0]),
        valid_rows=int(keep_mask.sum()),
        dropped_rows=int((~keep_mask).sum()),
        feature_count=int(array.shape[2]),
        total_feature_values=int(array.size),
        nonfinite_values=int((~finite).sum()),
        nonfinite_by_feature=nonfinite_by_feature,
    )
    return keep_mask, report


class RollingRobustScaler:
    """Per-feature clipping and robust scaling fitted only on a train window."""

    STATE_VERSION = 1

    def __init__(
        self,
        feature_names: Sequence[str],
        config: RobustScaleConfig | None = None,
    ) -> None:
        names = tuple(str(name) for name in feature_names)
        if not names:
            raise ValueError("feature_names must not be empty")
        if len(set(names)) != len(names):
            raise ValueError("feature_names must be unique")
        self.feature_names = names
        self.config = config or RobustScaleConfig()
        self._lower_clip: np.ndarray | None = None
        self._upper_clip: np.ndarray | None = None
        self._center: np.ndarray | None = None
        self._scale: np.ndarray | None = None
        self._fallback_scale: np.ndarray | None = None
        self._fit_rows: int | None = None

    @property
    def fitted(self) -> bool:
        return self._scale is not None

    def fit(self, values: np.ndarray) -> RollingRobustScaler:
        array = _as_sequence_array(values)
        if array.shape[2] != len(self.feature_names):
            raise FeatureQualityError(
                f"array features={array.shape[2]} does not match names={len(self.feature_names)}"
            )
        if not np.isfinite(array).all():
            raise FeatureQualityError("fit input contains NaN or +/-inf; screen rows before fit")

        flat = array.reshape(-1, array.shape[2])
        lower = np.quantile(flat, self.config.lower_clip_quantile, axis=0)
        upper = np.quantile(flat, self.config.upper_clip_quantile, axis=0)
        clipped = np.clip(flat, lower, upper)
        center = np.median(clipped, axis=0)
        q25 = np.quantile(clipped, 0.25, axis=0)
        q75 = np.quantile(clipped, 0.75, axis=0)
        robust_scale = (q75 - q25) / 1.349
        std_scale = np.std(clipped, axis=0)
        fallback = robust_scale < self.config.min_scale
        scale = np.where(fallback, std_scale, robust_scale)
        scale = np.where(scale < self.config.min_scale, 1.0, scale)

        self._lower_clip = lower.astype(np.float64, copy=False)
        self._upper_clip = upper.astype(np.float64, copy=False)
        self._center = center.astype(np.float64, copy=False)
        self._scale = scale.astype(np.float64, copy=False)
        self._fallback_scale = fallback.astype(bool, copy=False)
        self._fit_rows = int(array.shape[0])
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        array = _as_sequence_array(values)
        if array.shape[2] != len(self.feature_names):
            raise FeatureQualityError(
                f"array features={array.shape[2]} does not match names={len(self.feature_names)}"
            )
        if not np.isfinite(array).all():
            raise FeatureQualityError("transform input contains NaN or +/-inf; screen rows first")
        if not self.fitted:
            raise FeatureQualityError("scaler is not fitted")

        assert self._lower_clip is not None
        assert self._upper_clip is not None
        assert self._center is not None
        assert self._scale is not None
        clipped = np.clip(array, self._lower_clip, self._upper_clip)
        scaled = (clipped - self._center) / self._scale
        if not np.isfinite(scaled).all():  # defensive contract; should be impossible after checks above
            raise FeatureQualityError("scaled output contains NaN or +/-inf")
        return scaled.astype(np.float32, copy=False)

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.fit(values).transform(values)

    def to_dict(self) -> dict[str, Any]:
        if not self.fitted:
            raise FeatureQualityError("cannot serialize an unfitted scaler")
        assert self._lower_clip is not None
        assert self._upper_clip is not None
        assert self._center is not None
        assert self._scale is not None
        assert self._fallback_scale is not None
        return {
            "schema_version": self.STATE_VERSION,
            "method": "train_window_robust_clip_median_iqr",
            "feature_names": list(self.feature_names),
            "config": asdict(self.config),
            "fit_rows": self._fit_rows,
            "feature_stats": {
                name: {
                    "lower_clip": float(self._lower_clip[idx]),
                    "upper_clip": float(self._upper_clip[idx]),
                    "center": float(self._center[idx]),
                    "scale": float(self._scale[idx]),
                    "used_std_fallback": bool(self._fallback_scale[idx]),
                }
                for idx, name in enumerate(self.feature_names)
            },
        }

    @classmethod
    def from_dict(cls, state: dict[str, Any]) -> RollingRobustScaler:
        """Restore a serialized train-window scaler for strict inference use.

        Checkpoint consumers must never re-fit a scaler.  This parser rejects
        incomplete, non-finite, or feature-order-mismatched state instead of
        guessing a fallback.
        """

        if not isinstance(state, dict):
            raise FeatureQualityError("scaler state must be a mapping")
        if state.get("schema_version") != cls.STATE_VERSION:
            raise FeatureQualityError(
                f"unsupported scaler schema_version: {state.get('schema_version')!r}"
            )
        if state.get("method") != "train_window_robust_clip_median_iqr":
            raise FeatureQualityError(f"unsupported scaler method: {state.get('method')!r}")
        raw_names = state.get("feature_names")
        if not isinstance(raw_names, list) or not raw_names:
            raise FeatureQualityError("scaler state feature_names must be a non-empty list")
        names = tuple(str(name) for name in raw_names)
        if len(set(names)) != len(names) or any(not name for name in names):
            raise FeatureQualityError("scaler state feature_names must be unique non-empty strings")
        raw_config = state.get("config")
        if not isinstance(raw_config, dict):
            raise FeatureQualityError("scaler state config must be a mapping")
        try:
            config = RobustScaleConfig(
                lower_clip_quantile=float(raw_config["lower_clip_quantile"]),
                upper_clip_quantile=float(raw_config["upper_clip_quantile"]),
                min_scale=float(raw_config["min_scale"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FeatureQualityError("invalid scaler state config") from exc
        raw_fit_rows = state.get("fit_rows")
        if isinstance(raw_fit_rows, bool) or not isinstance(raw_fit_rows, int) or raw_fit_rows <= 0:
            raise FeatureQualityError("scaler state fit_rows must be a positive integer")
        raw_stats = state.get("feature_stats")
        if not isinstance(raw_stats, dict) or set(raw_stats) != set(names):
            raise FeatureQualityError("scaler state feature_stats must match feature_names exactly")

        lower: list[float] = []
        upper: list[float] = []
        center: list[float] = []
        scale: list[float] = []
        fallback: list[bool] = []
        required_fields = {"lower_clip", "upper_clip", "center", "scale", "used_std_fallback"}
        for name in names:
            raw_feature = raw_stats[name]
            if not isinstance(raw_feature, dict) or set(raw_feature) != required_fields:
                raise FeatureQualityError(f"invalid scaler statistics for feature {name!r}")
            try:
                lo = float(raw_feature["lower_clip"])
                hi = float(raw_feature["upper_clip"])
                mid = float(raw_feature["center"])
                width = float(raw_feature["scale"])
            except (TypeError, ValueError) as exc:
                raise FeatureQualityError(f"non-numeric scaler statistics for feature {name!r}") from exc
            if not all(math.isfinite(value) for value in (lo, hi, mid, width)):
                raise FeatureQualityError(f"non-finite scaler statistics for feature {name!r}")
            if lo > hi or width <= 0.0:
                raise FeatureQualityError(f"invalid scaler bounds or scale for feature {name!r}")
            if not isinstance(raw_feature["used_std_fallback"], bool):
                raise FeatureQualityError(f"invalid fallback flag for feature {name!r}")
            lower.append(lo)
            upper.append(hi)
            center.append(mid)
            scale.append(width)
            fallback.append(raw_feature["used_std_fallback"])

        scaler = cls(names, config=config)
        scaler._lower_clip = np.asarray(lower, dtype=np.float64)
        scaler._upper_clip = np.asarray(upper, dtype=np.float64)
        scaler._center = np.asarray(center, dtype=np.float64)
        scaler._scale = np.asarray(scale, dtype=np.float64)
        scaler._fallback_scale = np.asarray(fallback, dtype=bool)
        scaler._fit_rows = int(raw_fit_rows)
        return scaler
