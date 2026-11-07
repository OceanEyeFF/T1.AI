"""Deprecated compatibility namespace for the retired static training path.

The supported training entrypoints are the Feature Contract-aware rolling LSTM
and XGBoost scripts.  This namespace intentionally does not emulate the old
static/incremental trainer: doing so would bypass Contract and checkpoint
compatibility gates.
"""

from __future__ import annotations

import warnings
from typing import Any

_MESSAGE = (
    "ashare_lab.training is retired. Use the Feature Contract-aware rolling training "
    "entrypoints; static/incremental training cannot produce compatible artifacts."
)

warnings.warn(_MESSAGE, DeprecationWarning, stacklevel=2)


def _retired(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError(_MESSAGE)


# Preserve the historical public names long enough for callers to receive an
# explicit migration failure instead of a ModuleNotFoundError.
IncrementalTrainConfig = _retired
IncrementalTrainer = _retired
TrainingGate = _retired
count_labeled_samples = _retired

__all__ = [
    "IncrementalTrainConfig",
    "IncrementalTrainer",
    "TrainingGate",
    "count_labeled_samples",
]
