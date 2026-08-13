#!/usr/bin/env python3
"""审计 IC 报告是否满足 strict daily-CS 比较前置条件。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_KEYS = ("oos_predictions_path", "oos_parquet_path", "oos_parquet")
RAW_REQUIRED_COLS = {"date", "symbol", "label_5d", "label_10d", "pred_5d", "pred_10d"}
CAL_REQUIRED_COLS = {"pred_5d_cal", "pred_10d_cal"}


def _resolve_oos_path(report_path: Path, report: dict[str, Any]) -> tuple[Path | None, str]:
    candidates: list[tuple[str, str]] = []
    for key in ROOT_KEYS:
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append((value.strip(), f"root.{key}"))

    cfg = report.get("config")
    if isinstance(cfg, dict):
        for key in ROOT_KEYS:
            value = cfg.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append((value.strip(), f"config.{key}"))

    seen: set[str] = set()
    for raw, source in candidates:
        if raw in seen:
            continue
        seen.add(raw)
        p = Path(raw)
        if p.is_absolute() and p.exists():
            return p, source
        local = (Path.cwd() / p).resolve()
        if local.exists():
            return local, source
        neighbor = (report_path.parent / p).resolve()
        if neighbor.exists():
            return neighbor, source
    return None, ""


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="审计报告 OOS parquet 覆盖率（用于 strict daily-CS 比较）")
    p.add_argument("--reports", nargs="+", required=True, help="报告 JSON 路径列表")
    p.add_argument("--output-dir", default="outputs/reports")
    p.add_argument("--tag", default=datetime.now().strftime("%Y%m%d"))
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    rows: list[dict[str, Any]] = []
    for report_path in args.reports:
        report = Path(report_path)
        data = json.loads(report.read_text(encoding="utf-8"))
        issues: list[str] = []
        oos_path, source = _resolve_oos_path(report, data)

        out: dict[str, Any] = {
            "report": report.name,
            "report_path": str(report),
            "oos_source": source if source else None,
            "oos_path": str(oos_path) if oos_path is not None else None,
            "oos_exists": bool(oos_path is not None),
            "raw_columns_ok": False,
            "calibrated_columns_ok": False,
            "row_count": 0,
            "month_count": 0,
            "months": [],
            "issues": issues,
        }

        if oos_path is None:
            issues.append("missing_oos_path")
            rows.append(out)
            continue

        df = pd.read_parquet(oos_path)
        cols = set(df.columns)
        out["raw_columns_ok"] = RAW_REQUIRED_COLS.issubset(cols)
        out["calibrated_columns_ok"] = CAL_REQUIRED_COLS.issubset(cols)
        out["row_count"] = int(len(df))

        if "date" in df.columns:
            dates = pd.to_datetime(df["date"], errors="coerce")
            months = sorted(m for m in dates.dt.to_period("M").astype(str).dropna().unique().tolist() if m != "NaT")
            out["months"] = months
            out["month_count"] = int(len(months))

        if not out["raw_columns_ok"]:
            missing_raw = sorted(list(RAW_REQUIRED_COLS - cols))
            issues.append(f"missing_raw_cols:{','.join(missing_raw)}")
        if not out["calibrated_columns_ok"]:
            missing_cal = sorted(list(CAL_REQUIRED_COLS - cols))
            issues.append(f"missing_cal_cols:{','.join(missing_cal)}")
        if out["row_count"] == 0:
            issues.append("empty_oos_rows")

        rows.append(out)

    summary = {
        "total_reports": len(rows),
        "oos_path_ready": sum(1 for r in rows if r["oos_exists"]),
        "strict_daily_cs_raw_ready": sum(
            1 for r in rows if r["oos_exists"] and r["raw_columns_ok"] and r["row_count"] > 0
        ),
        "strict_daily_cs_calibrated_ready": sum(
            1
            for r in rows
            if r["oos_exists"] and r["raw_columns_ok"] and r["calibrated_columns_ok"] and r["row_count"] > 0
        ),
    }

    payload = {"summary": summary, "results": rows}

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"ic_report_oos_coverage_{args.tag}.json"
    md_path = out_dir / f"ic_report_oos_coverage_{args.tag}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# IC 报告 OOS 覆盖率审计",
        "",
        f"- 报告总数: {summary['total_reports']}",
        f"- 有 OOS parquet 路径: {summary['oos_path_ready']}",
        f"- strict daily-CS(raw) 就绪: {summary['strict_daily_cs_raw_ready']}",
        f"- strict daily-CS(calibrated) 就绪: {summary['strict_daily_cs_calibrated_ready']}",
        "",
        "| 报告 | OOS 路径 | raw列 | cal列 | 样本行数 | 月份数 | 问题 |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        issues = ",".join(row["issues"]) if row["issues"] else "OK"
        lines.append(
            "| {report} | {oos} | {raw_ok} | {cal_ok} | {rows_cnt} | {month_cnt} | {issues} |".format(
                report=row["report"],
                oos="YES" if row["oos_exists"] else "NO",
                raw_ok="YES" if row["raw_columns_ok"] else "NO",
                cal_ok="YES" if row["calibrated_columns_ok"] else "NO",
                rows_cnt=row["row_count"],
                month_cnt=row["month_count"],
                issues=issues,
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved: {json_path}\nSaved: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
