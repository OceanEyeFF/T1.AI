from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Thread

import pandas as pd
import pytest

import ashare_lab.recommendation.history as h
from ashare_lab.recommendation import RecommendationHistory
from ashare_lab.recommendation.validator import ValidationResult


@dataclass(frozen=True)
class _DummyRec:
    """用于测试的轻量 Recommendation 替身。"""

    rank: int
    symbol: str
    predicted_return: float
    name: str = "测试"


def _get_unique_index_cols(conn, table: str) -> list[str]:
    indices = conn.execute(f"PRAGMA index_list({table});").fetchall()
    unique_names = [row[1] for row in indices if int(row[2]) == 1]
    assert unique_names, f"{table} 未找到 UNIQUE 索引"
    cols: list[str] = []
    for idx_name in unique_names:
        cols = [r[2] for r in conn.execute(f"PRAGMA index_info({idx_name});").fetchall()]
        if cols:
            break
    return cols


def test_normalize_date_variants_and_errors() -> None:
    assert h._normalize_date("20250102") == "2025-01-02"
    assert h._normalize_date("2025-01-02") == "2025-01-02"
    assert h._normalize_date(pd.Timestamp("2025-01-02")) == "2025-01-02"
    with pytest.raises(ValueError):
        h._normalize_date(None)
    with pytest.raises(ValueError):
        h._normalize_date("")
    with pytest.raises(ValueError):
        h._normalize_date("2025/01/02")


def test_internal_helpers_and_extractors() -> None:
    assert h._mapping_get_first({}, ("a", "b")) is None

    with pytest.raises(ValueError):
        h._extract_symbol({"score": 0.1})

    @dataclass(frozen=True)
    class _RecScoreObj:
        symbol: str
        score: float

    assert h._extract_score(_RecScoreObj(symbol="A", score=0.2)) == 0.2

    with pytest.raises(ValueError):
        h._extract_score({"symbol": "A"})

    class _ToDictObj:
        def to_dict(self):
            return {"symbol": "A", "predicted_return": 0.1, "note": "n"}

    assert h._extract_metadata(_ToDictObj()) == h._json_dumps({"note": "n"})


