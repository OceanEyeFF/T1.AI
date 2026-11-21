import csv
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from ashare_infra.data import external_daily
from ashare_infra.lake import DataLake
from scripts.account_replay import main

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/account_replay/with_context"
OPENING, THROUGH = "2026-11-20", "2026-11-26"


def _import_account(tmp_path, market, *, operations=None, overrides=None, prices=None):
    account = market.lower()
    fixtures = FIXTURES / account
    common = ["--db", str(tmp_path / f"{account}.sqlite"), "--account", account]
    for kind in ("opening", "events", "operations", "statement"):
        path = (overrides or {}).get(kind, fixtures / f"{kind}.csv")
        if kind == "operations" and operations:
            path = operations
        args = ["import", *common, "--market", market, "--kind", kind, "--csv", str(path)]
        if kind == "events":
            args += ["--coverage-start", "2026-11-21", "--coverage-end", THROUGH]
        assert main(args) == 0
    return [
        "replay",
        *common,
        "--opening",
        OPENING,
        "--through",
        THROUGH,
        "--out-dir",
        str(tmp_path / account),
        "--prices-csv",
        str(prices or fixtures / "prices.csv"),
        "--external-cache-dir",
        str(tmp_path / "cache"),
    ]


def _rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_two_account_decision_replay_and_native_pnl(tmp_path, monkeypatch):
    lake = DataLake(tmp_path / "cache", tushare_token="fixture")
    trade_day = date.fromisoformat(OPENING)
    clock = [datetime.fromisoformat("2026-11-21T20:00:00+08:00")]
    monkeypatch.setattr(external_daily, "_now", lambda: clock[0])

    def provider(endpoint, symbol, *_args, **_kwargs):
        return {
            "fields": ["ts_code", "trade_date", "open", "high", "low", "close"],
            "items": [[symbol, "20261120", 100, 100, 100, 100]],
        }

    monkeypatch.setattr(external_daily, "_query_tushare", provider)
    lake.refresh_external_daily("SPX", trade_day, trade_day)
    clock[0] = datetime.fromisoformat("2026-11-23T10:10:00+08:00")
    lake.refresh_external_daily("SC.INE", trade_day, trade_day)

    def no_network(*_args, **_kwargs):
        pytest.fail("account decision replay must only use cached market data")

    monkeypatch.setattr(external_daily, "_query_tushare", no_network)
    for market, currency, final_pnl in [("CN", "CNY", "30900"), ("HK", "HKD", "290885")]:
        assert main(_import_account(tmp_path, market)) == 0
        run = tmp_path / market.lower()
        decisions = json.loads((run / "decision_replay.json").read_text(encoding="utf-8"))
        assert len(decisions) == 4
        assert all(d["currency"] == currency and d["market"] == market for d in decisions)
        assert [d["external"]["SPX"]["rows"] for d in decisions] == [1] * 4
        assert [d["external"]["SC.INE"]["rows"] for d in decisions] == [0, 1, 1, 1]
        assert all(
            datetime.fromisoformat(item["latest"]["available_at"])
            <= datetime.fromisoformat(d["decision_at"])
            for d in decisions
            for item in d["external"].values()
            if item["latest"]
        )
        pnl = {row["date"]: row for row in _rows(run / "pnl_daily.csv")}
        assert pnl[OPENING]["pnl_since_open_cents"] == "0"
        assert pnl[THROUGH]["currency"] == currency
        assert pnl[THROUGH]["pnl_since_open_cents"] == final_pnl
        assert all(row["attribution_status"] == "pass" for row in pnl.values())
        (sale,) = _rows(run / "sales_pnl.csv")
        assert (sale["currency"], sale["shares"]) == (currency, "100")
        final = [row for row in _rows(run / "reconciliation.csv") if row["date"] == THROUGH]
        assert [(row["status"], row["difference"]) for row in final] == [("pass", "0")] * (
            2 if market == "CN" else 3
        )

        if market == "CN":
            assert [(d["positions"]["600000.SH"], d["cash_cents"]) for d in decisions] == [
                (500, 2000000),
                (700, 1798500),
                (700, 1798500),
                (600, 2000900),
            ]
            assert pnl[THROUGH]["net_transfers_cents"] == "100000"
            assert pnl["2026-11-25"]["pnl_change_cents"] == "6000"
            assert [
                sale[key]
                for key in (
                    "gross_proceeds_cents",
                    "fifo_cost_cents",
                    "sell_fees_cents",
                    "realized_net_cents",
                )
            ] == ["103000", "100000", "600", "2400"]
            assert [
                pnl[THROUGH][key]
                for key in ("realized_net_cents", "unrealized_cents", "fees_cents")
            ] == ["1900", "29000", "1100"]
        else:
            assert [d["positions"]["00700.HK"] for d in decisions] == [100, 300, 300, 300]
            assert [d["positions"]["00005.HK"] for d in decisions] == [300, 300, 300, 200]
            assert [d["cash_cents"] for d in decisions] == [13000000, 13000000, 13000000, 3377265]
            assert [d["pending_settlement_cents"] for d in decisions] == [
                0,
                -9622735,
                -9622735,
                593620,
            ]
            assert pnl["2026-11-23"]["pnl_since_open_cents"] == "-10735"
            assert pnl["2026-11-25"]["pnl_change_cents"] == "0"
            assert pnl[THROUGH]["pending_settlement_cents"] == "0"
            assert [
                sale[key]
                for key in (
                    "gross_proceeds_cents",
                    "fifo_cost_cents",
                    "sell_fees_cents",
                    "realized_net_cents",
                )
            ] == ["600000", "600000", "6380", "-6380"]
            assert [
                pnl[THROUGH][key]
                for key in ("realized_net_cents", "unrealized_cents", "fees_cents")
            ] == ["-24615", "315500", "24615"]


