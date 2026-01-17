#!/usr/bin/env python
"""推荐结果评估与报告生成"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd


def _load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    return pd.read_csv(path)


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def evaluate_top_k(
    pred_df: pd.DataFrame,
    actual_df: pd.DataFrame,
    top_n: int = 10,
) -> Tuple[dict, pd.DataFrame]:
    """计算 Top-K 命中率与接近度评分。

    pred_df 必须包含 columns: date, symbol, predicted_return
    actual_df 必须包含 columns: date, symbol, actual_return
    """
    if pred_df.empty or actual_df.empty:
        raise ValueError("pred_df and actual_df must be non-empty")

    merged = pd.merge(
        pred_df,
        actual_df,
        on=["date", "symbol"],
        how="inner",
        validate="many_to_many",
    )
    merged = merged.sort_values("predicted_return", ascending=False).head(top_n).copy()
    if merged.empty:
        raise ValueError("No overlapping rows for evaluation")

    hits = (merged["predicted_return"] > 0) & (merged["actual_return"] > 0)
    hit_rate = float(hits.mean())

    mae = float(np.mean(np.abs(merged["predicted_return"] - merged["actual_return"])))
    closeness = _clamp01(1 - mae)

    cumulative_return = float((1 + merged["actual_return"]).prod() - 1)

    metrics = {
        "hit_rate": hit_rate,
        "closeness": closeness,
        "mae": mae,
        "cumulative_return": cumulative_return,
        "n": int(len(merged)),
    }

    daily = merged.groupby("date").agg(
        hit_rate=("actual_return", lambda s: float(((s > 0) & (merged.loc[s.index, "predicted_return"] > 0)).mean())),
        closeness=("actual_return", lambda s: _clamp01(1 - float(np.mean(np.abs(merged.loc[s.index, "predicted_return"] - s))))),
        avg_return=("actual_return", "mean"),
    )
    daily = daily.reset_index()

    return metrics, daily


def generate_report(
    metrics: dict,
    daily: pd.DataFrame,
    output_dir: Path,
    date: pd.Timestamp,
) -> dict:
    """生成 CSV/JSON/HTML 报告，返回路径字典。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = date.strftime("%Y%m%d")

    summary_path = output_dir / f"summary_{date_str}.json"
    summary_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    trend_path = output_dir / f"hit_rate_trend_{date_str}.csv"
    daily.to_csv(trend_path, index=False)

    html_path = output_dir / f"report_{date_str}.html"
    html_content = (
        f"<h3>Recommendation Evaluation - {date_str}</h3>"
        f"<p>Hit Rate: {metrics['hit_rate']:.2%}</p>"
        f"<p>Closeness: {metrics['closeness']:.4f}</p>"
        f"<p>Cumulative Return: {metrics['cumulative_return']:.2%}</p>"
        f"{daily.to_html(index=False)}"
    )
    html_path.write_text(html_content, encoding="utf-8")

    return {"summary": summary_path, "trend": trend_path, "html": html_path}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评估推荐榜单命中率与接近度")
    parser.add_argument("--pred-file", required=True, help="预测结果文件（csv/json），需含 predicted_return")
    parser.add_argument("--actual-file", required=True, help="实际涨跌文件（csv/json），需含 actual_return")
    parser.add_argument("--output-dir", default="data/recommendations/validation", help="报告输出目录")
    parser.add_argument("--top-n", type=int, default=10, help="Top-N 截断")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    pred_df = _load_table(Path(args.pred_file))
    actual_df = _load_table(Path(args.actual_file))

    metrics, daily = evaluate_top_k(pred_df, actual_df, top_n=args.top_n)
    paths = generate_report(metrics, daily, Path(args.output_dir), pd.to_datetime(pred_df.iloc[0]["date"]))

    print(json.dumps({"metrics": metrics, "paths": {k: str(v) for k, v in paths.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI 入口
    main()
