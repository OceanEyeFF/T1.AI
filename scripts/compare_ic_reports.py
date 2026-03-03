#!/usr/bin/env python3
"""统一比较 rolling OOS 报告的全时段与月度 IC 指标。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class GateThresholds:
    mean_ic_5_10: float = 0.05
    mean_rank_ic_5_10: float = 0.08
    monthly_win_rate: float = 0.60
    worst_month: float = -0.10
    max_consecutive_negative_months: int = 2


@dataclass
class MonthlySummary:
    month_count: int
    mean: float
    median: float
    worst: float
    win_rate: float
    max_consecutive_negative_months: int


def _metric_block(report: dict[str, Any], metric_source: str) -> dict[str, Any]:
    mapping = {
        "raw": ["raw_oos_metrics", "raw_test_metrics", "raw_oos_metrics_h2"],
        "calibrated": ["calibrated_oos_metrics", "calibrated_test_metrics"],
    }
    for key in mapping[metric_source]:
        block = report.get(key)
        if isinstance(block, dict):
            return block
    raise ValueError(f"report 不包含可用指标块: source={metric_source}")


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(out) else out


def compute_ic_5_10(metrics: dict[str, Any]) -> float | None:
    ic5 = _safe_float(metrics.get("ic_5d"))
    ic10 = _safe_float(metrics.get("ic_10d"))
    if ic5 is None or ic10 is None:
        return None
    return (ic5 + ic10) / 2.0


def compute_rank_ic_5_10(metrics: dict[str, Any]) -> float | None:
    r5 = _safe_float(metrics.get("rank_ic_5d"))
    r10 = _safe_float(metrics.get("rank_ic_10d"))
    if r5 is None or r10 is None:
        return None
    return (r5 + r10) / 2.0


def _monthly_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("monthly_logs")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    # Backward compatibility for walk-forward report format.
    rows = report.get("monthly_decisions")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    return []


def extract_monthly_series(report: dict[str, Any], monthly_source: str) -> dict[str, float]:
    rows = _monthly_rows(report)
    if not rows:
        return {}

    month_to_ic: dict[str, float] = {}
    for row in rows:
        month = row.get("month")
        if not isinstance(month, str):
            continue

        value: float | None = None
        if "month_avg_ic_5_10" in row:
            value = _safe_float(row.get("month_avg_ic_5_10"))
        elif "month_ic_5d" in row and "month_ic_10d" in row:
            ic5 = _safe_float(row.get("month_ic_5d"))
            ic10 = _safe_float(row.get("month_ic_10d"))
            if ic5 is not None and ic10 is not None:
                value = (ic5 + ic10) / 2.0
        elif monthly_source == "raw":
            value = _safe_float(row.get("raw_avg_ic"))
            if value is None:
                value = _safe_float(row.get("month_raw_avg_ic"))
        else:
            value = _safe_float(row.get("cal_avg_ic"))
            if value is None:
                value = _safe_float(row.get("month_cal_avg_ic"))

        if value is not None:
            month_to_ic[month] = value

    return month_to_ic


def summarize_monthly(values: list[float]) -> MonthlySummary:
    if not values:
        return MonthlySummary(0, 0.0, 0.0, 0.0, 0.0, 0)

    arr = np.array(values, dtype=float)
    negative_flags = [v < 0 for v in arr]
    max_neg = 0
    cur = 0
    for flag in negative_flags:
        if flag:
            cur += 1
            max_neg = max(max_neg, cur)
        else:
            cur = 0

    return MonthlySummary(
        month_count=int(arr.size),
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        worst=float(np.min(arr)),
        win_rate=float(np.mean(arr > 0)),
        max_consecutive_negative_months=max_neg,
    )


def passes_gate(mean_ic_5_10: float | None, mean_rank_ic_5_10: float | None, monthly: MonthlySummary, gate: GateThresholds) -> bool:
    if mean_ic_5_10 is None or mean_rank_ic_5_10 is None or monthly.month_count == 0:
        return False
    return (
        mean_ic_5_10 >= gate.mean_ic_5_10
        and mean_rank_ic_5_10 >= gate.mean_rank_ic_5_10
        and monthly.win_rate >= gate.monthly_win_rate
        and monthly.worst >= gate.worst_month
        and monthly.max_consecutive_negative_months <= gate.max_consecutive_negative_months
    )


def _common_months(loaded: list[tuple[str, dict[str, float]]]) -> list[str]:
    common: set[str] | None = None
    for _, monthly in loaded:
        month_set = set(monthly.keys())
        common = month_set if common is None else common & month_set
    return sorted(common or [])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="统一评估多个实验报告的全时段 + 月度 IC 口径")
    p.add_argument("--reports", nargs="+", required=True, help="报告 JSON 路径列表")
    p.add_argument("--metric-source", choices=["raw", "calibrated"], default="raw")
    p.add_argument("--monthly-source", choices=["raw", "calibrated"], default="raw")
    p.add_argument("--output-dir", default="output/reports")
    p.add_argument("--tag", default=datetime.now().strftime("%Y%m%d"))
    p.add_argument("--allow-empty-common-months", action="store_true", help="允许公共 OOS 月份为空（默认报错）")
    p.add_argument("--gate-mean-ic-5-10", type=float, default=0.05)
    p.add_argument("--gate-mean-rankic-5-10", type=float, default=0.08)
    p.add_argument("--gate-monthly-win-rate", type=float, default=0.60)
    p.add_argument("--gate-worst-month", type=float, default=-0.10)
    p.add_argument("--gate-max-consecutive-negative-months", type=int, default=2)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    gate = GateThresholds(
        mean_ic_5_10=args.gate_mean_ic_5_10,
        mean_rank_ic_5_10=args.gate_mean_rankic_5_10,
        monthly_win_rate=args.gate_monthly_win_rate,
        worst_month=args.gate_worst_month,
        max_consecutive_negative_months=args.gate_max_consecutive_negative_months,
    )
    loaded: list[tuple[str, dict[str, Any], dict[str, float], float | None, float | None]] = []

    for report_path in args.reports:
        path = Path(report_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        metrics = _metric_block(data, args.metric_source)
        ic_5_10 = compute_ic_5_10(metrics)
        rank_ic_5_10 = compute_rank_ic_5_10(metrics)
        monthly = extract_monthly_series(data, args.monthly_source)
        loaded.append((path.name, metrics, monthly, ic_5_10, rank_ic_5_10))

    common_months = _common_months([(name, monthly) for name, _, monthly, _, _ in loaded])
    if not common_months and not args.allow_empty_common_months:
        raise ValueError("公共 OOS 月份为空，请检查报告时间区间或使用 --allow-empty-common-months")

    rows: list[dict[str, Any]] = []
    for name, _, monthly, ic_5_10, rank_ic_5_10 in loaded:
        aligned = [monthly[m] for m in common_months]
        monthly_summary = summarize_monthly(aligned)
        rows.append(
            {
                "report": name,
                "available_months": sorted(monthly.keys()),
                "missing_common_months": [m for m in common_months if m not in monthly],
                "mean_ic_5_10": ic_5_10,
                "mean_rank_ic_5_10": rank_ic_5_10,
                "monthly": asdict(monthly_summary),
                "pass_gate": passes_gate(ic_5_10, rank_ic_5_10, monthly_summary, gate),
            }
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"ic_monthly_comparison_{args.tag}.json"
    md_path = output_dir / f"ic_monthly_comparison_{args.tag}.md"

    payload = {
        "metric_source": args.metric_source,
        "monthly_source": args.monthly_source,
        "common_months": common_months,
        "gate": asdict(gate),
        "results": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# IC 统一评估比较",
        "",
        f"- 指标口径: {args.metric_source}",
        f"- 月度口径: {args.monthly_source}",
        f"- 公共 OOS 月份数: {len(common_months)}",
        "",
        "| 报告 | mean(IC_5_10) | mean(RankIC_5_10) | 月胜率 | 最差月 | 连续负月 | 门禁 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        monthly = row["monthly"]
        mean_ic_text = "N/A" if row["mean_ic_5_10"] is None else f"{row['mean_ic_5_10']:.4f}"
        mean_rank_text = "N/A" if row["mean_rank_ic_5_10"] is None else f"{row['mean_rank_ic_5_10']:.4f}"
        lines.append(
            "| {report} | {ic} | {rank_ic} | {win:.1%} | {worst:.4f} | {neg} | {gate} |".format(
                report=row["report"],
                ic=mean_ic_text,
                rank_ic=mean_rank_text,
                win=monthly["win_rate"],
                worst=monthly["worst"],
                neg=monthly["max_consecutive_negative_months"],
                gate="PASS" if row["pass_gate"] else "FAIL",
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved: {json_path}\nSaved: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
