import json
from datetime import date, datetime
from pathlib import Path

import pytest

from ashare_infra.data import external_daily
from ashare_infra.lake import DataLake
from scripts.external_daily import main

MANUAL_OPERATIONS = (
    Path(__file__).resolve().parents[2] / "fixtures/external_daily/manual_operations.csv"
)


def _at(day, time):
    return datetime.fromisoformat(f"2026-11-{day}T{time}+08:00")


def _payload(symbol, day, close):
    return {
        "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "vol"],
        "items": [[symbol, f"202611{day}", close, close, close, close, None]],
    }


def test_cn_and_hk_decisions_only_see_prior_observations(tmp_path, monkeypatch, capsys):
    lake = DataLake(tmp_path, tushare_token="fixture")
    start = date(2026, 11, 17)
    today = date(2026, 11, 18)
    clock = [_at("18", "13:15:00")]
    monkeypatch.setattr(external_daily, "_now", lambda: clock[0])
    fetched = []

    def provider(endpoint, symbol, start, end, token, **_):
        fetched.append((endpoint, symbol, end))
        return _payload(symbol, str(end.day), 10)

    monkeypatch.setattr(external_daily, "_query_tushare", provider)
    for symbol in ("SPX", "IXIC"):
        lake.refresh_external_daily(symbol, start, today)
    assert all(end == start for _, _, end in fetched)
    clock[0] = _at("18", "15:30:00")
    for symbol in ("HSI", "HKTECH", "AU.SHF"):
        lake.refresh_external_daily(symbol, start, today)
    assert fetched[-1][0] == "fut_daily"
    clock[0] = _at("19", "13:15:00")
    lake.refresh_external_daily("SPX", start, today)
    assert fetched[-1] == ("index_global", "SPX", today)

    def no_network(*_, **__):
        pytest.fail("replay must not fetch or refresh data")

    monkeypatch.setattr(external_daily, "_query_tushare", no_network)
    for market, cutoff in [("CN", _at("18", "15:00:00")), ("HK", _at("18", "16:10:00"))]:
        assert (
            main(
                [
                    "--cache-dir",
                    str(tmp_path),
                    "replay",
                    "--market",
                    market,
                    "--as-of",
                    cutoff.isoformat(),
                ]
            )
            == 0
        )
        series = json.loads(capsys.readouterr().out)["series"]
        assert series["SPX"]["latest"]["trade_date"] == "2026-11-17"
        assert series["IXIC"]["latest"]["trade_date"] == "2026-11-17"
        assert all(
            series[code]["rows"] == (0 if market == "CN" else 1)
            for code in ("HSI", "HKTECH", "AU.SHF")
        )
        for entry in series.values():
            if entry["latest"]:
                assert datetime.fromisoformat(entry["latest"]["available_at"]) <= cutoff


def test_backfills_and_revisions_do_not_rewrite_prior_information(tmp_path, monkeypatch):
    lake = DataLake(tmp_path, tushare_token="fixture")
    trade_day = date(2026, 11, 16)
    first, second, third = (_at("18", "13:15:00"), _at("19", "14:00:00"), _at("20", "14:00:00"))
    clock = [first]
    payload = [_payload("SPX", "16", 10)]
    monkeypatch.setattr(external_daily, "_now", lambda: clock[0])
    monkeypatch.setattr(external_daily, "_query_tushare", lambda *_, **__: payload[0])

    assert lake.refresh_external_daily("SPX", trade_day, trade_day)["inserted"] == 1
    assert not lake.load_external_daily(as_of=_at("18", "13:14:59"))["SPX"]
    clock[0] = second
    payload[0] = _payload("SPX", "16", 11)
    assert lake.refresh_external_daily("SPX", trade_day, trade_day)["inserted"] == 1
    clock[0] = third
    assert lake.refresh_external_daily("SPX", trade_day, trade_day)["inserted"] == 0
    assert lake.load_external_daily(as_of=first)["SPX"][0]["close"] == 10
    (latest,) = lake.load_external_daily(as_of=third)["SPX"]
    assert latest["close"] == 11
    assert datetime.fromisoformat(latest["available_at"]) == second


def test_future_session_row_and_naive_decision_time_are_rejected(tmp_path, monkeypatch):
    lake = DataLake(tmp_path, tushare_token="fixture")
    monkeypatch.setattr(external_daily, "_now", lambda: _at("18", "15:00:00"))
    monkeypatch.setattr(
        external_daily, "_query_tushare", lambda *_, **__: _payload("HSI", "18", 10)
    )
    with pytest.raises(ValueError, match="unexpected symbol or trade date"):
        lake.refresh_external_daily("HSI", date(2026, 11, 17), date(2026, 11, 18))
    assert not lake.load_external_daily(as_of=_at("19", "15:00:00"))["HSI"]
    with pytest.raises(ValueError, match="timezone"):
        lake.load_external_daily(as_of=datetime(2026, 11, 18, 15))  # noqa: DTZ001


def test_replay_manual_operations_uses_each_cn_and_hk_cutoff(tmp_path, monkeypatch, capsys):
    lake = DataLake(tmp_path, tushare_token="fixture")
    clock = [_at("21", "20:24:00")]
    trade_day = date(2026, 11, 20)
    added = {"CU.SHF", "SC.INE", "PG.DCE", "TA.ZCE"}
    monkeypatch.setattr(external_daily, "_now", lambda: clock[0])

    def provider(endpoint, symbol, *_args, **_kwargs):
        if symbol in added:
            assert endpoint == "fut_daily"
        return _payload(symbol, "20", 10)

    monkeypatch.setattr(external_daily, "_query_tushare", provider)
    for symbol in ("SPX", "IXIC", "AU.SHF", "HSI", "HKTECH"):
        lake.refresh_external_daily(symbol, trade_day, trade_day)
    clock[0] = _at("21", "20:30:00")
    for symbol in sorted(added):
        lake.refresh_external_daily(symbol, trade_day, trade_day)

    def no_network(*_args, **_kwargs):
        pytest.fail("replaying a manual log must use only cached observations")

    monkeypatch.setattr(external_daily, "_query_tushare", no_network)
    args = ["--cache-dir", str(tmp_path), "replay-operations", "--csv", str(MANUAL_OPERATIONS)]
    assert main(args) == 0
    operations = json.loads(capsys.readouterr().out)["operations"]
    assert [(r["id"], r["symbol"], r["action"]) for r in operations] == [
        ("CN-01", "600000.SH", "plan"),
        ("HK-01", "00700.HK", "hold"),
        ("CN-02", "600000.SH", "note"),
        ("HK-02", "00700.HK", "note"),
        ("CN-03", "600000.SH", "plan"),
        ("HK-03", "00700.HK", "plan"),
    ]
    expected = [set(), set(external_daily.SERIES) - added, set(external_daily.SERIES)]
    for operation, symbols in zip(
        operations, [group for group in expected for _ in range(2)], strict=True
    ):
        visible = {code for code, state in operation["series"].items() if state["rows"]}
        assert visible == symbols
        for code in visible:
            bar = operation["series"][code]["latest"]
            assert datetime.fromisoformat(bar["available_at"]) <= datetime.fromisoformat(
                operation["decision_at"]
            )

    missing_offset = tmp_path / "missing_offset.csv"
    missing_offset.write_text(
        MANUAL_OPERATIONS.read_text(encoding="utf-8").replace("+08:00", "", 1),
        encoding="utf-8",
    )
    assert main([*args[:-1], str(missing_offset)]) == 1
    error = capsys.readouterr()
    assert error.out == ""
    assert "line 2" in error.err and "UTC offset" in error.err
