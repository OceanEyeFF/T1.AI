"""推荐历史持久化（SQLite）。

本模块用于将“每日推荐列表”和“验证结果”落盘到 SQLite，便于后续查询与月度统计。

关键约束：
- recommendations 表唯一键： (rec_date, symbol)
- validations 表唯一键： (rec_date, validation_date, horizon)
- 写入时使用 REPLACE（INSERT OR REPLACE）处理重复记录
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, is_dataclass
from datetime import date as date_type
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from .validator import ValidationResult

_RECOMMENDATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rec_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    score REAL NOT NULL,
    rank INTEGER NOT NULL,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rec_date, symbol)
);
"""

_VALIDATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rec_date TEXT NOT NULL,
    validation_date TEXT NOT NULL,
    hit_rate REAL NOT NULL,
    ic REAL NOT NULL,
    rank_ic REAL NOT NULL,
    excess_return REAL NOT NULL,
    valid_count INTEGER NOT NULL,
    horizon INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rec_date, validation_date, horizon)
);
"""

_PIPELINE_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    status TEXT NOT NULL,
    steps_completed TEXT,
    steps_failed TEXT,
    error_messages TEXT,
    execution_time_seconds REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_date)
);
"""

_MODEL_SNAPSHOTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS model_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    model_path TEXT NOT NULL,
    model_type TEXT NOT NULL,
    train_samples INTEGER NOT NULL,
    val_ic REAL,
    trigger_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

_RECOMMENDATIONS_INDEX = "CREATE INDEX IF NOT EXISTS idx_recommendations_rec_date ON recommendations(rec_date);"
_VALIDATIONS_INDEX = "CREATE INDEX IF NOT EXISTS idx_validations_rec_date ON validations(rec_date);"
_PIPELINE_RUNS_INDEX = "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_date ON pipeline_runs(run_date);"
_MODEL_SNAPSHOTS_INDEX = "CREATE INDEX IF NOT EXISTS idx_model_snapshots_snapshot_date ON model_snapshots(snapshot_date);"


def _normalize_date(value: Any) -> str:
    """将日期统一规范化为 YYYY-MM-DD。"""
    if value is None:
        raise ValueError("日期不能为空")

    if isinstance(value, (datetime, date_type)):
        return value.strftime("%Y-%m-%d")

    s = str(value).strip()
    if not s:
        raise ValueError("日期不能为空")

    # 兼容 YYYYMMDD / YYYY-MM-DD
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")

    return datetime.fromisoformat(s).date().strftime("%Y-%m-%d")


