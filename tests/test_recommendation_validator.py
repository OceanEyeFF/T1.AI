from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import ashare_lab.recommendation.validator as v


@dataclass(frozen=True)
class _DummyRec:
    """用于测试的轻量 Recommendation 替身。"""

    symbol: str
    predicted_return: float


class _FakeDailyBarsSource:
    """用于测试的假数据源：直接返回预置的日线数据。"""

    def __init__(self, bars_by_symbol: dict[str, pd.DataFrame]) -> None:
        self._bars_by_symbol = bars_by_symbol

    def fetch_daily_bars(self, symbols: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
        _ = (start_date, end_date)
        return {s: self._bars_by_symbol.get(s, pd.DataFrame()) for s in symbols}


class _FakeCalendarSource:
    """用于测试的假交易日历源：返回预置的 HS300 日线（索引即交易日历）。"""

    def __init__(self, hs300_df: pd.DataFrame) -> None:
        self._hs300_df = hs300_df

    def fetch_hs300_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        _ = (start_date, end_date)
        return self._hs300_df


def _df_with_close(dates: list[str], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(dates), "close": closes}).set_index("date")


def test_to_yyyymmdd_formats() -> None:
    assert v._to_yyyymmdd("2025-01-02") == "20250102"
    assert v._to_yyyymmdd("20250102") == "20250102"
    with pytest.raises(ValueError):
        v._to_yyyymmdd("2025/01/02")


def test_symbol_to_ts_code_rules() -> None:
    assert v._symbol_to_ts_code("600519") == "600519.SH"
    assert v._symbol_to_ts_code("000001") == "000001.SZ"
    assert v._symbol_to_ts_code("300001") == "300001.SZ"
    assert v._symbol_to_ts_code("830001") == "830001.BJ"
    assert v._symbol_to_ts_code("600519.SH") == "600519.SH"
    with pytest.raises(ValueError):
        v._symbol_to_ts_code("ABC")


def test_ensure_daily_schema_empty_and_missing_cols() -> None:
    out = v._ensure_daily_schema(pd.DataFrame())
    assert list(out.columns) == list(v._REQUIRED_DAILY_COLS)

    df = pd.DataFrame({"date": pd.to_datetime(["2025-01-01"]), "close": [10.0]}).set_index("date")
    out2 = v._ensure_daily_schema(df)
    assert list(out2.columns) == list(v._REQUIRED_DAILY_COLS)
    assert float(out2.loc[pd.Timestamp("2025-01-01"), "close"]) == 10.0


