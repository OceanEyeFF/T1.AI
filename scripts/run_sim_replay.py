from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from ashare_infra.lake import DataLake
from ashare_infra.lake.r4_contract import R4_ADJUST_DEFAULT, make_r4_datalake
from ashare_lab.sim import LimitOrder, PaperBroker, ReplayConfig, ReplayEngine, SimConfig
from ashare_lab.symbols import symbol_to_ts_code
from ashare_lab.universe import is_allowed_a_share_symbol


class PrevCloseLimitPlanner:
    """
    Tiny demo planner (not a real strategy):

    - If flat: buy ``shares`` at previous close * buy_offset
    - If long: sell all sellable at previous close * sell_offset
    """

    def __init__(
        self,
        symbol: str,
        shares: int = 100,
        buy_offset: float = 1.0,
        sell_offset: float = 1.01,
    ) -> None:
        self._symbol = symbol
        self._shares = shares
        self._buy_offset = buy_offset
        self._sell_offset = sell_offset

    def plans(self, today, prev_date, history, broker: PaperBroker):
        _ = today
        if prev_date is None:
            return []
        df = history.get(self._symbol)
        if df is None or df.empty:
            return []
        prev_close = float(df.iloc[-1]["close"])
        if not prev_close == prev_close:
            return []

        held = broker.book.total_shares(self._symbol)
        sellable = broker.book.sellable_shares(self._symbol, today=today)
        if held <= 0:
            return [
                LimitOrder(
                    symbol=self._symbol,
                    side="BUY",
                    shares=self._shares,
                    limit_price=round(prev_close * self._buy_offset, 2),
                )
            ]
        if sellable > 0:
            return [
                LimitOrder(
                    symbol=self._symbol,
                    side="SELL",
                    shares=sellable,
                    limit_price=round(prev_close * self._sell_offset, 2),
                )
            ]
        return []


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Replay local paper broker on daily OHLCV cache.")
    p.add_argument("--symbol", required=True, help="e.g. 600519")
    p.add_argument("--start", required=True, help="YYYYMMDD")
    p.add_argument("--end", required=True, help="YYYYMMDD")
    p.add_argument("--cash", type=float, default=20_000.0)
    p.add_argument("--shares", type=int, default=100)
    p.add_argument("--source", default="akshare", choices=["akshare", "tushare"])
    p.add_argument("--cache-dir", default="inputs/data/cache")
    p.add_argument("--out-dir", default="outputs/sim")
    p.add_argument("--refresh", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if not is_allowed_a_share_symbol(args.symbol):
        raise SystemExit(f"symbol not allowed: {args.symbol}")

    if args.source == "tushare":
        lake = make_r4_datalake(cache_dir=args.cache_dir, refresh=args.refresh)
        lake_symbol = symbol_to_ts_code(args.symbol)
        adjust = R4_ADJUST_DEFAULT
    else:
        lake = DataLake(
            cache_dir=Path(args.cache_dir),
            default_source="akshare",
            refresh=args.refresh,
        )
        lake_symbol = args.symbol
        adjust = "qfq"
    df = lake.load_daily_bars(
        lake_symbol, args.start, args.end, source=args.source, adjust=adjust
    )
    if df.empty:
        raise SystemExit(f"empty data for {args.symbol}")

    sim_cfg = SimConfig(initial_cash=args.cash, max_participation=1.0)
    broker = PaperBroker(sim_cfg)
    planner = PrevCloseLimitPlanner(symbol=args.symbol, shares=args.shares)
    result = ReplayEngine(ReplayConfig(sim=sim_cfg)).run(
        {args.symbol: df}, planner=planner, broker=broker
    )

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / f"replay_{args.symbol}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.equity_curve.to_csv(out_dir / "equity.csv")
    result.fills.to_csv(out_dir / "fills.csv", index=False)
    result.rejects.to_csv(out_dir / "rejects.csv", index=False)
    pd.Series(result.diagnostics).to_csv(out_dir / "diagnostics.csv")
    print(f"wrote {out_dir}")
    print(dict(result.diagnostics))
    if not result.equity_curve.empty:
        print(
            "start_equity=",
            float(args.cash),
            "end_equity=",
            float(result.equity_curve.iloc[-1]["equity"]),
        )


if __name__ == "__main__":
    main()
