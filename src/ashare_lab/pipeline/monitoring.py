"""Compatibility wrapper for monitoring utilities (Task 3.4).

The canonical implementation lives in the package directory
`ashare_lab.pipeline.monitoring` (to support pytest-cov source-path usage like
`--cov=src/ashare_lab/pipeline/monitoring`).
"""

from __future__ import annotations

from .monitoring import MonitoringMetrics, PerformanceMonitor, RetrainDecision

__all__ = ["MonitoringMetrics", "PerformanceMonitor", "RetrainDecision"]