def _json_dumps(obj: Any) -> str:
    """将任意对象转为 JSON 字符串（尽量保留中文）。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _mapping_get_first(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    """从 mapping 中按优先级取第一个非空 key 对应的值。"""
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _extract_symbol(item: Any) -> str:
    """从推荐条目中提取 symbol。"""
    if hasattr(item, "symbol"):
        return str(getattr(item, "symbol"))
    if isinstance(item, Mapping) and "symbol" in item:
        return str(item["symbol"])
    raise ValueError("推荐条目缺少 symbol 字段")


def _extract_score(item: Any) -> float:
    """从推荐条目中提取 score（兼容 predicted_return/score）。"""
    if hasattr(item, "predicted_return"):
        return float(getattr(item, "predicted_return"))
    if hasattr(item, "score"):
        return float(getattr(item, "score"))
    if isinstance(item, Mapping):
        if "predicted_return" in item:
            return float(item["predicted_return"])
        if "score" in item:
            return float(item["score"])
    raise ValueError("推荐条目缺少 predicted_return/score 字段")


def _extract_rank(item: Any, fallback_rank: int) -> int:
    """从推荐条目中提取 rank（缺失则使用 fallback_rank）。"""
    if hasattr(item, "rank"):
        try:
            return int(getattr(item, "rank"))
        except Exception as exc:  # pragma: no cover - 防御性转换
            raise ValueError("rank 字段无法转换为整数") from exc
    if isinstance(item, Mapping) and "rank" in item and item["rank"] is not None:
        try:
            return int(item["rank"])
        except Exception as exc:  # pragma: no cover - 防御性转换
            raise ValueError("rank 字段无法转换为整数") from exc
    return int(fallback_rank)


def _extract_metadata(item: Any) -> str | None:
    """将推荐条目除必填字段外的信息打包为 metadata JSON。"""
    payload: dict[str, Any] | None = None

    if is_dataclass(item):
        payload = asdict(item)
    elif hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
        try:
            raw = item.to_dict()
            payload = dict(raw) if isinstance(raw, Mapping) else None
        except Exception:  # pragma: no cover - 防御性降级
            payload = None
    elif isinstance(item, Mapping):
        payload = dict(item)

    if not payload:
        return None

    for key in ("symbol", "predicted_return", "score", "rank"):
        payload.pop(key, None)

    if not payload:
        return None

    return _json_dumps(payload)


def _parse_recommendations_input(recommendations: Any, rec_date: str | None) -> tuple[str, list[Any]]:
    """解析 save_recommendations 输入，兼容 payload/列表两种风格。"""
    if isinstance(recommendations, Mapping):
        inferred_date = rec_date or _mapping_get_first(recommendations, ("rec_date", "recommendation_date", "date"))
        if inferred_date is None:
            raise ValueError("缺少 rec_date（可通过参数传入或在 payload 中提供 date 字段）")

        items: Any = None
        for key in ("recommendations", "items", "recs"):
            if key in recommendations:
                items = recommendations[key]
                break

        if items is None:
            # 兼容 engine.save_as_json 的结构（3d/5d/10d）；优先使用 5d
            for key in ("5d", "3d", "10d"):
                if key in recommendations:
                    items = recommendations[key]
                    break

        if items is None:
            raise ValueError("payload 中未找到推荐列表字段（recommendations/items/recs/3d/5d/10d）")

        if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
            return _normalize_date(inferred_date), list(items)

        # 单条 dict 也允许
        return _normalize_date(inferred_date), [items]

    if rec_date is None:
        raise ValueError("当 recommendations 为列表时必须显式提供 rec_date")

    if recommendations is None:
        return _normalize_date(rec_date), []

    if isinstance(recommendations, Sequence) and not isinstance(recommendations, (str, bytes)):
        return _normalize_date(rec_date), list(recommendations)

    return _normalize_date(rec_date), [recommendations]


class RecommendationHistory:
    """推荐历史管理（SQLite 后端）。"""

    def __init__(self, db_path: str | Path = "data/recommendations.db") -> None:
        self.db_path = Path(db_path) if db_path != ":memory:" else Path(":memory:")
        self._conn = self._connect(self.db_path)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        """建立数据库连接，并设置常用 PRAGMA。"""
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            str(db_path),
            timeout=30.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row

        # 尽量提升并发写入体验：WAL + busy_timeout
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self) -> None:
        """初始化数据库表与索引。"""
        with self._lock, self._conn:
            self._conn.execute(_RECOMMENDATIONS_SCHEMA)
            self._conn.execute(_VALIDATIONS_SCHEMA)
            self._conn.execute(_PIPELINE_RUNS_SCHEMA)
            self._conn.execute(_MODEL_SNAPSHOTS_SCHEMA)
            self._conn.execute(_RECOMMENDATIONS_INDEX)
            self._conn.execute(_VALIDATIONS_INDEX)
            self._conn.execute(_PIPELINE_RUNS_INDEX)
            self._conn.execute(_MODEL_SNAPSHOTS_INDEX)

    def save_recommendations(self, recommendations: Any, rec_date: str | None = None) -> int:
        """批量保存推荐记录（使用 REPLACE 处理重复）。

        Args:
            recommendations: 推荐列表或包含日期字段的 payload。
            rec_date: 推荐日期（YYYY-MM-DD / YYYYMMDD），当 recommendations 为列表时必须提供。

        Returns:
            实际写入（或替换）条数。
        """
        norm_date, items = _parse_recommendations_input(recommendations, rec_date=rec_date)

        rows: list[tuple[str, str, float, int, str | None]] = []
        for idx, item in enumerate(items, start=1):
            symbol = _extract_symbol(item)
            score = _extract_score(item)
            rank = _extract_rank(item, fallback_rank=idx)
            metadata = _extract_metadata(item)
            rows.append((norm_date, symbol, float(score), int(rank), metadata))

        if not rows:
            return 0

        sql = """
        INSERT OR REPLACE INTO recommendations (rec_date, symbol, score, rank, metadata)
        VALUES (?, ?, ?, ?, ?)
        """
        with self._lock, self._conn:
            self._conn.executemany(sql, rows)
        return len(rows)

    def save_validation_results(self, rec_date: str, validation_result: ValidationResult | Mapping[str, Any], horizon: int) -> None:
        """保存验证结果（使用 REPLACE 处理重复）。"""
        if horizon <= 0:
            raise ValueError("horizon 必须为正整数")

        norm_rec_date = _normalize_date(rec_date)

        if isinstance(validation_result, ValidationResult):
            vr = validation_result
            validation_date = _normalize_date(vr.validation_date)
            hit_rate = float(vr.hit_rate)
            ic = float(vr.ic)
            rank_ic = float(vr.rank_ic)
            excess_return = float(vr.excess_return)
            valid_count = int(vr.valid_count)
        else:
            validation_date_raw = validation_result.get("validation_date")
            if not validation_date_raw:
                raise ValueError("validation_result 缺少 validation_date")
            validation_date = _normalize_date(validation_date_raw)
            hit_rate = float(validation_result["hit_rate"])
            ic = float(validation_result["ic"])
            rank_ic = float(validation_result["rank_ic"])
            excess_return = float(validation_result["excess_return"])
            valid_count = int(validation_result["valid_count"])

        sql = """
        INSERT OR REPLACE INTO validations
        (rec_date, validation_date, hit_rate, ic, rank_ic, excess_return, valid_count, horizon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._lock, self._conn:
            self._conn.execute(
                sql,
                (
                    norm_rec_date,
                    validation_date,
                    hit_rate,
                    ic,
                    rank_ic,
                    excess_return,
                    valid_count,
                    int(horizon),
                ),
            )

    def query_recommendations(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        symbol: str | None = None,
    ):
        """查询历史推荐（支持日期范围与股票代码过滤）。"""
        import pandas as pd

        clauses: list[str] = []
        params: list[Any] = []

        if start_date:
            clauses.append("rec_date >= ?")
            params.append(_normalize_date(start_date))
        if end_date:
            clauses.append("rec_date <= ?")
            params.append(_normalize_date(end_date))
        if symbol:
            clauses.append("symbol = ?")
            params.append(str(symbol))

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT rec_date, symbol, score, rank, metadata, created_at
        FROM recommendations
        {where}
        ORDER BY rec_date ASC, rank ASC, symbol ASC
        """
        with self._lock:
            return pd.read_sql_query(sql, self._conn, params=params)

    def query_validations(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        horizon: int | None = None,
    ):
        """查询验证结果（支持日期范围过滤）。"""
        import pandas as pd

        clauses: list[str] = []
        params: list[Any] = []

        if start_date:
            clauses.append("rec_date >= ?")
            params.append(_normalize_date(start_date))
        if end_date:
            clauses.append("rec_date <= ?")
            params.append(_normalize_date(end_date))
        if horizon is not None:
            clauses.append("horizon = ?")
            params.append(int(horizon))

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT rec_date, validation_date, hit_rate, ic, rank_ic, excess_return, valid_count, horizon, created_at
        FROM validations
        {where}
        ORDER BY rec_date ASC, horizon ASC
        """
        with self._lock:
            return pd.read_sql_query(sql, self._conn, params=params)

    def save_pipeline_run(self, run: Any) -> None:
        """保存一次流水线执行记录（INSERT OR REPLACE by run_date）。"""
        if run is None:
            raise ValueError("run 不能为空")

        if isinstance(run, Mapping):
            payload: Mapping[str, Any] = run
            run_date = payload.get("run_date")
            status = payload.get("status")
            steps_completed = payload.get("steps_completed")
            steps_failed = payload.get("steps_failed")
            error_messages = payload.get("error_messages")
            execution_time_seconds = payload.get("execution_time_seconds")
            created_at = payload.get("created_at")
        else:
            run_date = getattr(run, "run_date", None)
            status = getattr(run, "status", None)
            steps_completed = getattr(run, "steps_completed", None)
            steps_failed = getattr(run, "steps_failed", None)
            error_messages = getattr(run, "error_messages", None)
            execution_time_seconds = getattr(run, "execution_time_seconds", None)
            created_at = getattr(run, "created_at", None)

        norm_run_date = _normalize_date(run_date)
        if not status:
            raise ValueError("pipeline run 缺少 status")

        if created_at is None:
            sql = """
            INSERT OR REPLACE INTO pipeline_runs
            (run_date, status, steps_completed, steps_failed, error_messages, execution_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                norm_run_date,
                str(status),
                None if steps_completed is None else _json_dumps(steps_completed),
                None if steps_failed is None else _json_dumps(steps_failed),
                None if error_messages is None else _json_dumps(error_messages),
                None if execution_time_seconds is None else float(execution_time_seconds),
            )
        else:
            sql = """
            INSERT OR REPLACE INTO pipeline_runs
            (run_date, status, steps_completed, steps_failed, error_messages, execution_time_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                norm_run_date,
                str(status),
                None if steps_completed is None else _json_dumps(steps_completed),
                None if steps_failed is None else _json_dumps(steps_failed),
                None if error_messages is None else _json_dumps(error_messages),
                None if execution_time_seconds is None else float(execution_time_seconds),
                str(created_at),
            )
        with self._lock, self._conn:
            self._conn.execute(sql, params)

    def query_pipeline_runs(self, start_date: str | None = None, end_date: str | None = None):
        """查询流水线执行历史（支持日期范围过滤）。"""
        import pandas as pd

        clauses: list[str] = []
        params: list[Any] = []

        if start_date:
            clauses.append("run_date >= ?")
            params.append(_normalize_date(start_date))
        if end_date:
            clauses.append("run_date <= ?")
            params.append(_normalize_date(end_date))

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT run_date, status, steps_completed, steps_failed, error_messages, execution_time_seconds, created_at
        FROM pipeline_runs
        {where}
        ORDER BY run_date ASC
        """
        with self._lock:
            return pd.read_sql_query(sql, self._conn, params=params)

    def save_model_snapshot(
        self,
        snapshot_date: str,
        model_path: str,
        model_type: str,
        train_samples: int,
        val_ic: float | None = None,
        trigger_reason: str | None = None,
    ) -> None:
        """保存模型快照记录。"""
        norm_date = _normalize_date(snapshot_date)
        if not model_path:
            raise ValueError("model_path 不能为空")
        if not model_type:
            raise ValueError("model_type 不能为空")
        if train_samples is None:
            raise ValueError("train_samples 不能为空")

        sql = """
        INSERT INTO model_snapshots
        (snapshot_date, model_path, model_type, train_samples, val_ic, trigger_reason)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        with self._lock, self._conn:
            self._conn.execute(
                sql,
                (
                    norm_date,
                    str(model_path),
                    str(model_type),
                    int(train_samples),
                    None if val_ic is None else float(val_ic),
                    None if trigger_reason is None else str(trigger_reason),
                ),
            )

    def query_model_snapshots(self, limit: int = 10):
        """查询最近模型快照（按 snapshot_date 倒序）。"""
        import pandas as pd

        if limit <= 0:
            raise ValueError("limit 必须为正整数")

        sql = """
        SELECT snapshot_date, model_path, model_type, train_samples, val_ic, trigger_reason, created_at
        FROM model_snapshots
        ORDER BY snapshot_date DESC, id DESC
        LIMIT ?
        """
        with self._lock:
            return pd.read_sql_query(sql, self._conn, params=(int(limit),))

    def get_monthly_stats(self, year_month: str) -> dict[str, Any]:
        """获取指定月份（YYYY-MM）的汇总统计。"""
        if not isinstance(year_month, str) or len(year_month) != 7 or year_month[4] != "-":
            raise ValueError("year_month 格式必须为 YYYY-MM")

        year_str, month_str = year_month.split("-", 1)
        if not (year_str.isdigit() and month_str.isdigit()):
            raise ValueError("year_month 格式必须为 YYYY-MM")

        year = int(year_str)
        month = int(month_str)
        if month < 1 or month > 12:
            raise ValueError("year_month 中的月份必须为 01-12")

        start = date_type(year, month, 1)
        if month == 12:
            end = date_type(year + 1, 1, 1)
        else:
            end = date_type(year, month + 1, 1)

        start_s = start.strftime("%Y-%m-%d")
        # 结束日期用“下月第一天 - 1 天”，便于闭区间查询
        end_s = (end - timedelta(days=1)).strftime("%Y-%m-%d")

        sql = """
        SELECT
            AVG(hit_rate) AS avg_hit_rate,
            AVG(ic) AS avg_ic,
            AVG(rank_ic) AS avg_rank_ic,
            AVG(excess_return) AS avg_excess_return,
            COUNT(DISTINCT rec_date) AS total_recommendations
        FROM validations
        WHERE rec_date >= ? AND rec_date <= ?
        """
        with self._lock:
            row = self._conn.execute(sql, (start_s, end_s)).fetchone()

        if row is None:
            return {}

        avg_hit_rate = row["avg_hit_rate"]
        if avg_hit_rate is None:
            return {}

        return {
            "year_month": year_month,
            "avg_hit_rate": float(row["avg_hit_rate"]),
            "avg_ic": float(row["avg_ic"]),
            "avg_rank_ic": float(row["avg_rank_ic"]),
            "avg_excess_return": float(row["avg_excess_return"]),
            "total_recommendations": int(row["total_recommendations"]),
        }

    def close(self) -> None:
        """关闭数据库连接。"""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None  # type: ignore[assignment]

    def __enter__(self) -> "RecommendationHistory":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        _ = (exc_type, exc, tb)
        self.close()
