"""Recommendation module.

This package provides the core recommendation engine that ranks A-share stocks for multiple
forward horizons (3d/5d/10d) and utilities to export results to JSON/CSV/Markdown.
"""

from __future__ import annotations

from .engine import Recommendation, RecommendationEngine, save_as_csv, save_as_json, save_as_markdown

__all__ = [
    "Recommendation",
    "RecommendationEngine",
    "save_as_csv",
    "save_as_json",
    "save_as_markdown",
]

