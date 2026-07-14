from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from ashare_lab.data import odp_source as odp


def _make_df(dates: list[str], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [100.0] * len(dates),
            "amount": [1000.0] * len(dates),
        }
    ).set_index("date")


def test_normalize_odp_equity_symbol_for_yfinance() -> None:
    assert odp._normalize_odp_equity_symbol("600519", provider="yfinance") == "600519.SS"
    assert odp._normalize_odp_equity_symbol("000001", provider="yfinance") == "000001.SZ"
    assert odp._normalize_odp_equity_symbol("600519.SH", provider="yfinance") == "600519.SS"
    assert odp._normalize_odp_equity_symbol("000001.SZ", provider="yfinance") == "000001.SZ"


def test_normalize_odp_payload_results_mapping() -> None:
    payload: dict[str, Any] = {
        "results": [
            {"date": "2025-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 123},
            {"date": "2025-01-03", "open": 10.6, "high": 11.1, "low": 10.1, "close": 10.7, "volume": 100},
        ]
    }
    out = odp._normalize_odp_payload_to_df(payload)
    assert list(out.columns) == list(odp.SUPPORTED_FIELDS)
    assert len(out) == 2
    assert out.index.name == "date"
    assert float(out.loc[pd.Timestamp("2025-01-02"), "close"]) == pytest.approx(10.5)


def test_normalize_odp_payload_with_date_index_not_datetimeindex() -> None:
    df = pd.DataFrame(
        {
            "open": [10.0, 10.2],
            "high": [10.1, 10.3],
            "low": [9.9, 10.1],
            "close": [10.05, 10.25],
            "volume": [100.0, 120.0],
        },
        index=pd.Index(["2025-01-02", "2025-01-03"], name="date"),
    )
    out = odp._normalize_odp_payload_to_df(df)
    assert len(out) == 2
    assert out.index.name == "date"
    assert float(out.loc[pd.Timestamp("2025-01-03"), "close"]) == pytest.approx(10.25)


def test_fetch_odp_historical_bars_fallback_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bool] = {"sdk": False, "rest": False}
    expected = _make_df(["2025-01-02"], [10.0])

    def _sdk_fail(_req: Any) -> pd.DataFrame:
        seen["sdk"] = True
        raise RuntimeError("sdk fail")

    def _rest_ok(_req: Any) -> pd.DataFrame:
        seen["rest"] = True
        return expected

    monkeypatch.setattr(odp, "_fetch_odp_via_sdk", _sdk_fail)
    monkeypatch.setattr(odp, "_fetch_odp_via_rest", _rest_ok)

    req = odp.ODPHistoricalRequest(
        endpoint="equity/price/historical",
        symbol="600519.SS",
        start_date="20250102",
        end_date="20250102",
    )
    out = odp.fetch_odp_historical_bars(req)
    assert seen["sdk"] is True
    assert seen["rest"] is True
    assert len(out) == 1


def test_load_or_fetch_historical_bars_cache_hit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    req = odp.ODPHistoricalRequest(
        endpoint="equity/price/historical",
        symbol="600519.SS",
        start_date="20250102",
        end_date="20250103",
    )
    first = _make_df(["2025-01-02", "2025-01-03"], [10.0, 10.1])
    monkeypatch.setattr(odp, "fetch_odp_historical_bars", lambda _req: first)
    out1 = odp.load_or_fetch_historical_bars(req, cache_dir=tmp_path, refresh=False)
    assert len(out1) == 2

    def _should_not_run(_req: Any) -> pd.DataFrame:  # pragma: no cover
        raise AssertionError("cache should hit without fetching")

    monkeypatch.setattr(odp, "fetch_odp_historical_bars", _should_not_run)
    out2 = odp.load_or_fetch_historical_bars(req, cache_dir=tmp_path, refresh=False)
    assert len(out2) == 2
    assert float(out2.iloc[-1]["close"]) == pytest.approx(10.1)


def test_load_or_fetch_historical_bars_merge_extend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    req_1 = odp.ODPHistoricalRequest(
        endpoint="equity/price/historical",
        symbol="600519.SS",
        start_date="20250102",
        end_date="20250103",
    )
    req_2 = odp.ODPHistoricalRequest(
        endpoint="equity/price/historical",
        symbol="600519.SS",
        start_date="20250102",
        end_date="20250106",
    )

    calls: list[str] = []

    def _fetch(req: Any) -> pd.DataFrame:
        calls.append(f"{req.start_date}-{req.end_date}")
        if str(req.end_date).startswith("20250103"):
            return _make_df(["2025-01-02", "2025-01-03"], [10.0, 10.1])
        return _make_df(["2025-01-03", "2025-01-06"], [10.1, 10.4])

    monkeypatch.setattr(odp, "fetch_odp_historical_bars", _fetch)
    out1 = odp.load_or_fetch_historical_bars(req_1, cache_dir=tmp_path, refresh=False)
    out2 = odp.load_or_fetch_historical_bars(req_2, cache_dir=tmp_path, refresh=False)

    assert len(calls) == 2
    assert len(out1) == 2
    assert len(out2) == 3
    assert float(out2.loc[pd.Timestamp("2025-01-06"), "close"]) == pytest.approx(10.4)


def test_load_or_fetch_daily_bars_normalizes_equity_symbol(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    def _capture(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = (cache_dir, refresh)
        seen["symbol"] = req.symbol
        return _make_df(["2025-01-02"], [10.0])

    monkeypatch.setattr(odp, "load_or_fetch_historical_bars", _capture)
    req = odp.ODPDailyBarsRequest(symbol="600519.SH", start_date="20250102", end_date="20250102")
    out = odp.load_or_fetch_daily_bars(req, cache_dir=tmp_path)
    assert seen["symbol"] == "600519.SS"
    assert len(out) == 1
