"""Contract: R4 approved caps are enforced on the TuShare fetch entrypoints."""

from __future__ import annotations

import ast
from pathlib import Path

from ashare_infra.data.tushare_rate_limit import (
    TushareRateLimiter,
    get_tushare_rate_limiter,
    reset_tushare_rate_limiter,
)
from ashare_infra.lake.r4_contract import r4_approved_daily_per_api, r4_approved_rpm

REPO = Path(__file__).resolve().parents[3]
TUSHARE_SOURCE = REPO / "src/ashare_infra/data/tushare_source.py"


def test_tushare_source_imports_and_calls_acquire() -> None:
    tree = ast.parse(TUSHARE_SOURCE.read_text(encoding="utf-8"))
    imported = False
    acquire_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").endswith("tushare_rate_limit"):
                for alias in node.names:
                    if alias.name == "acquire_tushare_call":
                        imported = True
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "acquire_tushare_call":
                acquire_calls += 1
    assert imported, "tushare_source must import acquire_tushare_call"
    # daily, adj_factor (qfq path), daily_basic, moneyflow, adj_factor dedicated
    assert acquire_calls >= 4, f"expected acquire wired into fetch paths, got {acquire_calls}"


def test_process_limiter_matches_approved_caps() -> None:
    reset_tushare_rate_limiter()
    lim = get_tushare_rate_limiter()
    assert isinstance(lim, TushareRateLimiter)
    assert lim.rpm == r4_approved_rpm() == 180
    assert lim.daily_per_api == r4_approved_daily_per_api() == 80000
    reset_tushare_rate_limiter()