def test_tushare_source_adapter_converts_symbol_to_ts_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    def fake_load(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = (cache_dir, refresh)
        captured.append(req.symbol)
        return _df_with_close(["2025-01-02", "2025-01-03"], [10.0, 10.5])

    import ashare_lab.data.tushare_source as ts_src

    monkeypatch.setattr(ts_src, "load_or_fetch_daily_bars", fake_load)

    adapter = v.TushareSourceAdapter(cache_dir=tmp_path)
    bars = adapter.fetch_daily_bars(["600519"], start_date="2025-01-02", end_date="2025-01-03")
    assert captured == ["600519.SH"]
    assert "600519" in bars
    assert list(bars["600519"].columns) == list(v._REQUIRED_DAILY_COLS)


def test_akshare_source_adapter_schema_fill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = (req, cache_dir, refresh)
        # 故意只返回 close，验证适配器会补齐字段
        return _df_with_close(["2025-01-02"], [10.0])

    import ashare_lab.data.akshare_source as ak_src

    monkeypatch.setattr(ak_src, "load_or_fetch_daily_bars", fake_load)

    adapter = v.AkshareSourceAdapter(cache_dir=tmp_path)
    bars = adapter.fetch_daily_bars(["000001"], start_date="2025-01-02", end_date="2025-01-02")
    assert list(bars["000001"].columns) == list(v._REQUIRED_DAILY_COLS)


def test_hs300_index_calendar_source_uses_index_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def fake_load(req: Any, cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = (cache_dir, refresh)
        seen.append(req)
        return _df_with_close(["2025-01-02", "2025-01-03"], [100.0, 101.0])

    import ashare_lab.data.index_source as idx_src

    monkeypatch.setattr(idx_src, "load_or_fetch_index_daily", fake_load)

    cal = v.HS300IndexCalendarSource(cache_dir=tmp_path)
    df = cal.fetch_hs300_daily("2025-01-02", "2025-01-03")
    assert seen and seen[0].symbol == "000300"
    assert list(df.columns) == list(v._REQUIRED_DAILY_COLS)


def test_hs300_index_calendar_source_empty_df(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load(_req: Any, _cache_dir: Path, refresh: bool = False) -> pd.DataFrame:
        _ = refresh
        return pd.DataFrame()

    import ashare_lab.data.index_source as idx_src

    monkeypatch.setattr(idx_src, "load_or_fetch_index_daily", fake_load)

    cal = v.HS300IndexCalendarSource(cache_dir=tmp_path)
    df = cal.fetch_hs300_daily("2025-01-02", "2025-01-03")
    assert df.empty
    assert list(df.columns) == list(v._REQUIRED_DAILY_COLS)


def test_extract_symbol_and_score_variants_and_errors() -> None:
    @dataclass(frozen=True)
    class _RecScore:
        symbol: str
        score: float

    assert v._extract_symbol_and_score(_RecScore(symbol="A", score=0.1)) == ("A", 0.1)

    @dataclass(frozen=True)
    class _RecBad:
        symbol: str

    with pytest.raises(ValueError):
        v._extract_symbol_and_score(_RecBad(symbol="A"))
    with pytest.raises(ValueError):
        v._extract_symbol_and_score({"score": 0.1})
    with pytest.raises(ValueError):
        v._extract_symbol_and_score({"symbol": "A"})


def test_parse_recommendations_payload_variants() -> None:
    items, date = v._parse_recommendations_payload(
        {"date": "2025-01-02", "recommendations": [{"symbol": "A", "score": 0.1}]},
        validation_horizon=5,
        recommendation_date=None,
    )
    assert date == "2025-01-02"
    assert len(items) == 1

    items2, date2 = v._parse_recommendations_payload(
        {"date": "2025-01-02", "items": [{"symbol": "A", "score": 0.1}]},
        validation_horizon=2,
        recommendation_date=None,
    )
    assert date2 == "2025-01-02"
    assert len(items2) == 1

    items3, date3 = v._parse_recommendations_payload(
        {"date": "2025-01-02", "recs": [{"symbol": "A", "score": 0.1}]},
        validation_horizon=2,
        recommendation_date=None,
    )
    assert date3 == "2025-01-02"
    assert len(items3) == 1

    items4, date4 = v._parse_recommendations_payload(
        {"date": "2025-01-02", "recommendations": None},
        validation_horizon=2,
        recommendation_date=None,
    )
    assert date4 == "2025-01-02"
    assert items4 == []

    items5, date5 = v._parse_recommendations_payload(
        {"date": "2025-01-02", "recommendations": {"symbol": "A", "score": 0.1}},
        validation_horizon=2,
        recommendation_date=None,
    )
    assert date5 == "2025-01-02"
    assert len(items5) == 1

    with pytest.raises(ValueError):
        v._parse_recommendations_payload({"recommendations": []}, validation_horizon=2, recommendation_date=None)


def test_get_close_on_branches() -> None:
    assert v._get_close_on(pd.DataFrame(), pd.Timestamp("2025-01-02")) is None

    df_no_close = pd.DataFrame({"date": pd.to_datetime(["2025-01-02"]), "open": [1.0]}).set_index("date")
    assert v._get_close_on(df_no_close, pd.Timestamp("2025-01-02")) is None

    df_nan_close = pd.DataFrame({"date": pd.to_datetime(["2025-01-02"]), "close": [float("nan")]}).set_index("date")
    assert v._get_close_on(df_nan_close, pd.Timestamp("2025-01-02")) is None


def test_validator_init_and_horizon_errors() -> None:
    with pytest.raises(ValueError):
        v.RecommendationValidator(data_source=None)  # type: ignore[arg-type]

    hs300_df = _df_with_close(["2025-01-02"], [100.0])
    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource({}),
        calendar_source=_FakeCalendarSource(hs300_df),
    )
    with pytest.raises(ValueError):
        validator.validate([], validation_horizon=0, recommendation_date="2025-01-02")


def test_validator_calendar_insufficient_dates_raises() -> None:
    # 交易日历包含推荐日，但不足以覆盖 horizon，触发缓冲区扩展并最终报错
    hs300_df = _df_with_close(["2025-01-02"], [100.0])
    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource({}),
        calendar_source=_FakeCalendarSource(hs300_df),
    )
    with pytest.raises(ValueError):
        validator.validate([{"symbol": "A", "score": 0.1}], validation_horizon=5, recommendation_date="2025-01-02")


def test_validator_metrics_hit_rate_ic_rankic_excess_return() -> None:
    # 交易日历使用 HS300 指数日期
    hs300_df = _df_with_close(
        ["2025-01-02", "2025-01-03", "2025-01-06"],
        [100.0, 101.0, 102.0],
    )

    # 股票 A/B 有完整数据，C 在验证日缺价（NaN 掩码应剔除）
    bars_by_symbol = {
        "A": _df_with_close(["2025-01-02", "2025-01-06"], [10.0, 11.0]),
        "B": _df_with_close(["2025-01-02", "2025-01-06"], [20.0, 19.0]),
        "C": _df_with_close(["2025-01-02"], [30.0]),
    }

    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource(bars_by_symbol),
        calendar_source=_FakeCalendarSource(hs300_df),
    )

    recs = [
        {"symbol": "A", "score": 0.2},
        {"symbol": "B", "score": -0.1},
        {"symbol": "C", "score": 0.05},
    ]
    result = validator.validate(recs, validation_horizon=2, recommendation_date="2025-01-02")

    assert result.validation_date == "2025-01-06"
    assert result.valid_count == 2
    assert result.hit_rate == 1.0
    assert result.ic == 1.0
    assert result.rank_ic == pytest.approx(1.0)
    # 组合平均收益：(0.10 + -0.05)/2 = 0.025；基准收益：(102/100 - 1)=0.02
    assert result.excess_return == pytest.approx(0.005)


