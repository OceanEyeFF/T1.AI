import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from scripts.account_replay import main
from tests.support.account_replay_broker_style import normalize_broker_fixture

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "account_replay"
START = "2026-08-11"
END = "2026-08-13"


def _load(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _import(tmp_path, kind, path=None, start=START, end=END, *, market=None, account="manual"):
    args = [
        "import",
        "--db",
        str(tmp_path / "ledger.sqlite"),
        "--account",
        account,
        "--kind",
        kind,
        "--csv",
        str(path or FIXTURES / f"{kind}.csv"),
    ]
    if kind == "events":
        args.extend(["--coverage-start", start, "--coverage-end", end])
    if market is not None:
        args.extend(["--market", market])
    return main(args)


def _replay(
    tmp_path,
    name,
    batch=None,
    prices_csv=FIXTURES / "prices.csv",
    *,
    opening="2026-08-10",
    through=END,
    account="manual",
):
    args = [
        "replay",
        "--db",
        str(tmp_path / "ledger.sqlite"),
        "--account",
        account,
        "--opening",
        opening,
        "--through",
        through,
        "--out-dir",
        str(tmp_path / name),
    ]
    if prices_csv is not None:
        args.extend(["--prices-csv", str(prices_csv)])
    if batch is not None:
        args.extend(["--through-batch", str(batch)])
    return main(args)


def _manifest(run):
    return json.loads((run / "manifest.json").read_text(encoding="utf-8"))


def _sample_events_with(tmp_path, name, include):
    header, *events = (FIXTURES / "events.csv").read_text(encoding="utf-8").splitlines()
    path = tmp_path / name
    path.write_text("\n".join([header, *filter(include, events)]) + "\n", encoding="utf-8")
    return path


def test_replay_reconciles_manual_holdings_and_deduplicates_overlapping_exports(tmp_path, capsys):
    for kind in ("opening", "events", "statement", "operations"):
        assert _import(tmp_path, kind) == 0
    assert _replay(tmp_path, "initial") == 0
    capsys.readouterr()

    assert _import(tmp_path, "events") == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"batch_id": 2, "inserted": 0, "duplicates": 10}
    overlap = _sample_events_with(tmp_path, "overlap.csv", lambda line: "2026-08-13" in line)
    assert _import(tmp_path, "events", overlap, start=END) == 0
    assert json.loads(capsys.readouterr().out)["duplicates"] == 2
    assert _replay(tmp_path, "reimported") == 0

    run = tmp_path / "initial"
    account = _load(run / "account_daily.csv")
    assert [int(row["cash_cents"]) for row in account] == [2000000, 1397500, 1616900, 1725900]
    assert [int(row["equity_cents"]) for row in account] == [2490000, 2525000, 2606900, 2715900]
    positions = _load(run / "positions_daily.csv")
    assert [int(row["shares"]) for row in positions] == [500, 1100, 900, 900]
    assert (positions[-1]["price_status"], positions[-1]["price_date"]) == ("carried", "2026-08-12")
    assert [row["status"] for row in _load(run / "reconciliation.csv")] == ["unverified"] * 4 + [
        "pass"
    ] * 2
    assert _load(run / "operations.csv")[2]["fill_ids"] == "F001|F002"
    for name in ("positions_daily", "account_daily", "reconciliation", "operations"):
        assert (run / f"{name}.csv").read_bytes() == (
            tmp_path / "reimported" / f"{name}.csv"
        ).read_bytes()


def test_missing_fee_is_reported_and_backfill_preserves_previous_replay(tmp_path):
    for kind in ("opening", "statement"):
        assert _import(tmp_path, kind) == 0
    no_fee = _sample_events_with(tmp_path, "no_fee.csv", lambda line: not line.startswith("C005,"))
    assert _import(tmp_path, "events", no_fee) == 0
    assert _replay(tmp_path, "missing") == 2
    missing = tmp_path / "missing"
    final_cash, final_shares = _load(missing / "reconciliation.csv")[-2:]
    assert (final_cash["replayed"], final_cash["broker"], final_cash["difference"]) == (
        "1726500",
        "1725900",
        "600",
    )
    assert final_cash["status"] == "mismatch"
    assert final_shares["status"] == "pass"

    fee = _sample_events_with(tmp_path, "fee.csv", lambda line: line.startswith("C005,"))
    assert _import(tmp_path, "events", fee, start="2026-08-12", end="2026-08-12") == 0
    assert _replay(tmp_path, "repaired") == 0
    assert _manifest(tmp_path / "repaired")["status"] == "pass"
    assert _replay(tmp_path, "historical", batch=_manifest(missing)["through_batch"]) == 2
    assert (tmp_path / "historical" / "reconciliation.csv").read_bytes() == (
        missing / "reconciliation.csv"
    ).read_bytes()


def test_gap_prevents_a_pass_even_when_the_snapshot_values_match(tmp_path):
    assert _import(tmp_path, "opening") == 0
    statement = tmp_path / "statement.csv"
    statement.write_text(
        "date,field,symbol,value\n2026-08-13,cash,,16169.00\n2026-08-13,position,600000.SH,900\n",
        encoding="utf-8",
    )
    assert _import(tmp_path, "statement", statement) == 0
    early = _sample_events_with(tmp_path, "early.csv", lambda line: END not in line)
    assert _import(tmp_path, "events", early, end="2026-08-12") == 0
    assert _replay(tmp_path, "gap") == 2
    assert _manifest(tmp_path / "gap")["first_coverage_gap"] == END
    final = _load(tmp_path / "gap" / "reconciliation.csv")[-2:]
    assert [(row["status"], row["difference"]) for row in final] == [("incomplete", "0")] * 2


