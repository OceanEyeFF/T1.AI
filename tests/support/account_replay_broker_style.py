"""Map one fictional broker export layout to the account replay CSV contract."""

import csv
from datetime import date
from pathlib import Path

from ashare_infra.account_ledger import CSV_FIELDS, MARKET_CURRENCIES

MARKETS = {"上海": "SH", "深圳": "SZ", "香港": "HK"}
SIDES = {"买入": "buy", "卖出": "sell"}
CASH_TYPES = {
    "买入成交款": "trade_cash",
    "买入交收净额": "trade_cash",
    "卖出交收净额": "trade_cash",
    "卖出成交款": "trade_cash",
    "交易费用": "fee",
    "交易佣金": "fee",
    "交易税费": "fee",
    "银证转入": "transfer",
    "股息入账": "dividend",
}


def _read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _day(value):
    return date(int(value[:4]), int(value[4:6]), int(value[6:])).isoformat()


def _symbol(row):
    return f"{row['证券代码']}.{MARKETS[row['市场']]}" if row["证券代码"] else ""


def _snapshot(rows):
    for row in rows:
        field, value = {
            "资金": ("cash", "资金余额"),
            "持仓": ("position", "总持仓股数"),
        }[row["项目"]]
        yield {
            "date": _day(row["快照日期"]),
            "field": field,
            "symbol": _symbol(row),
            "value": row[value],
        }


def _events(trades, cash):
    for row in trades:
        day = _day(row["成交日期"])
        side = SIDES[row["买卖方向"]]
        yield {
            "id": f"F-{row['成交编号']}",
            "type": f"{side}_fill",
            "event_date": day,
            "effective_date": day,
            "symbol": _symbol(row),
            "order_id": row["委托编号"],
            "shares_delta": int(row["成交数量"]) * (1 if side == "buy" else -1),
        }
    # The cash ledger owns monetary movements. Fees displayed in trades are informational.
    for row in cash:
        booked = row["记账日期"]
        yield {
            "id": f"C-{row['流水编号']}",
            "type": CASH_TYPES[row["业务类型"]],
            "event_date": _day(row["交易日期"] or booked),
            "effective_date": _day(booked),
            "symbol": _symbol(row),
            "cash_delta": row["资金变动"],
            "order_id": row["委托编号"],
        }


def _operations(rows):
    for row in rows:
        yield {
            "id": row["操作编号"],
            "date": _day(row["操作日期"]),
            "action": {"计划": "plan", "撤单": "cancel"}[row["动作"]],
            "symbol": _symbol(row),
            "side": SIDES[row["方向"]],
            "shares": row["股数"],
            "order_id": row["委托编号"],
            "reason": row["备注"],
        }


def normalize_broker_fixture(
    source: Path, destination: Path, *, market: str = "CN"
) -> dict[str, Path]:
    """Generate importer inputs; hold the synthetic broker statements independent of replay."""
    destination.mkdir(parents=True, exist_ok=True)
    names = ("opening", "trade_day_statement", "statement", "trades", "cash_ledger", "operations")
    raw = {name: _read(source / f"{name}.csv") for name in names}
    if market == "HK":
        for name in names[:-1]:
            if any(row.get("币种") != MARKET_CURRENCIES[market] for row in raw[name]):
                raise ValueError(f"{name}: fixture must report HKD")
    data = {
        "opening": ("opening", _snapshot(raw["opening"])),
        "trade_day_statement": ("statement", _snapshot(raw["trade_day_statement"])),
        "statement": ("statement", _snapshot(raw["statement"])),
        "events": ("events", _events(raw["trades"], raw["cash_ledger"])),
        "operations": ("operations", _operations(raw["operations"])),
    }
    paths = {}
    for name, (kind, rows) in data.items():
        path = destination / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS[kind].split(","))
            writer.writeheader()
            writer.writerows(rows)
        paths[name] = path
    return paths
