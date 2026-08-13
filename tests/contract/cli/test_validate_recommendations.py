from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest



def _df_close(dates: list[str], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(dates), "close": closes}).set_index("date")


class _FakeDailyBarsSource:
    """用于集成测试的假数据源：返回固定的收盘价序列。"""

    def __init__(self, bars_by_symbol: dict[str, pd.DataFrame]) -> None:
        self._bars_by_symbol = dict(bars_by_symbol)

    def fetch_daily_bars(self, symbols: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
        _ = (start_date, end_date)
        return {s: self._bars_by_symbol.get(s, pd.DataFrame()) for s in symbols}


class _FakeHS300CalendarSource:
    """用于集成测试的假交易日历：索引即交易日历。"""

    def __init__(self, hs300_df: pd.DataFrame) -> None:
        self._hs300_df = hs300_df

    def fetch_hs300_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        _ = (start_date, end_date)
        return self._hs300_df


def _install_fake_calendar(monkeypatch: pytest.MonkeyPatch, hs300_df: pd.DataFrame) -> None:
    """通过 monkeypatch 替换默认 HS300IndexCalendarSource，避免触发外部数据源。"""
    import ashare_lab.recommendation.validator as v

    class _Factory:
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            _ = (args, kwargs)

        def fetch_hs300_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
            return _FakeHS300CalendarSource(hs300_df).fetch_hs300_daily(start_date, end_date)

    monkeypatch.setattr(v, "HS300IndexCalendarSource", _Factory)


def test_validate_json_input_and_output_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    # 构造交易日历：horizon=5 时应落在第 6 个交易日
    trade_dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"]
    hs300_df = _df_close(trade_dates, [100, 101, 102, 103, 104, 105])
    _install_fake_calendar(monkeypatch, hs300_df)

    # 构造股票日线：保证推荐日与验证日都有 close
    bars_by_symbol = {
        "000001": _df_close(["2025-01-02", "2025-01-09"], [10.0, 11.0]),
        "000002": _df_close(["2025-01-02", "2025-01-09"], [20.0, 19.0]),
    }

    import scripts.validate_recommendations as vr

    monkeypatch.setattr(vr, "_create_data_source", lambda _source: _FakeDailyBarsSource(bars_by_symbol))

    input_path = tmp_path / "recommendations.json"
    input_path.write_text(
        json.dumps(
            {
                "date": "2025-01-02",
                "5d": [
                    {"rank": 1, "symbol": "000001", "predicted_return": 0.2},
                    {"rank": 2, "symbol": "000002", "predicted_return": -0.1},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "report.json"

    code = vr.main(["--input", str(input_path), "--horizon", "5", "--output", str(out_path)])
    assert code == 0

    stdout = capsys.readouterr().out
    assert "推荐验证报告" in stdout
    assert "验证日期" in stdout

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["source"] == "tushare"
    assert int(report["horizon"]) == 5
    assert report["rec_date"] == "2025-01-02"
    assert report["validation_date"] == "2025-01-09"
    assert int(report["metrics"]["valid_count"]) == 2
    assert float(report["metrics"]["hit_rate"]) == pytest.approx(1.0)


def test_validate_csv_input_and_save_to_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trade_dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"]
    hs300_df = _df_close(trade_dates, [100, 101, 102, 103, 104, 105])
    _install_fake_calendar(monkeypatch, hs300_df)

    bars_by_symbol = {
        "000001": _df_close(["2025-01-02", "2025-01-09"], [10.0, 11.0]),
        "000002": _df_close(["2025-01-02", "2025-01-09"], [20.0, 19.0]),
    }

    import scripts.validate_recommendations as vr

    monkeypatch.setattr(vr, "_create_data_source", lambda _source: _FakeDailyBarsSource(bars_by_symbol))

    input_path = tmp_path / "recommendations.csv"
    input_path.write_text(
        "\n".join(
            [
                "date,rank,symbol,predicted_return,note",
                "2025-01-02,1,000001,0.2,foo",
                "2025-01-02,2,000002,-0.1,bar",
            ]
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "history.db"
    code = vr.main(
        [
            "--input",
            str(input_path),
            "--horizon",
            "5",
            "--save-to-db",
            "--db-path",
            str(db_path),
        ]
    )
    assert code == 0

    from ashare_lab.recommendation import RecommendationHistory

    history = RecommendationHistory(db_path)
    try:
        recs = history.query_recommendations()
        assert len(recs) == 2
        assert set(recs["symbol"].tolist()) == {"000001", "000002"}

        vals = history.query_validations()
        assert len(vals) == 1
        assert vals.iloc[0]["rec_date"] == "2025-01-02"
        assert int(vals.iloc[0]["horizon"]) == 5
    finally:
        history.close()


def test_source_switch_is_wired(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trade_dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"]
    hs300_df = _df_close(trade_dates, [100, 101, 102, 103, 104, 105])
    _install_fake_calendar(monkeypatch, hs300_df)

    import scripts.validate_recommendations as vr

    seen: dict[str, str] = {}

    def _fake_create(source: str) -> Any:
        seen["source"] = source
        return _FakeDailyBarsSource(
            {
                "000001": _df_close(["2025-01-02", "2025-01-09"], [10.0, 11.0]),
                "000002": _df_close(["2025-01-02", "2025-01-09"], [20.0, 19.0]),
            }
        )

    monkeypatch.setattr(vr, "_create_data_source", _fake_create)

    input_path = tmp_path / "recommendations.json"
    input_path.write_text(
        json.dumps(
            {
                "date": "2025-01-02",
                "recommendations": [
                    {"rank": 1, "symbol": "000001", "score": 0.2},
                    {"rank": 2, "symbol": "000002", "score": -0.1},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    code = vr.main(["--input", str(input_path), "--source", "tushare", "--horizon", "5"])
    assert code == 0
    assert seen["source"] == "tushare"


def test_source_switch_to_odp_is_wired(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trade_dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"]
    hs300_df = _df_close(trade_dates, [100, 101, 102, 103, 104, 105])
    _install_fake_calendar(monkeypatch, hs300_df)

    import scripts.validate_recommendations as vr

    seen: dict[str, str] = {}

    def _fake_create(source: str) -> Any:
        seen["source"] = source
        return _FakeDailyBarsSource({"000001": _df_close(["2025-01-02", "2025-01-09"], [10.0, 10.8])})

    monkeypatch.setattr(vr, "_create_data_source", _fake_create)

    input_path = tmp_path / "recommendations.json"
    input_path.write_text(
        json.dumps(
            {"date": "2025-01-02", "recommendations": [{"rank": 1, "symbol": "000001", "score": 0.2}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    code = vr.main(["--input", str(input_path), "--source", "odp", "--horizon", "5"])
    assert code == 0
    assert seen["source"] == "odp"


def test_error_message_for_missing_input(tmp_path: Path, capsys: Any) -> None:
    import scripts.validate_recommendations as vr

    missing = tmp_path / "missing.json"
    code = vr.main(["--input", str(missing)])
    assert code == 1
    err = capsys.readouterr().err
    assert "输入文件不存在" in err


def test_load_json_supports_utf8_sig(tmp_path: Path) -> None:
    import scripts.validate_recommendations as vr

    p = tmp_path / "rec.json"
    p.write_text(json.dumps({"date": "2025-01-02", "recommendations": []}), encoding="utf-8-sig")
    payload = vr._load_json(p)
    assert payload["date"] == "2025-01-02"


def test_unsupported_input_suffix_raises(tmp_path: Path, capsys: Any) -> None:
    import scripts.validate_recommendations as vr

    p = tmp_path / "rec.txt"
    p.write_text("x", encoding="utf-8")
    code = vr.main(["--input", str(p)])
    assert code == 1
    err = capsys.readouterr().err
    assert "不支持的输入格式" in err


def test_csv_multiple_dates_raises(tmp_path: Path, capsys: Any) -> None:
    import scripts.validate_recommendations as vr

    p = tmp_path / "recommendations.csv"
    p.write_text(
        "\n".join(
            [
                "date,rank,symbol,predicted_return",
                "2025-01-02,1,000001,0.2",
                "2025-01-03,2,000002,-0.1",
            ]
        ),
        encoding="utf-8",
    )
    code = vr.main(["--input", str(p), "--horizon", "5"])
    assert code == 1
    err = capsys.readouterr().err
    assert "CSV 中存在多个推荐日期" in err


def test_csv_missing_symbol_or_score_raises(tmp_path: Path, capsys: Any) -> None:
    import scripts.validate_recommendations as vr

    p1 = tmp_path / "missing_symbol.csv"
    p1.write_text("date,rank,predicted_return\n2025-01-02,1,0.1\n", encoding="utf-8")
    assert vr.main(["--input", str(p1)]) == 1
    err1 = capsys.readouterr().err
    assert "缺少 symbol" in err1

    p2 = tmp_path / "missing_score.csv"
    p2.write_text("date,rank,symbol\n2025-01-02,1,000001\n", encoding="utf-8")
    assert vr.main(["--input", str(p2)]) == 1
    err2 = capsys.readouterr().err
    assert "缺少 score" in err2 or "缺少 score/predicted_return" in err2


def test_source_create_failure_prints_tushare_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    trade_dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"]
    hs300_df = _df_close(trade_dates, [100, 101, 102, 103, 104, 105])
    _install_fake_calendar(monkeypatch, hs300_df)

    import scripts.validate_recommendations as vr

    monkeypatch.setattr(vr, "_create_data_source", lambda _source: (_ for _ in ()).throw(RuntimeError("boom")))

    input_path = tmp_path / "recommendations.json"
    input_path.write_text(
        json.dumps({"date": "2025-01-02", "recommendations": [{"symbol": "000001", "score": 0.1}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    code = vr.main(["--input", str(input_path), "--source", "tushare"])
    assert code == 1
    err = capsys.readouterr().err
    assert "提示: 使用 TuShare" in err


def test_create_data_source_dispatch_real_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实 _create_data_source 分派（此前测试直接替换整个工厂，三分支从未被测）。"""
    import scripts.validate_recommendations as vr

    tushare = object()
    odp = object()
    monkeypatch.setattr(vr, "TushareSourceAdapter", lambda: tushare)
    monkeypatch.setattr(vr, "ODPSourceAdapter", lambda: odp)

    assert vr._create_data_source("tushare") is tushare
    assert vr._create_data_source("odp") is odp
    with pytest.raises(ValueError, match="不支持的数据源: akshare"):
        vr._create_data_source("akshare")