@pytest.mark.parametrize(
    ("market", "original", "flat", "day", "cash_delta", "pending_delta", "transfer_delta"),
    [
        (
            "CN",
            "2026-11-25,600000.SH,10.30",
            "2026-11-25,600000.SH,10.20",
            "2026-11-25",
            100000,
            0,
            100000,
        ),
        (
            "HK",
            "2026-11-26,00700.HK,490.00\n2026-11-26,00005.HK,61.00",
            "2026-11-26,00700.HK,485.00\n2026-11-26,00005.HK,60.50",
            "2026-11-26",
            593620,
            -593620,
            0,
        ),
    ],
)
def test_cash_moves_do_not_create_profit_when_marks_are_flat(
    tmp_path,
    market,
    original,
    flat,
    day,
    cash_delta,
    pending_delta,
    transfer_delta,
):
    price_text = (FIXTURES / market.lower() / "prices.csv").read_text(encoding="utf-8")
    assert original in price_text
    prices = tmp_path / "flat_prices.csv"
    prices.write_text(price_text.replace(original, flat), encoding="utf-8")
    assert main(_import_account(tmp_path, market, prices=prices)) == 0
    rows = _rows(tmp_path / market.lower() / "pnl_daily.csv")
    index = next(i for i, row in enumerate(rows) if row["date"] == day)
    previous, current = rows[index - 1 : index + 1]
    assert current["pnl_change_cents"] == "0"
    assert current["attribution_difference_cents"] == "0"
    for field, delta in (
        ("cash_cents", cash_delta),
        ("pending_settlement_cents", pending_delta),
        ("net_transfers_cents", transfer_delta),
    ):
        assert int(current[field]) - int(previous[field]) == delta
    for field in ("realized_net_cents", "unrealized_cents", "fees_cents"):
        assert current[field] == previous[field]


def test_fifo_crosses_lots_and_allocates_order_fee_without_losing_cents(tmp_path):
    events = _rows(FIXTURES / "cn" / "events.csv")
    new_rows = []
    for row in events:
        if row["id"] == "CN-F2":
            new_rows.append({**row, "shares_delta": "-400", "gross_amount": "4120.00"})
            new_rows.append(
                {
                    **row,
                    "id": "CN-F3",
                    "shares_delta": "-200",
                    "gross_amount": "2060.00",
                    "effective_at": "2026-11-24T11:01:00+08:00",
                }
            )
            continue
        if row["id"] == "CN-C3":
            row["cash_delta"] = "6180.00"
        if row["id"] == "CN-C4":
            row["cash_delta"] = "-6.01"
            row["symbol"] = ""
        new_rows.append(row)
    events_path = tmp_path / "split_sales.csv"
    with events_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(new_rows)
    statement = tmp_path / "statement.csv"
    statement.write_text(
        "date,field,symbol,value\n2026-11-26,cash,,25158.99\n2026-11-26,position,600000.SH,100\n",
        encoding="utf-8",
    )
    assert (
        main(
            _import_account(
                tmp_path, "CN", overrides={"events": events_path, "statement": statement}
            )
        )
        == 0
    )
    first, second = _rows(tmp_path / "cn" / "sales_pnl.csv")
    assert [
        (row["fifo_cost_cents"], row["sell_fees_cents"], row["realized_net_cents"])
        for row in (first, second)
    ] == [("400000", "400", "11600"), ("200500", "201", "5299")]
    assert [(lot["source"], lot["shares"]) for lot in json.loads(second["fifo_lots"])] == [
        ("opening", 100),
        ("CN-F1", 100),
    ]
    final = _rows(tmp_path / "cn" / "pnl_daily.csv")[-1]
    assert final["pnl_since_open_cents"] == "20899"
    assert final["attribution_difference_cents"] == "0"


def test_context_rejects_an_operation_without_an_actual_cutoff(tmp_path, capsys):
    opening = FIXTURES / "cn" / "operations.csv"
    date_only = tmp_path / "date_only.csv"
    date_only.write_text(
        "\n".join(
            line.rsplit(",", 1)[0] for line in opening.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
    )
    assert main(_import_account(tmp_path, "CN", operations=date_only)) == 1
    assert "requires decision_at" in capsys.readouterr().err
    assert not (tmp_path / "cn").exists()