def test_db_schema_tables_and_unique_constraints(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    history = RecommendationHistory(db)
    try:
        conn = history._conn
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
        assert "recommendations" in tables
        assert "validations" in tables

        rec_cols = _get_unique_index_cols(conn, "recommendations")
        assert rec_cols == ["rec_date", "symbol"]

        val_cols = _get_unique_index_cols(conn, "validations")
        assert val_cols == ["rec_date", "validation_date", "horizon"]
    finally:
        history.close()


def test_save_recommendations_replace_and_query_filters(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    history = RecommendationHistory(db)
    try:
        recs = [
            _DummyRec(rank=1, symbol="600519", predicted_return=0.10, name="贵州茅台"),
            _DummyRec(rank=2, symbol="000001", predicted_return=0.05, name="平安银行"),
        ]
        assert history.save_recommendations(recs, rec_date="2025-01-02") == 2

        # 重复写入同一 (rec_date, symbol)，应被 REPLACE 覆盖
        recs2 = [
            {"rank": 9, "symbol": "600519", "score": 0.20, "extra": "x"},
        ]
        assert history.save_recommendations(recs2, rec_date="2025-01-02") == 1

        df_all = history.query_recommendations()
        assert set(df_all.columns) >= {"rec_date", "symbol", "score", "rank", "metadata"}
        assert len(df_all) == 2

        row = df_all[df_all["symbol"] == "600519"].iloc[0]
        assert float(row["score"]) == pytest.approx(0.20)
        assert int(row["rank"]) == 9

        # metadata 应保留 extra，且不应包含必填字段
        meta = row["metadata"]
        assert isinstance(meta, str) and meta
        meta_obj = h.json.loads(meta)
        assert meta_obj == {"extra": "x"}

        # 日期范围过滤
        df_range = history.query_recommendations(start_date="2025-01-02", end_date="2025-01-02")
        assert len(df_range) == 2
        df_empty = history.query_recommendations(start_date="2025-01-03", end_date="2025-01-03")
        assert df_empty.empty

        # 单股票过滤
        df_symbol = history.query_recommendations(symbol="000001")
        assert len(df_symbol) == 1
        assert df_symbol.iloc[0]["symbol"] == "000001"
    finally:
        history.close()


def test_save_recommendations_payload_parsing(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    history = RecommendationHistory(db)
    try:
        payload = {
            "date": "2025-01-05",
            "5d": [{"symbol": "A", "predicted_return": 0.3}],
        }
        assert history.save_recommendations(payload) == 1

        df = history.query_recommendations()
        assert len(df) == 1
        assert df.iloc[0]["rec_date"] == "2025-01-05"

        with pytest.raises(ValueError):
            history.save_recommendations([{"symbol": "A", "score": 0.1}])

        # recommendations=None 视为无写入
        assert history.save_recommendations(None, rec_date="2025-01-06") == 0
    finally:
        history.close()


def test_save_validation_results_replace_query_and_monthly_stats(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    history = RecommendationHistory(db)
    try:
        # 2025-01 月份两天验证（同一 horizon）
        history.save_validation_results(
            rec_date="2025-01-02",
            validation_result=ValidationResult(
                hit_rate=0.5,
                ic=0.1,
                rank_ic=0.2,
                excess_return=0.01,
                valid_count=10,
                validation_date="2025-01-09",
            ),
            horizon=5,
        )
        history.save_validation_results(
            rec_date="2025-01-03",
            validation_result={
                "hit_rate": 1.0,
                "ic": 0.3,
                "rank_ic": 0.4,
                "excess_return": 0.03,
                "valid_count": 8,
                "validation_date": "2025-01-10",
            },
            horizon=5,
        )

        # REPLACE 覆盖同一 (rec_date, validation_date, horizon)
        history.save_validation_results(
            rec_date="2025-01-03",
            validation_result=ValidationResult(
                hit_rate=0.0,
                ic=-0.1,
                rank_ic=-0.2,
                excess_return=-0.01,
                valid_count=7,
                validation_date="2025-01-10",
            ),
            horizon=5,
        )

        df = history.query_validations()
        assert len(df) == 2
        row = df[df["rec_date"] == "2025-01-03"].iloc[0]
        assert float(row["hit_rate"]) == 0.0
        assert int(row["valid_count"]) == 7

        df_h = history.query_validations(horizon=5, start_date="2025-01-02", end_date="2025-01-03")
        assert len(df_h) == 2
        df_none = history.query_validations(start_date="2025-02-01", end_date="2025-02-28")
        assert df_none.empty

        stats = history.get_monthly_stats("2025-01")
        assert stats["year_month"] == "2025-01"
        assert stats["total_recommendations"] == 2
        assert stats["avg_hit_rate"] == pytest.approx((0.5 + 0.0) / 2)
        assert stats["avg_ic"] == pytest.approx((0.1 + -0.1) / 2)
        assert stats["avg_rank_ic"] == pytest.approx((0.2 + -0.2) / 2)
        assert stats["avg_excess_return"] == pytest.approx((0.01 + -0.01) / 2)

        assert history.get_monthly_stats("2025-02") == {}
        with pytest.raises(ValueError):
            history.get_monthly_stats("202501")
        with pytest.raises(ValueError):
            history.get_monthly_stats("2025-13")

        with pytest.raises(ValueError):
            history.save_validation_results("2025-01-02", ValidationResult(0.0, 0.0, 0.0, 0.0, 0, "2025-01-03"), horizon=0)
        with pytest.raises(ValueError):
            history.save_validation_results(
                "2025-01-02",
                {"hit_rate": 0.0, "ic": 0.0, "rank_ic": 0.0, "excess_return": 0.0, "valid_count": 1},
                horizon=5,
            )
    finally:
        history.close()


def test_concurrent_writes_are_serialized(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    history = RecommendationHistory(db)
    try:
        def writer(i: int) -> None:
            history.save_recommendations([{"symbol": f"S{i}", "score": float(i)}], rec_date="2025-01-02")
            history.save_validation_results(
                rec_date="2025-01-02",
                validation_result=ValidationResult(
                    hit_rate=0.1 * i,
                    ic=0.0,
                    rank_ic=0.0,
                    excess_return=0.0,
                    valid_count=1,
                    validation_date="2025-01-03",
                ),
                horizon=5,
            )

        threads = [Thread(target=writer, args=(i,)) for i in range(1, 6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        df = history.query_recommendations(rec_date := "2025-01-02", end_date=rec_date)
        assert len(df) == 5
    finally:
        history.close()
        history.close()


def test_month_12_branch_and_context_manager(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    with RecommendationHistory(db) as history:
        assert history.get_monthly_stats("2025-12") == {}
        with pytest.raises(ValueError):
            history.get_monthly_stats("202A-01")

    assert history._conn is None


def test_extract_metadata_empty_payload_returns_none() -> None:
    assert h._extract_metadata(123) is None

    @dataclass(frozen=True)
    class _OnlyRequired:
        symbol: str
        predicted_return: float
        rank: int

    assert h._extract_metadata(_OnlyRequired(symbol="A", predicted_return=0.1, rank=1)) is None


def test_parse_recommendations_input_error_and_single_item_branches() -> None:
    with pytest.raises(ValueError):
        h._parse_recommendations_input({"recommendations": []}, rec_date=None)

    with pytest.raises(ValueError):
        h._parse_recommendations_input({"date": "2025-01-02"}, rec_date=None)

    rec_date, items = h._parse_recommendations_input(
        {"date": "2025-01-02", "recommendations": {"symbol": "A", "score": 0.1}},
        rec_date=None,
    )
    assert rec_date == "2025-01-02"
    assert isinstance(items, list) and len(items) == 1

    rec_date2, items2 = h._parse_recommendations_input(123, rec_date="2025-01-02")
    assert rec_date2 == "2025-01-02"
    assert items2 == [123]
