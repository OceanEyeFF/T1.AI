"""Trade-like Top-N panel 对比（3.2 月胜率分布 + 可对比面板报告）。

读取 rolling 实验报告 JSON 的 ``comparison_panel``（topn_equal_weight_excess），
产出逐月明细 + 汇总对比 MD（outputs/reports/ic_trade_panel_<tag>.md）。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _fmt(v: Any, digits: int = 4) -> str:
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    if isinstance(v, bool):
        return "pass" if v else "fail"
    return str(v)


def _panel_rows(reports: list[dict[str, Any]], source: str) -> list[str]:
    lines = ["| 报告 | 日数 | 月数 | 日均超额 | 日胜率 | 月胜率 | 最差日 | 连续负日 | 最差月 | 连续负月 | pass_gate |"]
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in reports:
        panel = r.get("comparison_panel", {}).get(source, {})
        if not panel.get("available"):
            lines.append(f"| {r['experiment_metadata']['experiment_id']} | (panel 不可用) |")
            continue
        lines.append(
            "| {name} | {days} | {months} | {excess} | {dwr} | {mwr} | {worst_d} | {neg_d} | {worst_m} | {neg_m} | {gate} |".format(
                name=r["experiment_metadata"]["experiment_id"],
                days=panel.get("day_count"),
                months=panel.get("month_count"),
                excess=_fmt(panel.get("mean_excess_return")),
                dwr=_fmt(panel.get("daily_win_rate")),
                mwr=_fmt(panel.get("monthly_win_rate")),
                worst_d=_fmt(panel.get("worst_day_excess_return")),
                neg_d=panel.get("max_consecutive_negative_days"),
                worst_m=_fmt(panel.get("worst_month")),
                neg_m=panel.get("max_consecutive_negative_months"),
                gate=_fmt(panel.get("pass_gate")),
            )
        )
    return lines


def _monthly_matrix(reports: list[dict[str, Any]], source: str) -> list[str]:
    all_months: list[str] = []
    for r in reports:
        panel = r.get("comparison_panel", {}).get(source, {})
        for m in panel.get("monthly", []):
            if m["month"] not in all_months:
                all_months.append(m["month"])
    all_months.sort()
    if not all_months:
        return ["（无逐月数据）"]

    lines = ["| 月份 | " + " | ".join(
        r["experiment_metadata"]["experiment_id"] for r in reports
    ) + " |"]
    lines.append("|---|" + "---|" * len(reports))
    for month in all_months:
        cells = [month]
        for r in reports:
            panel = r.get("comparison_panel", {}).get(source, {})
            row = next((m for m in panel.get("monthly", []) if m["month"] == month), None)
            cells.append(_fmt(row["avg_excess_return"]) if row else "—")
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trade-like Top-N panel 对比")
    parser.add_argument("--reports", nargs="+", required=True, help="报告 JSON 路径（≥2）")
    parser.add_argument("--panel-source", choices=["raw", "calibrated"], default="raw")
    parser.add_argument("--output-dir", default="outputs/reports")
    parser.add_argument("--tag", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args(argv)

    reports: list[dict[str, Any]] = []
    for p in args.reports:
        payload = json.loads(Path(p).read_text(encoding="utf-8"))
        payload["_path"] = str(p)
        reports.append(payload)

    source = args.panel_source
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ic_trade_panel_{args.tag}.md"

    lines = [
        "# Trade-like Top-N 面板对比",
        "",
        f"- panel 口径: {source}",
        f"- 报告数: {len(reports)}",
        "",
        "## 汇总",
        "",
        *_panel_rows(reports, source),
        "",
        "## 逐月平均超额收益",
        "",
        *_monthly_matrix(reports, source),
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
