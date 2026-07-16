"""防伪门禁 Sanity Check — shim；实现在 ``ashare_infra.guard.sanity``。"""

from __future__ import annotations

from ashare_infra.guard.sanity import (
    compute_baseline_ic,
    lag1_test,
    neutralization_test,
    random_label_test,
    run_all_checks,
    shuffle_test,
    time_reverse_test,
)

__all__ = [
    "compute_baseline_ic",
    "lag1_test",
    "neutralization_test",
    "random_label_test",
    "run_all_checks",
    "shuffle_test",
    "time_reverse_test",
]