def test_validator_accepts_payload_date_and_horizon_key() -> None:
    hs300_df = _df_with_close(
        ["2025-01-02", "2025-01-03", "2025-01-06"],
        [100.0, 101.0, 102.0],
    )
    bars_by_symbol = {"A": _df_with_close(["2025-01-02", "2025-01-06"], [10.0, 11.0])}
    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource(bars_by_symbol),
        calendar_source=_FakeCalendarSource(hs300_df),
    )

    payload = {"date": "2025-01-02", "2d": [{"symbol": "A", "predicted_return": 0.2}]}
    result = validator.validate(payload, validation_horizon=2)
    assert result.validation_date == "2025-01-06"
    assert result.valid_count == 1


def test_validator_rec_date_not_in_calendar_raises() -> None:
    hs300_df = _df_with_close(["2025-01-02"], [100.0])
    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource({}),
        calendar_source=_FakeCalendarSource(hs300_df),
    )
    with pytest.raises(ValueError):
        validator.validate([_DummyRec(symbol="A", predicted_return=0.1)], validation_horizon=1, recommendation_date="2025-01-04")


def test_validator_all_nan_returns_yield_zero_metrics() -> None:
    hs300_df = _df_with_close(
        ["2025-01-02", "2025-01-03"],
        [100.0, 101.0],
    )
    # start/ end 收盘价缺失会导致收益为 NaN
    bars_by_symbol = {"A": _df_with_close(["2025-01-03"], [10.0])}
    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource(bars_by_symbol),
        calendar_source=_FakeCalendarSource(hs300_df),
    )
    result = validator.validate([_DummyRec(symbol="A", predicted_return=0.1)], validation_horizon=1, recommendation_date="2025-01-02")
    assert result.valid_count == 0
    assert result.hit_rate == 0.0
    assert result.ic == 0.0
    assert result.rank_ic == 0.0
    assert result.excess_return == 0.0


def test_to_yyyymmdd_empty_raises() -> None:
    with pytest.raises(ValueError):
        v._to_yyyymmdd("")


def test_ensure_daily_schema_sets_index_name_when_missing() -> None:
    df = pd.DataFrame({"dt": pd.to_datetime(["2025-01-01"]), "close": [10.0]}).set_index("dt")
    assert df.index.name == "dt"
    out = v._ensure_daily_schema(df)
    assert out.index.name == "date"


def test_symbol_to_ts_code_empty_and_unknown_prefix_raises() -> None:
    with pytest.raises(ValueError):
        v._symbol_to_ts_code("")
    with pytest.raises(ValueError):
        v._symbol_to_ts_code("900001")


def test_extract_symbol_and_score_unsupported_type_raises() -> None:
    with pytest.raises(ValueError):
        v._extract_symbol_and_score(123)


def test_validator_empty_recommendations_returns_zero_metrics() -> None:
    hs300_df = _df_with_close(
        ["2025-01-02", "2025-01-03", "2025-01-06"],
        [100.0, 101.0, 102.0],
    )
    validator = v.RecommendationValidator(
        data_source=_FakeDailyBarsSource({}),
        calendar_source=_FakeCalendarSource(hs300_df),
    )
    result = validator.validate([], validation_horizon=2, recommendation_date="2025-01-02")
    assert result.valid_count == 0
    assert result.hit_rate == 0.0
    assert result.ic == 0.0
    assert result.rank_ic == 0.0
    assert result.excess_return == 0.0
    assert result.validation_date == "2025-01-06"


def test_validator_empty_calendar_raises() -> None:
    class _EmptyCalendar:
        def fetch_hs300_daily(self, _start_date: str, _end_date: str) -> pd.DataFrame:
            return pd.DataFrame()

    validator = v.RecommendationValidator(data_source=_FakeDailyBarsSource({}), calendar_source=_EmptyCalendar())
    with pytest.raises(ValueError):
        validator.validate([{"symbol": "A", "score": 0.1}], validation_horizon=1, recommendation_date="2025-01-02")


def test_benchmark_return_missing_close_returns_nan() -> None:
    hs300_df = pd.DataFrame({"date": pd.to_datetime(["2025-01-02"]), "open": [1.0]}).set_index("date")
    validator = v.RecommendationValidator(data_source=_FakeDailyBarsSource({}), calendar_source=_FakeCalendarSource(hs300_df))
    out = validator._benchmark_return(hs300_df, pd.Timestamp("2025-01-02"), pd.Timestamp("2025-01-03"))
    assert math.isnan(out)
