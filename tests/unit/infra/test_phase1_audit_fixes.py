"""Regression tests for Phase 1 audit findings (H1/H2/M1-M5, L1/L3/L4).

Audit ref: subagent audit 2026-07-18; all no-network (mocked fetch).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import ashare_infra.data.tushare_source as ts
from ashare_infra.guard.metrics import calculate_daily_cs_ic, summarize_daily_cs
from ashare_infra.guard.scope import DataScope, MissingBarPolicy
from ashare_infra.guard.temporal import truncate_as_of
from ashare_infra.lake import DataLake
from ashare_infra.sim.broker import MissingBarError, PaperBroker, SimConfig
from ashare_infra.sim.fill_model import match_limit_daily_ohlc
from ashare_infra.sim.types import DailyBar, LimitOrder


def _bars_frame(start: str, end: str) -> pd.DataFrame:
    idx = pd.bdate_range(start, end)
    return pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0, "amount": 1.0},
        index=idx,
    )


@pytest.fixture()
def mock_tushare(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    def fake_fetch(req):
        calls.append((req.start_date, req.end_date))
        return _bars_frame(req.start_date, req.end_date)

    monkeypatch.setattr(ts, "fetch_tushare_daily_bars", fake_fetch)
    monkeypatch.setattr(ts, "_retry_with_backoff", lambda fn, retries=3, base_delay=0.5: fn())
    return calls


# --- H1: refresh must not destroy cached rows outside the requested range ---


def test_h1_refresh_subrange_preserves_cache(tmp_path: Path, mock_tushare) -> None:
    req_full = ts.TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240102", end_date="20250131", adjust="raw"
    )
    df_full = ts.load_or_fetch_daily_bars(req_full, cache_dir=tmp_path)
    n_full = len(df_full)
    assert n_full > 200

    # refresh a small sub-range
    req_sub = ts.TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240102", end_date="20240331", adjust="raw"
    )
    ts.load_or_fetch_daily_bars(req_sub, cache_dir=tmp_path, refresh=True)

    # middle + tail must still be served from cache without holes
    mock_tushare.clear()
    req_mid = ts.TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240601", end_date="20240630", adjust="raw"
    )
    df_mid = ts.load_or_fetch_daily_bars(req_mid, cache_dir=tmp_path)
    assert not df_mid.empty, "refresh sub-range must not punch holes in cached data"
    assert mock_tushare == [], "middle range should come from cache, not refetch"

    df_full_again = ts.load_or_fetch_daily_bars(req_full, cache_dir=tmp_path)
    assert len(df_full_again) == n_full


# --- H2: adjusted (qfq) incremental fetch must not mix adjustment bases ---


def test_h2_qfq_incremental_refetches_full_span(tmp_path: Path, mock_tushare) -> None:
    req1 = ts.TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240102", end_date="20240331", adjust="qfq"
    )
    ts.load_or_fetch_daily_bars(req1, cache_dir=tmp_path)
    assert mock_tushare == [("20240102", "20240331")]

    # extend the window: must refetch the WHOLE span (one base), not just the tail
    mock_tushare.clear()
    req2 = ts.TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240102", end_date="20240630", adjust="qfq"
    )
    ts.load_or_fetch_daily_bars(req2, cache_dir=tmp_path)
    assert mock_tushare == [("20240102", "20240630")]

    # raw mode keeps incremental tail-only fetch
    mock_tushare.clear()
    req_raw1 = ts.TushareDailyBarsRequest(
        symbol="600001.SH", start_date="20240102", end_date="20240331", adjust="raw"
    )
    ts.load_or_fetch_daily_bars(req_raw1, cache_dir=tmp_path)
    mock_tushare.clear()
    req_raw2 = ts.TushareDailyBarsRequest(
        symbol="600001.SH", start_date="20240102", end_date="20240630", adjust="raw"
    )
    ts.load_or_fetch_daily_bars(req_raw2, cache_dir=tmp_path)
    assert len(mock_tushare) == 1
    # tail-only：起点在已缓存末日（bdate 3/29）之后，而非整段重取
    assert mock_tushare[0][0] >= "20240330"
    assert mock_tushare[0][1] == "20240630"


# --- M1: empty cache + empty upstream must return empty frame, not raise ---


def test_m1_empty_fetch_returns_empty_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ts, "fetch_tushare_daily_bars", lambda req: pd.DataFrame(columns=ts.SUPPORTED_FIELDS)
    )
    monkeypatch.setattr(ts, "_retry_with_backoff", lambda fn, retries=3, base_delay=0.5: fn())

    req = ts.TushareDailyBarsRequest(
        symbol="600000.SH", start_date="20240102", end_date="20240131", adjust="raw"
    )
    df = ts.load_or_fetch_daily_bars(req, cache_dir=tmp_path)
    assert df.empty


def test_m1_odp_empty_fetch_returns_empty_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ashare_infra.data.odp_source as odp

    monkeypatch.setattr(
        odp,
        "fetch_odp_historical_bars",
        lambda req: pd.DataFrame(columns=list(odp.SUPPORTED_FIELDS)),
    )
    req = odp.ODPDailyBarsRequest(symbol="600000", start_date="20240102", end_date="20240131")
    df = odp.load_or_fetch_daily_bars(req, cache_dir=tmp_path)
    assert df.empty


# --- M2: truncate_as_of must not leak future rows on unsorted index ---


def test_m2_truncate_as_of_unsorted_index() -> None:
    idx = pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02"])
    df = pd.DataFrame({"close": [3.0, 1.0, 2.0]}, index=idx)
    out = truncate_as_of(df, date(2024, 1, 2), inclusive=True)
    assert set(out.index.date) == {date(2024, 1, 1), date(2024, 1, 2)}


# --- M3: ts_code style scope symbols must still get lifecycle attached ---


def test_m3_ts_code_scope_gets_lifecycle(tmp_path: Path) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir(parents=True)
    pd.DataFrame(
        {"symbol": ["600000"], "list_date": ["2024-01-08"], "delist_date": [""]}
    ).to_csv(meta_dir / "stock_basic.csv", index=False)

    lake = DataLake(cache_dir=tmp_path)
    scope = DataScope(
        symbols=frozenset({"600000.SH"}),
        window_start=date(2024, 1, 2),
        window_end=date(2024, 1, 31),
    )
    scoped = lake.with_stock_basic_meta(scope)
    assert "600000.SH" in scoped.symbol_meta
    assert not scoped.is_tradable("600000.SH", date(2024, 1, 5))
    assert scoped.is_tradable("600000.SH", date(2024, 1, 8))


def test_l4_scope_override_not_overwritten(tmp_path: Path) -> None:
    from ashare_infra.guard.scope import MetaSource, SymbolLifecycle

    meta_dir = tmp_path / "meta"
    meta_dir.mkdir(parents=True)
    pd.DataFrame(
        {"symbol": ["600000"], "list_date": ["2020-01-01"], "delist_date": [""]}
    ).to_csv(meta_dir / "stock_basic.csv", index=False)

    override = SymbolLifecycle(
        list_date=date(2024, 6, 1),
        source=MetaSource(kind="scope_override", evidence_ref="manual"),
    )
    scope = DataScope(
        symbols=frozenset({"600000"}),
        window_start=date(2024, 1, 2),
        window_end=date(2024, 12, 31),
        symbol_meta={"600000": override},
    )
    lake = DataLake(cache_dir=tmp_path)
    scoped = lake.with_stock_basic_meta(scope, fill_missing_only=False)
    assert scoped.symbol_meta["600000"].list_date == date(2024, 6, 1)
    assert scoped.symbol_meta["600000"].source.kind == "scope_override"


# --- M4: MissingBarPolicy wired into PaperBroker ---


def _order(symbol: str = "600000") -> LimitOrder:
    return LimitOrder(symbol=symbol, side="BUY", shares=100, limit_price=10.0)


def test_m4_missing_bar_reject_default() -> None:
    broker = PaperBroker(SimConfig())
    broker.submit([_order()])
    result = broker.match_day(date(2024, 1, 5), bars={})
    assert [r.reason for r in result.rejects] == ["missing_bar"]


def test_m4_missing_bar_skip() -> None:
    broker = PaperBroker(SimConfig(), missing_bar_policy=MissingBarPolicy.SKIP)
    broker.submit([_order()])
    result = broker.match_day(date(2024, 1, 5), bars={})
    assert result.rejects == []
    assert result.fills == []


def test_m4_missing_bar_raise() -> None:
    broker = PaperBroker(SimConfig(), missing_bar_policy=MissingBarPolicy.RAISE)
    broker.submit([_order()])
    with pytest.raises(MissingBarError):
        broker.match_day(date(2024, 1, 5), bars={})


def test_m4_session_syncs_policy_from_scope() -> None:
    from ashare_infra.sim.session import TestSession

    session = TestSession.for_ic({"600000"}, date(2024, 1, 2), date(2024, 1, 15))
    assert session.broker.missing_bar_policy is MissingBarPolicy.SKIP

    session2 = TestSession.for_sim({"600000"}, date(2024, 1, 2), date(2024, 1, 15))
    assert session2.broker.missing_bar_policy is MissingBarPolicy.REJECT


# --- M5: degenerate days must be NaN, not IC=0.0 counted as valid ---


def test_m5_single_symbol_day_is_nan() -> None:
    idx = pd.MultiIndex.from_tuples(
        [
            ("2024-01-05", "A"),
            ("2024-01-05", "B"),
            ("2024-01-05", "C"),
            ("2024-01-08", "A"),  # single-symbol day
        ],
        names=["date", "symbol"],
    )
    preds = pd.Series([0.1, 0.2, 0.3, 0.5], index=idx)
    labels = pd.Series([0.1, 0.2, 0.3, 0.5], index=idx)  # perfect signal

    daily = calculate_daily_cs_ic(preds, labels)
    assert np.isnan(daily.loc["2024-01-08"])
    stats = summarize_daily_cs(daily)
    assert stats["n_days"] == 1
    assert stats["mean_ic"] == pytest.approx(1.0)


def test_m5_constant_cross_section_is_nan() -> None:
    idx = pd.MultiIndex.from_tuples(
        [("2024-01-05", "A"), ("2024-01-05", "B"), ("2024-01-05", "C")],
        names=["date", "symbol"],
    )
    preds = pd.Series([0.1, 0.1, 0.1], index=idx)  # constant → no cross-section
    labels = pd.Series([0.1, 0.2, 0.3], index=idx)
    daily = calculate_daily_cs_ic(preds, labels)
    assert daily.isna().all()


# --- L1: max_participation >= 1.0 must still cap by day volume ---


def test_l1_full_participation_still_volume_capped() -> None:
    bar = DailyBar(open=10.0, high=10.5, low=9.5, close=10.0, volume=300.0, prev_close=10.0)
    order = LimitOrder(symbol="600000", side="BUY", shares=100_000, limit_price=10.5)
    touch = match_limit_daily_ohlc(order, bar, max_participation=1.0)
    assert touch.shares == 300


# --- L3: DataScope.symbol_meta must be read-only ---


def test_l3_symbol_meta_readonly() -> None:
    from ashare_infra.guard.scope import MetaSource, SymbolLifecycle

    scope = DataScope(
        symbols=frozenset({"600000"}),
        window_start=date(2024, 1, 2),
        window_end=date(2024, 1, 31),
    )
    lifecycle = SymbolLifecycle(
        list_date=date(2020, 1, 1), source=MetaSource(kind="stock_basic", evidence_ref="x")
    )
    with pytest.raises(TypeError):
        scope.symbol_meta["600000"] = lifecycle  # type: ignore[index]
