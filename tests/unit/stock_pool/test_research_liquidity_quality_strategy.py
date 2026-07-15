"""Unit tests for research_liquidity_quality strategy."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ashare_lab.stock_pool.base import PoolCandidate, StockPoolStrategy
from ashare_lab.stock_pool.research_liquidity_quality.strategy import (
    ResearchLiquidityQualityStrategy,
)


def _write_symbol_cache(
    root: Path,
    dataset: str,
    ts_code: str,
    df: pd.DataFrame,
) -> None:
    year_dir = root / dataset / ts_code / "year=2024"
    year_dir.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if "date" not in out.columns:
        out = out.reset_index().rename(columns={"index": "date"})
    out.to_parquet(year_dir / "part.parquet", index=False)


def _synth_bars(periods: int = 150, amount_scale: float = 1.5e6) -> pd.DataFrame:
    # amount_scale: TuShare 千元；1.5e6 千元 ≈ 15 亿元日均
    dates = pd.bdate_range("2024-01-02", periods=periods)
    close = np.linspace(10.0, 20.0, periods)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close - 0.1,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": np.full(periods, 1_000_000.0),
            "amount": np.full(periods, amount_scale),
        }
    )


def _synth_basic(periods: int = 150) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    return pd.DataFrame(
        {
            "date": dates,
            "circ_mv": np.full(periods, 2.0e6),
            "total_mv": np.full(periods, 3.0e6),
            "turnover_rate": np.full(periods, 2.0),
        }
    )


@pytest.fixture()
def cache_root(tmp_path: Path) -> Path:
    root = tmp_path / "cache"
    for sym, amt in (("600519.SH", 2.0e6), ("000001.SZ", 1.2e6), ("300750.SZ", 1.8e6)):
        _write_symbol_cache(root, "tushare_qfq", sym, _synth_bars(amount_scale=amt))
        _write_symbol_cache(root, "tushare_daily_basic", sym, _synth_basic())
        _write_symbol_cache(
            root,
            "tushare_moneyflow",
            sym,
            pd.DataFrame(
                {
                    "date": pd.bdate_range("2024-01-02", periods=150),
                    "net_mf_amount": np.zeros(150),
                }
            ),
        )
    # index for sync dimension（千元单位）
    _write_symbol_cache(root, "tushare_qfq", "510300.SH", _synth_bars(amount_scale=5.0e6))
    return root


def test_strategy_implements_base() -> None:
    assert issubclass(ResearchLiquidityQualityStrategy, StockPoolStrategy)


def test_select_returns_pool_candidate(cache_root: Path) -> None:
    s = ResearchLiquidityQualityStrategy(data_root=cache_root, score_threshold=0.0)
    result = s.select(["600519", "000001", "300750"])
    assert isinstance(result, PoolCandidate)
    assert "600519" in result.symbols or "000001" in result.symbols
    # ChiNext / 300 prefix hard-filtered
    assert "300750" not in result.symbols
    assert result.metadata["strategy"] == "research_liquidity_quality"
    assert result.metadata["total_selected"] <= result.metadata["hard_cap"]


def test_select_idempotent(cache_root: Path) -> None:
    s = ResearchLiquidityQualityStrategy(data_root=cache_root, score_threshold=0.0)
    a = s.select(["600519", "000001"])
    b = s.select(["600519", "000001"])
    assert a.symbols == b.symbols


def test_hard_cap_enforced(cache_root: Path) -> None:
    s = ResearchLiquidityQualityStrategy(
        data_root=cache_root,
        score_threshold=0.0,
        soft_target_size=1,
        hard_cap=1,
    )
    result = s.select(["600519", "000001"])
    assert len(result.symbols) <= 1


def test_amount_floor_rejects(cache_root: Path, tmp_path: Path) -> None:
    # rebuild tiny-amount symbol only
    root = tmp_path / "tiny"
    # 1e4 千元 ≈ 0.1 亿元 < min_avg_amount_yi=0.5 → H5
    _write_symbol_cache(root, "tushare_qfq", "600000.SH", _synth_bars(amount_scale=1e4))
    _write_symbol_cache(root, "tushare_daily_basic", "600000.SH", _synth_basic())
    s = ResearchLiquidityQualityStrategy(data_root=root, score_threshold=0.0)
    result = s.select(["600000"])
    assert result.symbols == []
    assert result.metadata["reject_count"] >= 1
    assert result.metadata.get("reject_reason_counts", {}).get("H5_amount_floor", 0) >= 1
