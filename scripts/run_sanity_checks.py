"""防伪门禁 Sanity Check 脚本

运行三项标准检验（Shuffle Labels / Time Reverse / Lag-1），
验证模型预测信号的有效性，输出 JSON 报告。

Usage:
    python scripts/run_sanity_checks.py \
        --recs-path runs/<exp>/recommendations.parquet \
        --price-path data/prices.parquet \
        --output runs/<exp>/sanity_report.json

    # 或直接使用预对齐的预测+标签文件
    python scripts/run_sanity_checks.py \
        --aligned-path runs/<exp>/aligned_pred_label.parquet \
        --output runs/<exp>/sanity_report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_lab.evaluation.sanity_checks import run_all_checks


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="防伪门禁 Sanity Check")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--aligned-path",
        help="预对齐的 parquet 文件，需包含 date/symbol/prediction/label 列",
    )
    group.add_argument(
        "--recs-path",
        help="推荐结果 parquet 文件，需包含 date/symbol/score 列",
    )
    group.add_argument(
        "--oos-parquet",
        help="OOS 多 horizon parquet（需含 date/symbol/pred_{h}d/label_{h}d 列）",
    )
    p.add_argument(
        "--price-path",
        help="价格数据 parquet 文件（与 --recs-path 配合使用），"
        "需包含 date/symbol/close 列",
    )
    p.add_argument("--horizon", type=int, default=5, help="前瞻天数 (默认 5)")
    p.add_argument("--method", default="pearson", choices=["pearson", "spearman"])
    p.add_argument("--shuffle-trials", type=int, default=5)
    p.add_argument("--shuffle-threshold", type=float, default=0.02)
    p.add_argument("--reverse-threshold", type=float, default=0.02)
    p.add_argument("--lag1-threshold", type=float, default=0.01)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", default=None, help="输出 JSON 路径 (默认打印到终端)")
    return p.parse_args()


def _load_aligned(path: str) -> tuple[pd.Series, pd.Series]:
    """加载预对齐的预测+标签数据"""
    df = pd.read_parquet(path)
    for col in ["date", "symbol", "prediction", "label"]:
        if col not in df.columns:
            raise ValueError(f"aligned 文件缺少列: {col}")
    df["date"] = pd.to_datetime(df["date"])
    idx = pd.MultiIndex.from_frame(df[["date", "symbol"]])
    predictions = pd.Series(df["prediction"].values, index=idx)
    labels = pd.Series(df["label"].values, index=idx)
    return predictions, labels


def _load_oos_parquet(path: str, horizon: int) -> tuple[pd.Series, pd.Series]:
    """Load OOS multi-horizon parquet with pred_{h}d / label_{h}d columns."""
    df = pd.read_parquet(path)
    pred_col, label_col = f"pred_{horizon}d", f"label_{horizon}d"
    for col in ["date", "symbol", pred_col, label_col]:
        if col not in df.columns:
            raise ValueError(f"OOS parquet 缺少列: {col}")
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=[pred_col, label_col])
    idx = pd.MultiIndex.from_frame(df[["date", "symbol"]])
    return (
        pd.Series(df[pred_col].values, index=idx),
        pd.Series(df[label_col].values, index=idx),
    )


def _load_recs_and_prices(
    recs_path: str, price_path: str, horizon: int
) -> tuple[pd.Series, pd.Series]:
    """从推荐文件和价格文件构建预测+标签"""
    recs = pd.read_parquet(recs_path)
    prices = pd.read_parquet(price_path)

    for col in ["date", "symbol", "score"]:
        if col not in recs.columns:
            raise ValueError(f"recs 文件缺少列: {col}")
    for col in ["date", "symbol", "close"]:
        if col not in prices.columns:
            raise ValueError(f"price 文件缺少列: {col}")

    recs["date"] = pd.to_datetime(recs["date"])
    prices["date"] = pd.to_datetime(prices["date"])

    # 构建前瞻收益标签
    prices = prices.sort_values(["symbol", "date"])
    prices["forward_ret"] = prices.groupby("symbol")["close"].transform(
        lambda s: s.shift(-horizon) / s - 1.0
    )
    prices_label = prices[["date", "symbol", "forward_ret"]].dropna()

    # 合并
    merged = recs.merge(prices_label, on=["date", "symbol"], how="inner")
    if merged.empty:
        raise ValueError("recs 与 prices 合并后为空，请检查日期和股票对齐")

    idx = pd.MultiIndex.from_frame(merged[["date", "symbol"]])
    predictions = pd.Series(merged["score"].values, index=idx)
    labels = pd.Series(merged["forward_ret"].values, index=idx)
    return predictions, labels


def main() -> None:
    args = _parse_args()

    if args.aligned_path:
        predictions, labels = _load_aligned(args.aligned_path)
    elif args.oos_parquet:
        predictions, labels = _load_oos_parquet(args.oos_parquet, args.horizon)
    else:
        if not args.price_path:
            raise SystemExit("使用 --recs-path 时必须同时指定 --price-path")
        predictions, labels = _load_recs_and_prices(
            args.recs_path, args.price_path, args.horizon
        )

    n_dates = predictions.index.get_level_values(0).nunique()
    n_symbols = predictions.index.get_level_values(1).nunique()
    print(f"数据加载完成: {n_dates} 个交易日, {n_symbols} 只股票, {len(predictions)} 条记录")

    report = run_all_checks(
        predictions=predictions,
        labels=labels,
        method=args.method,
        shuffle_n_trials=args.shuffle_trials,
        shuffle_threshold=args.shuffle_threshold,
        reverse_threshold=args.reverse_threshold,
        lag1_threshold=args.lag1_threshold,
        seed=args.seed,
    )

    # 打印结果
    print("\n=== Sanity Check 结果 ===")
    print(f"Baseline mean_ic: {report['baseline']['mean_ic']:.6f}")
    print(f"  ICIR: {report['baseline']['icir']:.3f}")
    print(f"  n_days: {report['baseline']['n_days']}")

    for check_name in ["shuffle_labels", "time_reverse", "lag_1"]:
        r = report[check_name]
        status = "PASS" if r["pass"] else "FAIL"
        print(f"\n[{status}] {check_name}:")
        for k, v in r.items():
            if k != "pass":
                print(f"  {k}: {v}")

    all_pass = report["all_pass"]
    print(f"\n总结: {'ALL PASS' if all_pass else 'SOME FAILED'}")

    # 输出 JSON
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # 转换 numpy 类型为 Python 原生类型
        def _convert(obj):  # noqa: ANN202
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            return obj

        clean_report = json.loads(json.dumps(report, default=_convert))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(clean_report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存: {out_path}")


if __name__ == "__main__":
    main()
