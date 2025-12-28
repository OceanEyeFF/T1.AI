from __future__ import annotations

import numpy as np
import pandas as pd


def align_equity_and_benchmark(
    equity_curve: pd.DataFrame, benchmark_close: pd.Series
) -> pd.DataFrame:
    df = pd.DataFrame({"equity": equity_curve["equity"]}).join(
        benchmark_close.rename("benchmark_close"), how="inner"
    )
    df["equity_ret"] = df["equity"].pct_change()
    df["benchmark_ret"] = df["benchmark_close"].pct_change()
    df = df.dropna()
    df["excess_ret"] = df["equity_ret"] - df["benchmark_ret"]
    df["excess_curve"] = (1.0 + df["excess_ret"]).cumprod()
    return df


def summarize_excess(excess_df: pd.DataFrame) -> dict[str, float]:
    if excess_df.empty:
        return {}
    ex = excess_df["excess_ret"].dropna()
    if ex.empty:
        return {}
    ann_excess = float(ex.mean() * 252.0)
    vol_excess = float(ex.std(ddof=0) * np.sqrt(252.0))
    sharpe_excess = float(ann_excess / max(vol_excess, 1e-12))
    return {
        "excess_ann": ann_excess,
        "excess_vol": vol_excess,
        "excess_sharpe": sharpe_excess,
    }
