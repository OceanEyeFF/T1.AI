"""Deprecated import path for retired incremental MTL fine-tuning."""

from __future__ import annotations

from ashare_lab.training import (
    IncrementalTrainConfig,
    IncrementalTrainer,
    TrainingGate,
    count_labeled_samples,
)

__all__ = [
    "IncrementalTrainConfig",
    "IncrementalTrainer",
    "TrainingGate",
    "count_labeled_samples",
]
