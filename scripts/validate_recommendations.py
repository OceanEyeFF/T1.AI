#!/usr/bin/env python
"""推荐结果验证脚本（第二阶段第 3 个任务）。

功能：
- 支持从 JSON/CSV 读取推荐列表；
  - JSON：支持 engine.save_as_json 输出结构（date + 3d/5d/10d）
  - CSV：支持 rank/symbol/score(or predicted_return) + 可选 date/rec_date 列
- 支持 --source 在 akshare/tushare 之间切换（默认 akshare）
- 支持 --horizon 设置验证天数（默认 5）
- 输出验证报告到控制台，并可通过 --output 保存 JSON 报告
- 可选通过 --save-to-db 写入 RecommendationHistory（推荐+验证结果）

说明：
该脚本尽量保持“轻量”：验证核心逻辑在 `ashare_lab.recommendation.validator` 中实现。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

# 与仓库内其他脚本保持一致：允许直接从源码运行。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ashare_lab.recommendation import (  # noqa: E402
    AkshareSourceAdapter,
    RecommendationHistory,
    RecommendationValidator,
    TushareSourceAdapter,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证推荐结果（命中率/IC/RankIC/超额收益）")
    parser.add_argument("--input", required=True, help="输入推荐文件路径（.json 或 .csv）")
    parser.add_argument("--source", choices=["akshare", "tushare"], default="akshare", help="数据源（默认 akshare）")
    parser.add_argument("--horizon", type=int, default=5, help="验证天数（交易日，默认 5）")
    parser.add_argument("--output", default="", help="保存 JSON 报告的路径（可选）")
    parser.add_argument("--save-to-db", action="store_true", help="是否写入 RecommendationHistory（可选）")
    parser.add_argument("--db-path", default="data/recommendations.db", help="SQLite 数据库路径（默认 data/recommendations.db）")
    return parser.parse_args(argv)


def _normalize_date(value: Any) -> str:
    """将日期统一规范化为 YYYY-MM-DD。"""
    import pandas as pd

    if value is None:
        raise ValueError("日期不能为空")

    s = str(value).strip()
    if not s:
        raise ValueError("日期不能为空")

    # 兼容 YYYYMMDD / YYYY-MM-DD
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")

    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception as exc:  # pragma: no cover - 防御性提示
        raise ValueError(f"无法解析日期: {value!r}") from exc


def _infer_date_from_path(path: Path) -> str | None:
    """尝试从文件名中推断日期（支持 YYYYMMDD / YYYY-MM-DD）。"""
    name = path.name

    # 优先匹配 YYYY-MM-DD
    m1 = re.findall(r"(20\d{2}-\d{2}-\d{2})", name)
    if m1:
        return _normalize_date(m1[-1])

    # 再匹配 YYYYMMDD
    m2 = re.findall(r"(20\d{6})", name)
    if m2:
        return _normalize_date(m2[-1])

    return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # 兼容部分 Windows 导出的 utf-8-sig
        return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_csv(path: Path) -> list[dict[str, Any]]:
    """加载 CSV 为 list[dict]，并保留原始字段以便 metadata 落库。"""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV 缺少表头（header）")
            return [dict(row) for row in reader]
    except UnicodeDecodeError:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV 缺少表头（header）")
            return [dict(row) for row in reader]


def _mapping_get_first(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _extract_rec_date_from_payload(payload: Any, input_path: Path) -> str:
    """从输入 payload 或文件名中推断推荐日期（YYYY-MM-DD）。"""
    if isinstance(payload, Mapping):
        raw = _mapping_get_first(payload, ("rec_date", "recommendation_date", "date"))
        if raw is not None:
            return _normalize_date(raw)

    inferred = _infer_date_from_path(input_path)
    if inferred is not None:
        return inferred

    raise ValueError("缺少推荐日期：请在输入中提供 date/rec_date/recommendation_date，或在文件名中包含日期")


def _coerce_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"字段 {field} 无法转换为数字: {value!r}") from exc


def _coerce_int(value: Any, field: str) -> int:
    try:
        return int(float(value))
    except Exception as exc:
        raise ValueError(f"字段 {field} 无法转换为整数: {value!r}") from exc


def _normalize_csv_rows(rows: list[dict[str, Any]], input_path: Path) -> dict[str, Any]:
    """将 CSV 行规范化为 validator/history 都能识别的 payload。"""
    if not rows:
        # 空 CSV 仍允许生成空推荐列表（后续验证结果会是全 0）
        rec_date = _infer_date_from_path(input_path)
        if rec_date is None:
            raise ValueError("CSV 为空且无法从文件名推断日期，请在文件名中包含日期或补充 date 列")
        return {"date": rec_date, "recommendations": []}

    # 优先从列中取日期；若不存在则从文件名推断
    date_values: list[str] = []
    for row in rows:
        raw = _mapping_get_first(row, ("rec_date", "recommendation_date", "date"))
        if raw not in (None, ""):
            date_values.append(_normalize_date(raw))

    if date_values:
        # 如果 CSV 中每行都有日期，要求一致
        unique = sorted(set(date_values))
        if len(unique) != 1:
            raise ValueError(f"CSV 中存在多个推荐日期: {unique}")
        rec_date = unique[0]
    else:
        inferred = _infer_date_from_path(input_path)
        if inferred is None:
            raise ValueError("CSV 缺少推荐日期列（date/rec_date/recommendation_date），且无法从文件名推断日期")
        rec_date = inferred

    recommendations: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        symbol = str(row.get("symbol") or row.get("code") or row.get("股票代码") or "").strip()
        if not symbol:
            raise ValueError(f"CSV 第 {idx} 行缺少 symbol/code 字段")
        symbol = symbol.zfill(6) if symbol.isdigit() and len(symbol) < 6 else symbol

        score_raw = row.get("predicted_return")
        score_field = "predicted_return"
        if score_raw in (None, ""):
            score_raw = row.get("score")
            score_field = "score"
        if score_raw in (None, ""):
            raise ValueError(f"CSV 第 {idx} 行缺少 score/predicted_return 字段")
        score = _coerce_float(score_raw, score_field)

        rank_raw = row.get("rank")
        rank = _coerce_int(rank_raw, "rank") if rank_raw not in (None, "") else idx

        # 保留额外字段用于 metadata（落库时会自动剔除必填字段）
        item = dict(row)
        item["symbol"] = symbol
        item["rank"] = rank
        # 统一使用 predicted_return 作为 score 字段（validator/history 均兼容）
        item.pop("score", None)
        item["predicted_return"] = score
        # 不强制移除 date 字段：history 会把它作为 metadata 过滤掉（不是必填字段也无妨）
        recommendations.append(item)

    return {"date": rec_date, "recommendations": recommendations}


def _load_recommendations(input_path: Path) -> tuple[Any, str]:
    """加载输入文件并返回（payload, rec_date）。"""
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"输入路径不是文件: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".json":
        payload = _load_json(input_path)
        rec_date = _extract_rec_date_from_payload(payload, input_path)
        # 兼容 JSON 为“纯列表”的情况：自动包一层
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, Mapping)):
            payload = {"date": rec_date, "recommendations": list(payload)}
        # 兼容 JSON 为 dict 但缺少 date 字段的情况：从文件名推断后补齐
        if isinstance(payload, Mapping):
            if _mapping_get_first(payload, ("rec_date", "recommendation_date", "date")) is None:
                payload = dict(payload)
                payload["date"] = rec_date
        return payload, rec_date

    if suffix == ".csv":
        rows = _load_csv(input_path)
        payload = _normalize_csv_rows(rows, input_path)
        rec_date = _extract_rec_date_from_payload(payload, input_path)
        return payload, rec_date

    raise ValueError(f"不支持的输入格式: {suffix}（仅支持 .json/.csv）")


def _create_data_source(source: str) -> Any:
    """根据 --source 创建数据源适配器。"""
    if source == "akshare":
        return AkshareSourceAdapter()
    if source == "tushare":
        return TushareSourceAdapter()
    raise ValueError(f"不支持的数据源: {source}")


def _result_to_dict(obj: Any) -> dict[str, Any]:
    if is_dataclass(obj):
        return dict(asdict(obj))
    if isinstance(obj, Mapping):
        return dict(obj)
    raise ValueError(f"无法序列化的对象类型: {type(obj)!r}")


def _format_console_report(report: Mapping[str, Any]) -> str:
    """将报告格式化为控制台可读文本。"""
    metrics = report.get("metrics", {}) if isinstance(report.get("metrics"), Mapping) else {}
    lines: list[str] = []
    lines.append("推荐验证报告")
    lines.append("-" * 60)
    lines.append(f"输入文件: {report.get('input', '')}")
    lines.append(f"数据源: {report.get('source', '')}")
    lines.append(f"推荐日期: {report.get('rec_date', '')}")
    lines.append(f"验证天数: {report.get('horizon', '')}")
    lines.append(f"验证日期: {report.get('validation_date', '')}")
    lines.append("-" * 60)
    lines.append(f"有效样本数: {metrics.get('valid_count', 0)}")
    lines.append(f"命中率: {metrics.get('hit_rate', 0.0):.4f}")
    lines.append(f"IC: {metrics.get('ic', 0.0):.4f}")
    lines.append(f"RankIC: {metrics.get('rank_ic', 0.0):.4f}")
    lines.append(f"超额收益: {metrics.get('excess_return', 0.0):.6f}")
    if report.get("output"):
        lines.append(f"JSON 报告已保存: {report.get('output')}")
    if report.get("saved_to_db"):
        lines.append(f"已写入数据库: {report.get('db_path')}")
    return "\n".join(lines)


def run(
    input_path: str | Path,
    source: str = "akshare",
    horizon: int = 5,
    output: str | Path | None = None,
    save_to_db: bool = False,
    db_path: str | Path = "data/recommendations.db",
) -> dict[str, Any]:
    """执行验证并返回结构化报告 dict。"""
    in_path = Path(input_path)
    payload, rec_date = _load_recommendations(in_path)

    data_source = _create_data_source(source)
    validator = RecommendationValidator(data_source=data_source)

    result = validator.validate(payload, validation_horizon=int(horizon), recommendation_date=None)
    metrics = _result_to_dict(result)

    report: dict[str, Any] = {
        "input": str(in_path),
        "source": str(source),
        "horizon": int(horizon),
        "rec_date": rec_date,
        "validation_date": metrics.get("validation_date", ""),
        "metrics": metrics,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "output": "",
        "saved_to_db": False,
        "db_path": str(db_path),
    }

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        report["output"] = str(out_path)

    if save_to_db:
        history = RecommendationHistory(db_path=db_path)
        try:
            history.save_recommendations(payload, rec_date=rec_date)
            history.save_validation_results(rec_date=rec_date, validation_result=result, horizon=int(horizon))
            report["saved_to_db"] = True
        finally:
            history.close()

    return report


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = run(
            input_path=args.input,
            source=args.source,
            horizon=args.horizon,
            output=args.output or None,
            save_to_db=bool(args.save_to_db),
            db_path=args.db_path,
        )
        print(_format_console_report(report))
        return 0
    except Exception as exc:
        source = getattr(args, "source", "akshare")
        msg = str(exc).strip() or exc.__class__.__name__
        print(f"错误: {msg}", file=sys.stderr)
        if source == "tushare":
            print("提示: 使用 TuShare 时请确保 token 可用（可通过环境变量或 TuShare 默认配置提供）", file=sys.stderr)
        # 输出调试信息便于定位（保持轻量，不做复杂日志系统）
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
