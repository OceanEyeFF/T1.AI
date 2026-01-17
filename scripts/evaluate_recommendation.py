#!/usr/bin/env python
"""推荐结果评估与报告生成"""

from __future__ import annotations

import argparse
import json
from datetime import date as date_type
from datetime import timedelta
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


def _validate_year_month(year_month: str) -> None:
    """验证 year_month 格式为 YYYY-MM。"""
    if not isinstance(year_month, str) or len(year_month) != 7 or year_month[4] != "-":
        raise ValueError("year_month 格式必须为 YYYY-MM（例如 2024-12）")

    year_str, month_str = year_month.split("-", 1)
    if not (year_str.isdigit() and month_str.isdigit()):
        raise ValueError("year_month 格式必须为 YYYY-MM（例如 2024-12）")

    month = int(month_str)
    if month < 1 or month > 12:
        raise ValueError("year_month 中的月份必须为 01-12")


def _month_date_range(year_month: str) -> tuple[str, str]:
    """将 YYYY-MM 转为该月起止日期（闭区间，YYYY-MM-DD）。"""
    _validate_year_month(year_month)
    year_str, month_str = year_month.split("-", 1)
    year = int(year_str)
    month = int(month_str)

    start = date_type(year, month, 1)
    if month == 12:
        end = date_type(year + 1, 1, 1)
    else:
        end = date_type(year, month + 1, 1)

    start_s = start.strftime("%Y-%m-%d")
    end_s = (end - timedelta(days=1)).strftime("%Y-%m-%d")
    return start_s, end_s


def _format_percent(value: float, digits: int = 1) -> str:
    """将 0-1 或任意小数格式化为百分比字符串。"""
    return f"{value * 100:.{digits}f}%"


def _format_float(value: float, digits: int = 2) -> str:
    """将浮点数格式化为定点小数。"""
    return f"{value:.{digits}f}"


def _render_monthly_markdown_report(
    year_month: str,
    monthly_stats: dict,
    validations: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> str:
    """生成月度 Markdown 报告内容。"""
    lines: list[str] = []
    lines.append(f"# {year_month} 推荐系统月度报告")
    lines.append("")

    lines.append("## 整体指标")
    lines.append(f"- 平均命中率: {_format_percent(float(monthly_stats['avg_hit_rate']), digits=1)}")
    lines.append(f"- 平均 IC: {_format_float(float(monthly_stats['avg_ic']), digits=2)}")
    lines.append(f"- 平均 RankIC: {_format_float(float(monthly_stats['avg_rank_ic']), digits=2)}")
    lines.append(f"- 平均超额收益: {_format_percent(float(monthly_stats['avg_excess_return']), digits=1)}")
    lines.append(f"- 推荐次数: {int(monthly_stats['total_recommendations'])}")
    lines.append("")

    lines.append("## 每日验证结果")
    lines.append("| 日期 | 命中率 | IC | RankIC | 超额收益 | 有效样本数 |")
    lines.append("|------|--------|----|---------|-----------| ----------|")
    if not validations.empty:
        for _, row in validations.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["rec_date"]),
                        _format_percent(float(row["hit_rate"]), digits=1),
                        _format_float(float(row["ic"]), digits=2),
                        _format_float(float(row["rank_ic"]), digits=2),
                        _format_percent(float(row["excess_return"]), digits=1),
                        str(int(row["valid_count"])),
                    ]
                )
                + " |"
            )
    lines.append("")

    lines.append("## 推荐详情")
    lines.append("| 日期 | 股票代码 | 得分 | 排名 |")
    lines.append("|------|----------|------|------|")
    if not recommendations.empty:
        for _, row in recommendations.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["rec_date"]),
                        str(row["symbol"]),
                        _format_float(float(row["score"]), digits=4),
                        str(int(row["rank"])),
                    ]
                )
                + " |"
            )
    lines.append("")

    return "\n".join(lines)


def _generate_monthly_report(year_month: str, db_path: str | Path) -> Path:
    """从 RecommendationHistory 读取数据并生成月度 Markdown 报告。"""
    from ashare_lab.recommendation import RecommendationHistory

    _validate_year_month(year_month)

    db_path = Path(db_path)
    if str(db_path) != ":memory:" and not db_path.exists():
        raise SystemExit(f"数据库文件不存在：{db_path}")

    start_date, end_date = _month_date_range(year_month)

    with RecommendationHistory(db_path) as history:
        monthly_stats = history.get_monthly_stats(year_month)
        if not monthly_stats:
            raise SystemExit(f"指定月份 {year_month} 无验证数据")

        validations = history.query_validations(start_date=start_date, end_date=end_date)
        # 兼容未来可能存在多个 horizon：优先使用 5；否则若只有一个 horizon 则使用它；再否则使用最小 horizon。
        if not validations.empty and "horizon" in validations.columns:
            horizons = sorted({int(x) for x in validations["horizon"].dropna().tolist()})
            if horizons:
                if 5 in horizons:
                    chosen_horizon = 5
                elif len(horizons) == 1:
                    chosen_horizon = horizons[0]
                else:
                    chosen_horizon = horizons[0]
                validations = validations[validations["horizon"] == chosen_horizon].copy()

        # 为了报告表格统一，按 rec_date 升序展示
        if not validations.empty:
            validations = validations.sort_values(["rec_date"]).reset_index(drop=True)

        recommendations = history.query_recommendations(start_date=start_date, end_date=end_date)
        if not recommendations.empty:
            recommendations = recommendations.sort_values(["rec_date", "rank", "symbol"]).reset_index(drop=True)

    markdown = _render_monthly_markdown_report(
        year_month=year_month,
        monthly_stats=monthly_stats,
        validations=validations,
        recommendations=recommendations,
    )

    output_dir = Path("output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{year_month}_report.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评估推荐榜单命中率与接近度")
    parser.add_argument("--pred-file", required=False, help="预测结果文件（csv/json），需含 predicted_return")
    parser.add_argument("--actual-file", required=False, help="实际涨跌文件（csv/json），需含 actual_return")
    parser.add_argument("--output-dir", default="data/recommendations/validation", help="报告输出目录")
    parser.add_argument("--top-n", type=int, default=10, help="Top-N 截断")
    parser.add_argument("--year-month", required=False, help="生成月度报告（YYYY-MM，例如 2024-12）")
    parser.add_argument("--db-path", default="data/recommendations.db", help="RecommendationHistory SQLite 路径")

    args = parser.parse_args(argv)

    # 参数互斥校验：--year-month 走月度统计分支；否则走 Top-K 文件评估分支
    if args.year_month:
        if args.pred_file or args.actual_file:
            parser.error("--year-month 与 --pred-file/--actual-file 互斥")
        try:
            _validate_year_month(args.year_month)
        except ValueError as exc:
            parser.error(str(exc))
        return args

    if not args.pred_file or not args.actual_file:
        parser.error("未指定 --year-month 时必须同时提供 --pred-file 与 --actual-file")

    return args


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.year_month:
        report_path = _generate_monthly_report(args.year_month, args.db_path)
        print(
            json.dumps(
                {"year_month": args.year_month, "report_path": str(report_path)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    pred_df = _load_table(Path(args.pred_file))
    actual_df = _load_table(Path(args.actual_file))

    metrics, daily = evaluate_top_k(pred_df, actual_df, top_n=args.top_n)
    paths = generate_report(metrics, daily, Path(args.output_dir), pd.to_datetime(pred_df.iloc[0]["date"]))

    print(json.dumps({"metrics": metrics, "paths": {k: str(v) for k, v in paths.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI 入口
    main()