def test_conflicting_event_rolls_back_the_whole_file(tmp_path):
    for kind in ("opening", "events", "statement"):
        assert _import(tmp_path, kind) == 0
    header = (FIXTURES / "events.csv").read_text(encoding="utf-8").splitlines()[0]
    conflict = tmp_path / "conflict.csv"
    conflict.write_text(
        header + "\nX001,transfer,2026-08-13,2026-08-13,,,1.00,,\n"
        "C007,dividend,2026-08-13,2026-08-13,600000.SH,,91.00,,\n",
        encoding="utf-8",
    )
    assert _import(tmp_path, "events", conflict, start=END) == 1
    assert _replay(tmp_path, "after_conflict") == 0
    assert _manifest(tmp_path / "after_conflict")["through_batch"] == 3


def test_broker_style_exports_replay_trade_and_cash_on_their_respective_days(tmp_path):
    normalized = normalize_broker_fixture(FIXTURES / "broker_style", tmp_path / "normalized")
    assert _import(tmp_path, "opening", normalized["opening"]) == 0
    assert _import(tmp_path, "events", normalized["events"]) == 0
    assert _import(tmp_path, "operations", normalized["operations"]) == 0
    for name in ("trade_day_statement", "statement"):
        assert _import(tmp_path, "statement", normalized[name]) == 0

    assert _replay(tmp_path, "broker_style_replay", prices_csv=None) == 0
    run = tmp_path / "broker_style_replay"
    account = _load(run / "account_daily.csv")
    assert [int(row["cash_cents"]) for row in account] == [3000000, 3000000, 3122875, 3342267]
    assert account[1]["event_ids"] == "F-000061|F-000062"
    positions = {
        (row["date"], row["symbol"]): int(row["shares"])
        for row in _load(run / "positions_daily.csv")
    }
    assert positions[(START, "600000.SH")] == 700
    assert {symbol: qty for (day, symbol), qty in positions.items() if day == END} == {
        "000001.SZ": 200,
        "600000.SH": 500,
    }
    reconciliation = _load(run / "reconciliation.csv")
    for day in (START, END):
        comparisons = [row for row in reconciliation if row["date"] == day]
        assert [(row["status"], row["difference"]) for row in comparisons] == [("pass", "0")] * 3
    assert _load(run / "operations.csv")[1]["fill_ids"] == "F-000061|F-000062"


def test_hk_manual_account_replays_settlement_and_reconciles(tmp_path, capsys):
    account = "manual-hk"
    opening, start, end = "2026-11-16", "2026-11-17", "2026-11-20"
    normalized = normalize_broker_fixture(
        FIXTURES / "hk_broker_style",
        tmp_path / "normalized",
        market="HK",
    )
    for name, kind in (
        ("opening", "opening"),
        ("events", "events"),
        ("operations", "operations"),
        ("trade_day_statement", "statement"),
        ("statement", "statement"),
    ):
        assert (
            _import(tmp_path, kind, normalized[name], start, end, market="HK", account=account) == 0
        )
    capsys.readouterr()
    assert (
        _import(tmp_path, "events", normalized["events"], start, end, market="HK", account=account)
        == 0
    )
    assert json.loads(capsys.readouterr().out)["duplicates"] == 7
    assert (
        _replay(
            tmp_path,
            "hk_reconciled",
            prices_csv=None,
            opening=opening,
            through=end,
            account=account,
        )
        == 0
    )

    run = tmp_path / "hk_reconciled"
    manifest = _manifest(run)
    assert (manifest["market"], manifest["currency"], manifest["status"]) == ("HK", "HKD", "pass")
    cash = _load(run / "account_daily.csv")
    assert [int(row["cash_cents"]) for row in cash] == [
        13000000,
        13000000,
        13000000,
        3377265,
        3970885,
    ]
    assert [row["event_ids"] for row in cash[1:]] == [
        "F-000061|F-000062",
        "F-000063",
        "C-000071|C-000072|C-000073",
        "C-000074",
    ]
    positions = {
        (row["date"], row["symbol"]): int(row["shares"])
        for row in _load(run / "positions_daily.csv")
    }
    assert positions[(start, "00700.HK")] == 300
    assert positions[("2026-11-18", "00005.HK")] == 200
    final = _load(run / "reconciliation.csv")[-3:]
    assert {
        (row["symbol"], row["status"], row["difference"], row["replayed"]) for row in final
    } == {
        ("", "pass", "0", "3970885"),
        ("00005.HK", "pass", "0", "200"),
        ("00700.HK", "pass", "0", "300"),
    }
    assert _load(run / "operations.csv")[1]["fill_ids"] == "F-000061|F-000062"

    cash_only = tmp_path / "cash_only.csv"
    cash_only.write_text("date,field,symbol,value\n2026-11-21,cash,,39708.85\n", encoding="utf-8")
    capsys.readouterr()
    assert _import(tmp_path, "statement", cash_only, market="CN", account=account) == 1
    assert "already bound to HK" in capsys.readouterr().err


def test_existing_a_share_sqlite_without_market_metadata_still_replays(tmp_path, capsys):
    for kind in ("opening", "events", "statement"):
        assert _import(tmp_path, kind) == 0
    with closing(sqlite3.connect(tmp_path / "ledger.sqlite")) as conn, conn:
        conn.execute("DROP TABLE account_profiles")
    assert _replay(tmp_path, "legacy") == 0
    assert _manifest(tmp_path / "legacy")["currency"] == "CNY"

    cash_only = tmp_path / "cash_only.csv"
    cash_only.write_text("date,field,symbol,value\n2026-08-14,cash,,17259.00\n", encoding="utf-8")
    capsys.readouterr()
    assert _import(tmp_path, "statement", cash_only, market="HK") == 1
    assert "already bound to CN" in capsys.readouterr().err
