"""新 TuShare 指数日线链路的行为合同测试。

覆盖双路 CodeReview 指出的 P0/P1 缺口：
- ``_to_index_ts_code`` 深市/沪市映射矩阵
- ``_normalize_index_daily`` 字段归一化契约（rename/sort/coerce/空帧）
- ``fetch_index_daily`` 真实调用契约（token 优先级、限流、API 参数）——mock tushare 客户端
- 缺 token 错误路径（不得创建客户端、不得触发限流）
- 缓存 refresh 绕过、空结果不写缓存、CSV round-trip、文件名按 ts_code 规范化
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

import ashare_infra.data.index_source as idx_src
from ashare_infra.data import tushare_rate_limit


def _normalized_frame(dates: list[str], closes: list[float]) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.1 for c in closes],
            "low": [c - 0.1 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
            "amount": [1000.0] * len(closes),
        },
        index=pd.to_datetime(dates),
    )
    df.index.name = "date"
    return df


# ---------------------------------------------------------------- 映射矩阵

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("000300", "000300.SH"),  # 沪市默认
        ("000905", "000905.SH"),
        ("399006", "399006.SZ"),  # 39 前缀 → 深市（创业板指）
        ("399001", "399001.SZ"),
        (" 000300 ", "000300.SH"),  # strip
        ("000300.SH", "000300.SH"),  # ts_code 直通
        ("399006.sz", "399006.SZ"),  # 小写后缀 → 大写
    ],
)
def test_to_index_ts_code_mapping(symbol: str, expected: str) -> None:
    assert idx_src._to_index_ts_code(symbol) == expected


# ---------------------------------------------------------------- 归一化契约

@pytest.mark.parametrize("empty", [pd.DataFrame(), None])
def test_normalize_empty_keeps_field_columns(empty: pd.DataFrame | None) -> None:
    out = idx_src._normalize_index_daily(empty)
    assert list(out.columns) == list(idx_src._INDEX_FIELDS)
    assert out.empty


def test_normalize_renames_sorts_and_coerces() -> None:
    raw = pd.DataFrame(
        {
            "trade_date": ["20240103", "20240102"],  # TuShare 常见降序
            "open": ["1", "2"],
            "high": ["1.1", "2.1"],
            "low": ["0.9", "1.9"],
            "close": ["1.05", "2.05"],
            "vol": ["100", "200"],
            "amount": ["1000.0", "2000.0"],
        }
    )
    out = idx_src._normalize_index_daily(raw)
    assert out.index.name == "date"
    assert list(out.index) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]  # sort_index
    assert out["volume"].tolist() == [200, 100]  # vol→volume 且数值化（升序后）
    assert out["amount"].dtype.kind == "f"  # coerce 生效
    assert out["close"].tolist() == [2.05, 1.05]


def test_normalize_invalid_numeric_coerces_to_nan() -> None:
    raw = pd.DataFrame(
        {"trade_date": ["20240102"], "open": ["bad"], "close": ["1.0"]}
    )
    out = idx_src._normalize_index_daily(raw)
    assert pd.isna(out["open"].iloc[0])
    assert float(out["close"].iloc[0]) == 1.0


# ---------------------------------------------------------------- fetch 契约

def _install_fake_tushare(monkeypatch: pytest.MonkeyPatch, raw: pd.DataFrame) -> dict:
    seen: dict = {}

    class FakePro:
        def index_daily(self, **kwargs):
            seen["kwargs"] = kwargs
            return raw

    def fake_pro_api(token: str):
        seen["token"] = token
        return FakePro()

    monkeypatch.setitem(sys.modules, "tushare", SimpleNamespace(pro_api=fake_pro_api))
    return seen


@pytest.mark.parametrize(
    ("request_token", "env_token", "expected_token"),
    [
        ("argument-token", "environment-token", "argument-token"),  # 显式 token 优先
        (None, "environment-token", "environment-token"),  # env 回退
    ],
)
def test_fetch_index_daily_token_priority_and_api_contract(
    monkeypatch: pytest.MonkeyPatch,
    request_token: str | None,
    env_token: str,
    expected_token: str,
) -> None:
    raw = pd.DataFrame(
        {
            "trade_date": ["20240202", "20240201"],
            "open": ["2", "1"],
            "high": ["3", "2"],
            "low": ["1", "0"],
            "close": ["2.5", "1.5"],
            "vol": ["200", "100"],
            "amount": ["2000", "1000"],
        }
    )
    seen = _install_fake_tushare(monkeypatch, raw)
    acquired: list[str] = []
    monkeypatch.setattr(tushare_rate_limit, "acquire_tushare_call", lambda api: acquired.append(api))
    monkeypatch.setenv("TUSHARE_TOKEN", env_token)

    out = idx_src.fetch_index_daily(
        idx_src.IndexDailyRequest("399001", "20240201", "20240202", token=request_token)
    )

    assert seen["token"] == expected_token
    assert acquired == ["index_daily"]
    assert seen["kwargs"] == {
        "ts_code": "399001.SZ",
        "start_date": "20240201",
        "end_date": "20240202",
    }
    assert list(out.columns) == list(idx_src._INDEX_FIELDS)
    assert list(out.index) == [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-02-02")]
    assert float(out.iloc[0]["volume"]) == 100.0


def test_fetch_index_daily_missing_token_raises_without_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[str] = []

    def fail_pro_api(token: str):
        created.append(token)
        pytest.fail("缺 token 时不得创建客户端")

    monkeypatch.setitem(sys.modules, "tushare", SimpleNamespace(pro_api=fail_pro_api))
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    acquired: list[str] = []
    monkeypatch.setattr(tushare_rate_limit, "acquire_tushare_call", lambda api: acquired.append(api))

    with pytest.raises(ValueError, match="TUSHARE_TOKEN not found"):
        idx_src.fetch_index_daily(idx_src.IndexDailyRequest("000300", "20240101", "20240102"))

    assert created == []
    assert acquired == []


# ---------------------------------------------------------------- 缓存行为

def test_refresh_bypasses_existing_cache_and_replaces(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    req = idx_src.IndexDailyRequest("000300", "20240101", "20240103")
    cache_file = tmp_path / "index_000300.SH_daily_20240101_20240103.csv"
    _normalized_frame(["2024-01-02"], [1.0]).reset_index().to_csv(cache_file, index=False)

    calls: list[idx_src.IndexDailyRequest] = []
    fresh = _normalized_frame(["2024-01-03"], [2.0])

    def fake_fetch(request: idx_src.IndexDailyRequest) -> pd.DataFrame:
        calls.append(request)
        return fresh.copy()

    monkeypatch.setattr(idx_src, "fetch_index_daily", fake_fetch)
    out = idx_src.load_or_fetch_index_daily(req, tmp_path, refresh=True)

    assert calls == [req]
    assert float(out.iloc[0]["close"]) == 2.0

    # 二次读取必须命中缓存（round-trip 后列/索引与写入一致）
    monkeypatch.setattr(idx_src, "fetch_index_daily", lambda _: pytest.fail("round-trip must hit cache"))
    cached = idx_src.load_or_fetch_index_daily(req, tmp_path)
    pd.testing.assert_frame_equal(cached, fresh, check_freq=False)


def test_empty_fetch_writes_no_cache(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    req = idx_src.IndexDailyRequest("000300", "20240101", "20240103")
    monkeypatch.setattr(
        idx_src,
        "fetch_index_daily",
        lambda _: pd.DataFrame(columns=list(idx_src._INDEX_FIELDS)),
    )

    out = idx_src.load_or_fetch_index_daily(req, tmp_path, refresh=True)

    assert out.empty
    assert list(tmp_path.glob("*.csv")) == []


def test_cache_filename_normalized_by_ts_code(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """bare 代码与 ts_code 形式共用同一缓存文件（防缓存分裂）。"""
    monkeypatch.setattr(
        idx_src, "fetch_index_daily", lambda _: _normalized_frame(["2024-01-02"], [1.0])
    )
    bare = idx_src.IndexDailyRequest("000300", "20240101", "20240102")
    idx_src.load_or_fetch_index_daily(bare, tmp_path)

    files = [p.name for p in tmp_path.glob("*.csv")]
    assert files == ["index_000300.SH_daily_20240101_20240102.csv"]

    # ts_code 形式命中同一文件，不触发二次 fetch
    monkeypatch.setattr(idx_src, "fetch_index_daily", lambda _: pytest.fail("must hit cache"))
    ts_code_req = idx_src.IndexDailyRequest("000300.SH", "20240101", "20240102")
    df = idx_src.load_or_fetch_index_daily(ts_code_req, tmp_path)
    assert len(df) == 1
