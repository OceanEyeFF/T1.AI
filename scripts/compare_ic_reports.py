#!/usr/bin/env python3
"""统一比较 rolling OOS 报告的全时段与月度 IC 指标。

优先使用 OOS 逐样本预测（parquet）计算 daily-CS 口径：
1) 每日横截面计算 IC/RankIC；
2) 再按时间聚合得到 mean(IC_5_10)/mean(RankIC_5_10)；
3) 月度稳定性基于 daily-CS 的月均 IC_5_10。

若报告未提供 OOS parquet（或列缺失），可回退到报告内置指标口径。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class GateThresholds:
    mean_ic_5_10: float = 0.05
    mean_rank_ic_5_10: float = 0.08
    monthly_win_rate: float = 0.60
    worst_month: float = -0.10
    max_consecutive_negative_months: int = 2
    icir_5_10: float = 0.0  # ICIR 门禁阈值（0 表示不检查）


@dataclass
class MonthlySummary:
    month_count: int
    mean: float
    median: float
    worst: float
    win_rate: float
    max_consecutive_negative_months: int


@dataclass
class DailyCsSummary:
    source_path: str
    day_count: int
    month_count: int
    mean_ic_5_10: float
    mean_rank_ic_5_10: float
    icir_5_10: float
    monthly_ic_5_10: dict[str, float]


@dataclass
class LoadedReport:
    name: str
    data: dict[str, Any]
    metrics: dict[str, Any]
    monthly_dict: dict[str, float]
    ic_5_10: float | None
    rank_ic_5_10: float | None
    source_mode: str
    daily_summary: DailyCsSummary | None


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


def _safe_pearsonr(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2 or y.size < 2:
        return 0.0
    x = x.astype(float, copy=False)
    y = y.astype(float, copy=False)
    mask = ~(np.isnan(x) | np.isnan(y))
    if int(mask.sum()) < 2:
        return 0.0
    xs = x[mask]
    ys = y[mask]
    if np.std(xs) == 0 or np.std(ys) == 0:
        return 0.0
    corr = np.corrcoef(xs, ys)[0, 1]
    return 0.0 if np.isnan(corr) else float(corr)


def _safe_spearmanr(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2 or y.size < 2:
        return 0.0
    xr = pd.Series(x).rank(method="average").to_numpy(dtype=float, copy=False)
    yr = pd.Series(y).rank(method="average").to_numpy(dtype=float, copy=False)
    return _safe_pearsonr(xr, yr)


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


def check_protocol_consistency(reports: list[dict[str, Any]]) -> tuple[bool, str]:
    """检查多份报告的评估协议是否一致。

    比对 evaluation_protocol 字段中的关键键值：
    signal_time_mode, execution_time_mode, label_mode, return_mode。
    strict 门禁下，缺少 evaluation_protocol 或关键键值会阻断比较。

    Returns:
        (is_consistent, message)
    """
    protocol_keys = ("signal_time_mode", "execution_time_mode", "label_mode", "return_mode")
    seen_protocols: list[tuple[str, dict[str, str]]] = []

    for report in reports:
        name = report.get("_report_name", "unknown")
        proto = report.get("evaluation_protocol")
        if not isinstance(proto, dict):
            return False, f"报告缺少 evaluation_protocol: {name}"
        missing_keys = [k for k in protocol_keys if not str(proto.get(k, "")).strip()]
        if missing_keys:
            return False, f"报告 evaluation_protocol 缺少关键字段: {name}: {','.join(missing_keys)}"
        extracted = {k: str(proto.get(k, "")) for k in protocol_keys}
        seen_protocols.append((name, extracted))

    if len(seen_protocols) < 2:
        return True, "协议字段完整；单报告无需跨报告一致性比较"

    reference_name, reference = seen_protocols[0]
    for name, proto in seen_protocols[1:]:
        diffs = {k: (reference[k], proto[k]) for k in protocol_keys if reference[k] != proto[k]}
        if diffs:
            diff_str = "; ".join(f"{k}: {a!r} vs {b!r}" for k, (a, b) in diffs.items())
            return False, f"协议不一致: {reference_name} vs {name}: {diff_str}"

    return True, "协议一致"


def check_icir_threshold(
    daily_summary: DailyCsSummary | None,
    threshold: float = 0.5,
) -> bool:
    """检查 ICIR 是否达到门禁阈值。

    Args:
        daily_summary: Daily-CS 汇总数据（包含 icir_5_10）
        threshold: ICIR 阈值，默认 0.5

    Returns:
        True 如果通过门禁（或无需检查）
    """
    if threshold <= 0:
        return True  # 阈值 <= 0 表示不检查
    if daily_summary is None:
        return False  # 无数据则未通过
    return daily_summary.icir_5_10 >= threshold


def passes_gate(
    mean_ic_5_10: float | None,
    mean_rank_ic_5_10: float | None,
    monthly: MonthlySummary,
    gate: GateThresholds,
    daily_summary: DailyCsSummary | None = None,
) -> bool:
    if mean_ic_5_10 is None or mean_rank_ic_5_10 is None or monthly.month_count == 0:
        return False
    base_pass = (
        mean_ic_5_10 >= gate.mean_ic_5_10
        and mean_rank_ic_5_10 >= gate.mean_rank_ic_5_10
        and monthly.win_rate >= gate.monthly_win_rate
        and monthly.worst >= gate.worst_month
        and monthly.max_consecutive_negative_months <= gate.max_consecutive_negative_months
    )
    if not base_pass:
        return False
    # ICIR 门禁（仅当阈值 > 0 时启用）
    if gate.icir_5_10 > 0:
        if not check_icir_threshold(daily_summary, gate.icir_5_10):
            return False
    return True


def _common_months(loaded: list[LoadedReport]) -> list[str]:
    common: set[str] | None = None
    for report in loaded:
        monthly_dict = report[1] if isinstance(report, tuple) else report.monthly_dict
        month_set = set(monthly_dict.keys())
        common = month_set if common is None else common & month_set
    return sorted(common or [])


def _resolve_oos_path(report_path: Path, report: dict[str, Any]) -> Path | None:
    candidates: list[str] = []
    for key in ("oos_predictions_path", "oos_parquet_path", "oos_parquet"):
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())

    cfg = report.get("config")
    if isinstance(cfg, dict):
        for key in ("oos_predictions_path", "oos_parquet_path", "oos_parquet"):
            value = cfg.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())

    seen: set[str] = set()
    for raw in candidates:
        if raw in seen:
            continue
        seen.add(raw)
        p = Path(raw)
        if p.is_absolute() and p.exists():
            return p
        local = Path.cwd() / p
        if local.exists():
            return local.resolve()
        neighbor = (report_path.parent / p).resolve()
        if neighbor.exists():
            return neighbor
    return None


def _daily_cs_from_oos(path: Path, metric_source: str) -> DailyCsSummary | None:
    df = pd.read_parquet(path)
    pred_5_col = "pred_5d"
    pred_10_col = "pred_10d"
    if metric_source == "calibrated":
        if "pred_5d_cal" in df.columns and "pred_10d_cal" in df.columns:
            pred_5_col = "pred_5d_cal"
            pred_10_col = "pred_10d_cal"
        else:
            return None

    required = {"date", "symbol", "label_5d", "label_10d", pred_5_col, pred_10_col}
    if not required.issubset(set(df.columns)):
        return None

    work = df[list(required)].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date"]).sort_values(["date", "symbol"])
    if work.empty:
        return None

    daily_rows: list[dict[str, float | pd.Timestamp]] = []
    for day, g in work.groupby("date", sort=True):
        p5 = g[pred_5_col].to_numpy(dtype=float, copy=False)
        p10 = g[pred_10_col].to_numpy(dtype=float, copy=False)
        y5 = g["label_5d"].to_numpy(dtype=float, copy=False)
        y10 = g["label_10d"].to_numpy(dtype=float, copy=False)

        ic5 = _safe_pearsonr(p5, y5)
        ic10 = _safe_pearsonr(p10, y10)
        r5 = _safe_spearmanr(p5, y5)
        r10 = _safe_spearmanr(p10, y10)

        daily_rows.append(
            {
                "date": day,
                "avg_ic_5_10": float((ic5 + ic10) / 2.0),
                "avg_rank_ic_5_10": float((r5 + r10) / 2.0),
            }
        )

    if not daily_rows:
        return None

    daily_df = pd.DataFrame(daily_rows)
    daily_df["month"] = daily_df["date"].dt.to_period("M").astype(str)
    monthly = (
        daily_df.groupby("month", sort=True)["avg_ic_5_10"]
        .mean()
        .astype(float)
        .to_dict()
    )

    # ICIR = mean(daily_ic) / std(daily_ic)
    mean_ic = float(daily_df["avg_ic_5_10"].mean())
    std_ic = float(daily_df["avg_ic_5_10"].std(ddof=1)) if len(daily_df) > 1 else 0.0
    icir = mean_ic / std_ic if std_ic > 0 else 0.0

    return DailyCsSummary(
        source_path=str(path),
        day_count=int(len(daily_df)),
        month_count=int(len(monthly)),
        mean_ic_5_10=mean_ic,
        mean_rank_ic_5_10=float(daily_df["avg_rank_ic_5_10"].mean()),
        icir_5_10=float(icir),
        monthly_ic_5_10=monthly,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="统一评估多个实验报告的全时段 + 月度 IC 口径")
    p.add_argument("--reports", nargs="+", required=True, help="报告 JSON 路径列表")
    p.add_argument("--metric-source", choices=["raw", "calibrated"], default="raw")
    p.add_argument("--monthly-source", choices=["raw", "calibrated"], default="raw")
    p.add_argument(
        "--daily-cs-mode",
        choices=["auto", "off", "required"],
        default="required",
        help="auto: 优先使用 OOS parquet 计算 daily-CS；off: 禁用；required: 无 daily-CS 则报错",
    )
    p.add_argument("--output-dir", default="output/reports")
    p.add_argument("--tag", default=datetime.now().strftime("%Y%m%d"))
    p.add_argument("--allow-empty-common-months", action="store_true", help="允许公共 OOS 月份为空（默认报错）")
    p.add_argument("--gate-mean-ic-5-10", type=float, default=0.05)
    p.add_argument("--gate-mean-rankic-5-10", type=float, default=0.08)
    p.add_argument("--gate-monthly-win-rate", type=float, default=0.60)
    p.add_argument("--gate-worst-month", type=float, default=-0.10)
    p.add_argument("--gate-max-consecutive-negative-months", type=int, default=2)
    p.add_argument("--gate-icir", type=float, default=0.0,
                   help="ICIR 门禁阈值（默认 0 表示不检查，推荐 0.5）")
    p.add_argument("--check-protocol", action="store_true",
                   help="检查报告间的 evaluation_protocol 一致性")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    gate = GateThresholds(
        mean_ic_5_10=args.gate_mean_ic_5_10,
        mean_rank_ic_5_10=args.gate_mean_rankic_5_10,
        monthly_win_rate=args.gate_monthly_win_rate,
        worst_month=args.gate_worst_month,
        max_consecutive_negative_months=args.gate_max_consecutive_negative_months,
        icir_5_10=args.gate_icir,
    )
    loaded: list[LoadedReport] = []
    daily_cs_reports = 0

    for report_path in args.reports:
        path = Path(report_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        metrics = _metric_block(data, args.metric_source)
        ic_5_10 = compute_ic_5_10(metrics)
        rank_ic_5_10 = compute_rank_ic_5_10(metrics)
        monthly = extract_monthly_series(data, args.monthly_source)
        source_mode = "report_metrics"
        daily_summary: DailyCsSummary | None = None

        if args.daily_cs_mode != "off":
            oos_path = _resolve_oos_path(path, data)
            if oos_path is not None:
                daily_summary = _daily_cs_from_oos(oos_path, args.metric_source)
                if daily_summary is not None:
                    ic_5_10 = daily_summary.mean_ic_5_10
                    rank_ic_5_10 = daily_summary.mean_rank_ic_5_10
                    monthly = daily_summary.monthly_ic_5_10
                    source_mode = "daily_cs"
                    daily_cs_reports += 1
                elif args.daily_cs_mode == "required":
                    raise ValueError(f"daily-CS 计算失败（列缺失或空数据）: {path}")
            elif args.daily_cs_mode == "required":
                raise ValueError(f"报告缺少可用 oos parquet 路径: {path}")

        loaded.append(
            LoadedReport(
                name=path.name,
                data=data,
                metrics=metrics,
                monthly_dict=monthly,
                ic_5_10=ic_5_10,
                rank_ic_5_10=rank_ic_5_10,
                source_mode=source_mode,
                daily_summary=daily_summary,
            )
        )

    # 协议一致性检查
    if args.check_protocol:
        report_dicts = []
        for loaded_report in loaded:
            report_dict = dict(loaded_report.data)
            report_dict["_report_name"] = loaded_report.name
            report_dicts.append(report_dict)
        consistent, msg = check_protocol_consistency(report_dicts)
        if not consistent:
            raise ValueError(f"协议一致性检查失败: {msg}")
        print(f"[协议检查] {msg}")

    common_months = _common_months(loaded)
    if not common_months and not args.allow_empty_common_months:
        raise ValueError("公共 OOS 月份为空，请检查报告时间区间或使用 --allow-empty-common-months")

    rows: list[dict[str, Any]] = []
    for loaded_report in loaded:
        aligned = [loaded_report.monthly_dict[m] for m in common_months]
        monthly_summary = summarize_monthly(aligned)
        rows.append(
            {
                "report": loaded_report.name,
                "metric_mode": loaded_report.source_mode,
                "available_months": sorted(loaded_report.monthly_dict.keys()),
                "missing_common_months": [m for m in common_months if m not in loaded_report.monthly_dict],
                "mean_ic_5_10": loaded_report.ic_5_10,
                "mean_rank_ic_5_10": loaded_report.rank_ic_5_10,
                "daily_cs": (
                    None
                    if loaded_report.daily_summary is None
                    else {
                        "source_path": loaded_report.daily_summary.source_path,
                        "day_count": loaded_report.daily_summary.day_count,
                        "month_count": loaded_report.daily_summary.month_count,
                        "icir_5_10": loaded_report.daily_summary.icir_5_10,
                    }
                ),
                "monthly": asdict(monthly_summary),
                "pass_gate": passes_gate(
                    loaded_report.ic_5_10,
                    loaded_report.rank_ic_5_10,
                    monthly_summary,
                    gate,
                    daily_summary=loaded_report.daily_summary,
                ),
            }
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"ic_monthly_comparison_{args.tag}.json"
    md_path = output_dir / f"ic_monthly_comparison_{args.tag}.md"

    payload = {
        "metric_source": args.metric_source,
        "monthly_source": args.monthly_source,
        "daily_cs_mode": args.daily_cs_mode,
        "daily_cs_reports": daily_cs_reports,
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
        f"- daily-CS 使用: {daily_cs_reports}/{len(rows)} 份报告",
        f"- 公共 OOS 月份数: {len(common_months)}",
        "",
        "| 报告 | 口径来源 | mean(IC_5_10) | mean(RankIC_5_10) | ICIR | 月胜率 | 最差月 | 连续负月 | 门禁 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        monthly = row["monthly"]
        mean_ic_text = "N/A" if row["mean_ic_5_10"] is None else f"{row['mean_ic_5_10']:.4f}"
        mean_rank_text = "N/A" if row["mean_rank_ic_5_10"] is None else f"{row['mean_rank_ic_5_10']:.4f}"
        icir_text = "N/A" if row["daily_cs"] is None else f"{row['daily_cs']['icir_5_10']:.3f}"
        lines.append(
            "| {report} | {source} | {ic} | {rank_ic} | {icir} | {win:.1%} | {worst:.4f} | {neg} | {gate} |".format(
                report=row["report"],
                source=row["metric_mode"],
                ic=mean_ic_text,
                rank_ic=mean_rank_text,
                icir=icir_text,
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
