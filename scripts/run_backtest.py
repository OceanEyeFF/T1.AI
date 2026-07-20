from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from ashare_infra.lake import DataLake
from ashare_lab.backtest.engine import BacktestConfig, BacktestEngine
from ashare_lab.reporting import align_equity_and_benchmark, summarize_excess
from ashare_lab.strategies.momentum import MomentumTopNStrategy
from ashare_lab.universe import is_allowed_a_share_symbol


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True, help="Comma-separated, e.g. 600519,000333")
    p.add_argument("--start", required=True, help="YYYYMMDD")
    p.add_argument("--end", required=True, help="YYYYMMDD")
    p.add_argument("--top-n", type=int, default=3)
    p.add_argument("--lookback", type=int, default=20)
    p.add_argument("--cash", type=float, default=100_000.0)
    p.add_argument("--refresh", action="store_true", help="Ignore cache and re-download")
    p.add_argument("--cache-dir", default="inputs/data/cache")
    p.add_argument("--out-dir", default="runs")
    p.add_argument("--benchmark", default="000300", help="Index symbol, default CSI300=000300")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    bad = [s for s in symbols if not is_allowed_a_share_symbol(s)]
    if bad:
        raise SystemExit(f"symbols not allowed by constraints (ST/北交/科创/创业 excluded): {bad}")
    cache_dir = Path(args.cache_dir)
    lake = DataLake(
        cache_dir=cache_dir,
        default_source="akshare",
        refresh=args.refresh,
    )

    data_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        df = lake.load_daily_bars(
            symbol, args.start, args.end, source="akshare", adjust="qfq"
        )
        if df.empty:
            raise SystemExit(f"empty data for {symbol}")
        data_by_symbol[symbol] = df

    engine = BacktestEngine(
        BacktestConfig(
            initial_cash=args.cash,
            max_daily_loss=0.02,
            total_friction_rate=0.001,
            min_cost_rmb=5.0,
            lot_size=100,
        )
    )
    strategy = MomentumTopNStrategy(top_n=args.top_n, lookback=args.lookback)
    result = engine.run(data_by_symbol, strategy=strategy)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    bench = lake.load_index_daily(args.benchmark, args.start, args.end)

    result.equity_curve.to_csv(out_dir / "equity.csv")
    result.fills.to_csv(out_dir / "fills.csv", index=False)
    pd.Series(result.stats).to_csv(out_dir / "stats.csv")
    pd.Series(result.diagnostics).to_csv(out_dir / "diagnostics.csv")
    bench.to_csv(out_dir / "benchmark.csv")

    if not bench.empty:
        excess_df = align_equity_and_benchmark(result.equity_curve, benchmark_close=bench["close"])
        excess_df.to_csv(out_dir / "excess.csv")
        excess_stats = summarize_excess(excess_df)
        if excess_stats:
            pd.Series(excess_stats).to_csv(out_dir / "excess_stats.csv")

    print("Backtest summary")
    for k in [
        "final_equity", "net_cagr", "gross_cagr", "net_mdd", "gross_mdd",
        "ann_vol", "sharpe", "sortino", "calmar",
        "win_rate_daily", "turnover_ratio", "total_cost", "cost_drag_pct", "trade_count",
    ]:
        if k in result.stats:
            print(f"- {k}: {result.stats[k]:.6f}")
    if not bench.empty:
        ex = summarize_excess(align_equity_and_benchmark(result.equity_curve, bench["close"]))
        for k in ["excess_ann", "excess_vol", "excess_sharpe"]:
            if k in ex:
                print(f"- {k}: {ex[k]}")
    print("Diagnostics")
    for k, v in result.diagnostics.items():
        print(f"- {k}: {v}")
    print(f"Saved: {out_dir}")


if __name__ == "__main__":
    main()
