"""Unit tests for MS-R4 A1-bound DataLake factory."""

from __future__ import annotations

from pathlib import Path

from ashare_infra.lake.r4_contract import (
    R4_ADJUST_DEFAULT,
    R4_CACHE_ROOT,
    R4_PRIMARY_SOURCE,
    R4_RATE_LIMITS_CONFIG,
    R4_STOCK_POOL_ID,
    R4_STOCK_POOL_VERSION,
    load_r4_rate_limits,
    make_r4_datalake,
    r4_approved_daily_per_api,
    r4_approved_rpm,
)


def test_make_r4_datalake_defaults(tmp_path: Path) -> None:
    lake = make_r4_datalake(cache_dir=tmp_path)
    assert lake.default_source == R4_PRIMARY_SOURCE == "tushare"
    assert lake.refresh is False
    assert lake.cache_dir == tmp_path
    assert R4_ADJUST_DEFAULT == "qfq"
    assert R4_STOCK_POOL_ID == "custom_research_liquidity_quality_v1"
    assert R4_STOCK_POOL_VERSION == "1"
    assert R4_CACHE_ROOT == Path("inputs/data/cache")


def test_make_r4_datalake_refresh_override(tmp_path: Path) -> None:
    lake = make_r4_datalake(cache_dir=tmp_path, refresh=True)
    assert lake.refresh is True


def test_load_r4_rate_limits_from_repo_config() -> None:
    load_r4_rate_limits.cache_clear()
    payload = load_r4_rate_limits()
    assert payload["status"] == "approved"
    assert payload["approved_caps"]["rpm"] == 180
    assert payload["approved_caps"]["daily_api_calls_per_api"] == 80000
    assert "tushare_rate_limits.toml" in Path(payload["config_path"]).name
    assert r4_approved_rpm() == 180
    assert r4_approved_daily_per_api() == 80000


def test_load_r4_rate_limits_fallback(tmp_path: Path) -> None:
    load_r4_rate_limits.cache_clear()
    missing = tmp_path / "missing.toml"
    payload = load_r4_rate_limits(str(missing))
    assert payload["status"] == "fallback"
    assert payload["approved_caps"] == {"rpm": 180, "daily_api_calls_per_api": 80000}
    load_r4_rate_limits.cache_clear()
