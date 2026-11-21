"""Audit saved cosine-8 and long-fit Transformer signals and portfolios."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_exec.weight_mapper import WeightMapper
from ashare_infra.ops_backup import digest
from ashare_lab.research_baseline import frame_hash

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "outputs/reports/ashare_transformer_width_long_fit_20261120"
POLICIES = {"fixed_top10": None, "retain_top15": 15}
PREDICTIONS = ["pred_3d", "pred_5d", "pred_10d"]
INITIAL_CASH = 1_000_000


def rank_signals(frame, scored_dates):
    ranked = frame.copy()
    ranked["execution_date"] = ranked["entry_at"].dt.tz_localize(None).dt.normalize()
    ranked["segment"] = np.where(ranked["date"].isin(scored_dates), "scored", "tail")
    ranks = ranked.groupby("date")[["pred_5d", "pred_10d"]].rank(pct=True)
    ranked["score"] = 0.5 * ranks["pred_5d"] + 0.5 * ranks["pred_10d"]
    ranked = ranked.sort_values(
        ["execution_date", "score", "symbol"], ascending=[True, False, True]
    )
    ranked["rank"] = ranked.groupby("execution_date").cumcount() + 1
    return {day: rows.set_index("symbol") for day, rows in ranked.groupby("execution_date")}


def codes(values):
    return "|".join(sorted(values))


def boundary(date, before, after):
    row = {
        "execution_date": date,
        "signal_date": before["date"].iloc[0],
        "segment": before["segment"].iloc[0],
    }
    for size in (10, 15):
        early, late = set(before.index[:size]), set(after.index[:size])
        key = f"top{size}"
        row[f"{key}_entries"] = codes(late - early)
        row[f"{key}_exits"] = codes(early - late)
        row[f"{key}_replacements"] = len(late - early)
        for version, ranked in (("short", before), ("long", after)):
            score = ranked["score"]
            gap = float(score.iloc[size - 1] - score.iloc[size])
            tied = score.index[score.eq(score.iloc[size - 1])] if gap == 0 else []
            row[f"{key}_gap_{version}"] = gap
            row[f"{key}_ties_{version}"] = codes(tied)
    return row


def read_closes(cache, hashes, start, end):
    closes = {}
    start_stamp, end_stamp = (datetime.combine(day, datetime.min.time()) for day in (start, end))
    for symbol, expected in hashes.items():
        parts = []
        for year in range(start.year, end.year + 1):
            part = cache / "tushare" / symbol / f"year={year}" / "part.parquet"
            if part.is_file():
                parts.append(
                    pd.read_parquet(
                        part, filters=[("date", ">=", start_stamp), ("date", "<=", end_stamp)]
                    )
                )
        if not parts:
            raise ValueError(f"missing raw price archive for {symbol}")
        frame = pd.concat(parts).set_index("date").sort_index()
        if frame_hash(frame) != expected["raw"]:
            raise ValueError(f"raw market data differs from saved run for {symbol}")
        closes[symbol] = frame["close"]
    return pd.DataFrame(closes).sort_index().ffill()


def value_book(positions, fills, close, equity):
    """Return per-session marked gains and fees at the recorded fills, with a cash check."""
    executed = fills.copy()
    executed["signed_quantity"] = np.where(
        executed.side.eq("BUY"), executed.shares, -executed.shares
    )
    executed["fill_mark"] = executed["signed_quantity"] * (
        [close.at[day, symbol] for day, symbol in zip(executed.date, executed.symbol, strict=True)]
        - executed["price"]
    )
    executed["signed_amount"] = executed["signed_quantity"] * executed["price"]

    def by_stock(column):
        return (
            executed.pivot_table(index="date", columns="symbol", values=column, aggfunc="sum")
            .reindex(index=close.index, columns=close.columns)
            .fillna(0)
        )

    executed["bought"] = executed.shares.where(executed.side.eq("BUY"), 0)
    executed["sold"] = executed.shares.where(executed.side.eq("SELL"), 0)
    previous = positions.shift(fill_value=0)
    quantity = by_stock("signed_quantity")
    mark = (previous * close.diff()).fillna(0)
    fill_mark = by_stock("fill_mark")
    fees = by_stock("cost")
    net = mark + fill_mark - fees
    np.testing.assert_array_equal(quantity.cumsum().to_numpy(), positions.to_numpy())
    cash = INITIAL_CASH - (by_stock("signed_amount") + fees).sum(axis=1).cumsum()
    np.testing.assert_allclose(cash, equity["cash"], rtol=0, atol=1e-6)
    np.testing.assert_allclose(
        cash + (positions * close).sum(axis=1), equity["equity"], rtol=0, atol=1e-6
    )
    np.testing.assert_allclose(
        net.sum(axis=1),
        equity.equity.diff().fillna(equity.equity.iloc[0] - INITIAL_CASH),
        rtol=0,
        atol=1e-6,
    )
    return {
        "old_shares": previous,
        "end_shares": positions,
        "buy_shares": by_stock("bought"),
        "sell_shares": by_stock("sold"),
        "old_shares_pnl": mark,
        "fill_mark_pnl": fill_mark,
        "fees": fees,
        "net_pnl": net,
    }


def read_replay(source, model, policy, closes):
    stub = source / f"{model}_{policy}"
    equity = pd.read_csv(
        stub.with_name(stub.name + "_equity.csv"), index_col="date", parse_dates=True
    )
    positions = pd.read_csv(
        stub.with_name(stub.name + "_positions.csv"), index_col="date", parse_dates=True
    )
    fills = pd.read_csv(stub.with_name(stub.name + "_fills.csv"), parse_dates=["date"])
    if not equity.index.equals(positions.index) or set(positions) - set(closes):
        raise ValueError(f"position dates or symbols differ from the equity/price archive: {stub}")
    if set(fills.side) - {"BUY", "SELL"} or not fills.date.isin(equity.index).all():
        raise ValueError(f"found unexpected fills: {stub}")
    positions = positions.reindex(columns=closes.columns, fill_value=0)
    book = value_book(positions, fills, closes.reindex(equity.index), equity)
    return equity, fills, book


def audit_policy(depth, policy, by_run, archives):
    daily, per_stock = [], []
    mapper = WeightMapper(top_n=10, retention_rank=POLICIES[policy])
    for date, before in by_run["short"].items():
        after = by_run["long"][date]
        audit = {
            "depth": depth,
            "policy": policy,
            "signal_date": before["date"].iloc[0],
            "execution_date": date,
            "segment": before["segment"].iloc[0],
        }
        per_run = {}
        for version, ranked in (("short", before), ("long", after)):
            equity, _, book = archives[version]
            by_day = pd.DataFrame({name: table.loc[date] for name, table in book.items()})
            by_day["rank"] = ranked["rank"]
            by_day["score"] = ranked["score"]
            old = by_day["old_shares"]
            eligible = set(ranked.index[:15]) & set(old.index[old.gt(0)])
            targets = set(
                mapper.map_weights(list(ranked.score.items()), current_positions=old.to_dict())
            )
            reserved = targets & eligible if POLICIES[policy] is not None else set()
            by_day["reserved"] = by_day.index.isin(reserved)
            by_day["selected"] = by_day.index.isin(targets)
            per_run[version] = by_day
            audit.update(
                {
                    f"target_{version}": codes(targets),
                    f"reserved_{version}": codes(reserved),
                    f"reserved_count_{version}": len(reserved),
                    f"bought_{version}": codes(by_day.index[by_day.buy_shares.gt(0)]),
                    f"sold_{version}": codes(by_day.index[by_day.sell_shares.gt(0)]),
                    f"end_holding_{version}": codes(by_day.index[by_day.end_shares.gt(0)]),
                    f"equity_{version}": equity.at[date, "equity"],
                    f"cash_{version}": equity.at[date, "cash"],
                }
            )
        short, long = per_run["short"], per_run["long"]
        merged = short.add_suffix("_short").join(long.add_suffix("_long")).rename_axis("symbol")
        for field in ("old_shares_pnl", "fill_mark_pnl", "fees", "net_pnl"):
            merged[f"delta_{field}"] = long[field] - short[field]
            audit[f"delta_{field}"] = float(merged[f"delta_{field}"].sum())
        audit["delta_equity"] = audit["equity_long"] - audit["equity_short"]
        per_stock.append(
            merged.reset_index().assign(
                **{
                    key: audit[key]
                    for key in ("depth", "policy", "signal_date", "execution_date", "segment")
                }
            )
        )
        daily.append(audit)
    result = pd.DataFrame(daily)
    np.testing.assert_allclose(
        result.delta_net_pnl.cumsum(), result.delta_equity, rtol=0, atol=1e-6
    )
    return result, pd.concat(per_stock, ignore_index=True)


def run(source, cache, out):
    if out.exists():
        raise ValueError("choose a new audit output directory")
    manifest = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    start = pd.Timestamp(manifest["fit_cutoff"]).date()
    end = pd.Timestamp(manifest["policy_execution_window"][-1]).date()
    closes = read_closes(cache, manifest["input_hashes"], start, end)
    oos = pd.read_parquet(source / "oos.parquet")
    metrics = pd.read_csv(source / "daily_metrics.csv", parse_dates=["date"])
    comparison = pd.read_csv(source / "policy_comparison.csv").set_index(["model", "policy"])
    boundaries, replay, symbols, actual = [], [], [], []
    reference = None
    for depth in (2, 4):
        model = f"encoder_decoder_3_{depth}_2x"
        names = {"short": model + "_cosine8", "long": model}
        by_run, comparable = {}, []
        for version, name in names.items():
            frame = oos.loc[oos.model.eq(name)].sort_values(["date", "symbol"])
            scored_dates = metrics.loc[metrics.model.eq(name) & metrics.horizon.eq(10), "date"]
            mature = frame.loc[frame.exit_10d_at.dt.date <= end, "date"].drop_duplicates()
            if (
                set(mature) != set(scored_dates)
                or len(scored_dates) != 54
                or frame.date.nunique() != 64
            ):
                raise ValueError(f"expected 54 scored and 10 tail signals for {name}")
            if frame.duplicated(["date", "symbol"]).any():
                raise ValueError(f"duplicate predictions for {name}")
            comparable.append(frame.drop(columns=["model", *PREDICTIONS]).reset_index(drop=True))
            by_run[version] = rank_signals(frame, scored_dates)
        pd.testing.assert_frame_equal(*comparable)
        if reference is None:
            reference = comparable[0]
        else:
            pd.testing.assert_frame_equal(reference, comparable[0])
        for date, before in by_run["short"].items():
            boundaries.append({"depth": depth, **boundary(date, before, by_run["long"][date])})
        for policy in POLICIES:
            logs = {
                version: read_replay(source, name, policy, closes)
                for version, name in names.items()
            }
            for version, (equity, fills, _) in logs.items():
                expected = comparison.loc[(names[version], policy)]
                np.testing.assert_allclose(
                    equity.equity.iloc[-1] / INITIAL_CASH - 1, expected.net_return
                )
                np.testing.assert_allclose(fills.cost.sum(), expected.fees)
                phase = {date: ranks["segment"].iloc[0] for date, ranks in by_run[version].items()}
                fills = fills.assign(
                    depth=depth, policy=policy, version=version, segment=fills.date.map(phase)
                )
                if fills.segment.isna().any():
                    raise ValueError("a fill falls outside the audited execution days")
                actual.append(fills)
            daily, detail = audit_policy(depth, policy, by_run, logs)
            replay.append(daily)
            symbols.append(detail)
    daily, detail = pd.concat(replay, ignore_index=True), pd.concat(symbols, ignore_index=True)
    money = ["delta_old_shares_pnl", "delta_fill_mark_pnl", "delta_fees", "delta_net_pnl"]
    grouped = daily.groupby(["depth", "policy", "segment"])
    segments = grouped[money].sum().assign(execution_days=grouped.size()).reset_index()
    by_symbol = detail.groupby(["depth", "policy", "segment", "symbol"])[money].sum().reset_index()
    out.mkdir(parents=True)
    for name, table in {
        "signal_boundaries": pd.DataFrame(boundaries),
        "daily_replay": daily,
        "symbol_daily": detail,
        "fills": pd.concat(actual, ignore_index=True),
        "segment_pnl": segments,
        "pnl_by_symbol": by_symbol,
    }.items():
        table.to_csv(out / f"{name}.csv", index=False, float_format="%.10f")
    sources = [
        source / name
        for name in ("summary.json", "oos.parquet", "daily_metrics.csv", "policy_comparison.csv")
    ]
    sources += [
        source / f"encoder_decoder_3_{depth}_2x{suffix}_{policy}_{kind}.csv"
        for depth in (2, 4)
        for suffix in ("_cosine8", "")
        for policy in POLICIES
        for kind in ("equity", "positions", "fills")
    ]
    (out / "sources.json").write_text(
        json.dumps({path.name: digest(path) for path in sources}, indent=2) + "\n", encoding="utf-8"
    )
    print(segments.round(2).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "inputs/data/cache")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.cache_dir, args.output_dir)


if __name__ == "__main__":
    main()
