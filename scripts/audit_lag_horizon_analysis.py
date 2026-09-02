"""4.2 lag-horizon 重叠感知时效分析（daily-CS 横截面口径）。

对 OOS parquet 计算 label h 的 lag=1..h 逐档 daily-CS IC：
- lag=1 为默认 sanity check（daily 滚动窗口重叠 90%+，判别力弱）
- lag=h 为非重叠对照：预测 h 天前的信号对今天标签是否仍有效
- 正确口径：每日横截面 corr 再平均（个股内时序 corr 会混合横截面信号，禁用）

输出：workspace/runs/audit_lag_horizon.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]


def _daily_cs_lag_ic(df: pd.DataFrame, pred_col: str, label_col: str, lag: int) -> tuple[float, int]:
    shifted = df.groupby("symbol")[pred_col].shift(lag)
    tmp = pd.DataFrame({label_col: df[label_col], "p": shifted, "_d": df["date"]})
    ics: list[float] = []
    for d, g in tmp.groupby("_d", sort=False):
        m = ~g["p"].isna() & ~g[label_col].isna()
        if int(m.sum()) >= 5:
            ics.append(float(np.corrcoef(g[label_col][m], g["p"][m])[0, 1]))
    if not ics:
        return float("nan"), 0
    return float(np.nanmean(ics)), len(ics)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="lag-horizon 重叠感知时效分析")
    parser.add_argument("--oos-parquet", required=True)
    parser.add_argument("--horizons", default="5,10")
    parser.add_argument("--output", default=str(REPO_ROOT / "workspace/runs/audit_lag_horizon.json"))
    args = parser.parse_args(argv)

    df = pd.read_parquet(args.oos_parquet)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    report: dict = {"rows": [], "verdict": "PASS"}
    for h in [int(x) for x in args.horizons.split(",")]:
        pred_col, label_col = f"pred_{h}d", f"label_{h}d"
        lag1, n1 = _daily_cs_lag_ic(df, pred_col, label_col, 1)
        for lag in range(2, h + 1):
            ic, n = _daily_cs_lag_ic(df, pred_col, label_col, lag)
            report["rows"].append({"horizon": h, "lag": lag, "daily_cs_ic": round(ic, 6), "n_days": n,
                                   "drop_vs_lag1": round(lag1 - ic, 6)})
            # 非重叠 lag=h：若 IC 不衰减反而显著上升 → 异常
            if lag == h and ic > lag1 + 0.01:
                report["verdict"] = "REVIEW"
        report["rows"].append({"horizon": h, "lag": 1, "daily_cs_ic": round(lag1, 6), "n_days": n1, "drop_vs_lag1": 0.0})

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"verdict={report['verdict']} rows={len(report['rows'])}")
    for r in sorted(report["rows"], key=lambda x: (x["horizon"], x["lag"])):
        print(f"  h={r['horizon']} lag={r['lag']:2d} ic={r['daily_cs_ic']:.4f} drop={r['drop_vs_lag1']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
