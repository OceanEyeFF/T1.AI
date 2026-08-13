"""出厂 profile 引用路径与三区对齐合同（双路 CodeReview P0/P1 修复的回归锁）。

此前：market_state profile 引用已删除的 ``data/`` 文件（开箱即崩）、
model_mtl 仍写 ``models/``/``logs/``（覆盖代码已对齐的 fallback）、
sequence profile 无法独立提供 required 参数。
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from ashare_lab.stock_pool.registry import get_stock_pool_record
from tests.support.paths import REPO_ROOT

PROFILE_ROOT = REPO_ROOT / "inputs/configs/profiles"


def _pool_resolvable(pool_id: str) -> bool:
    """stock_pool_id 必须能经真实 registry 解析（目录名≠pool_id，不能猜路径）。"""
    try:
        record = get_stock_pool_record("inputs/pools", stock_pool_id=pool_id)
        return bool(record and record.stock_pool_id)
    except (KeyError, ValueError):
        return False


def _load_toml(rel: str) -> dict:
    return tomllib.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


@pytest.mark.contract
def test_sequence_profile_is_self_contained_and_three_zone() -> None:
    cfg = _load_toml("inputs/configs/profiles/sequence_dataset_baseline.toml")[
        "build_sequence_dataset"
    ]
    # 独立可用：start/end 必须由 profile 提供（required 参数）
    assert cfg["start"] and cfg["end"]
    assert cfg["source"] == "tushare"
    assert cfg["cache_dir"] == "inputs/data/cache"
    assert str(cfg["output_dir"]).startswith("workspace/datasets")
    # 选股来源必须可解析：stock_pool_id 指向 registry 或 symbols 列表
    if cfg.get("stock_pool_id"):
        assert _pool_resolvable(cfg["stock_pool_id"]), f"stock_pool_id 不可解析: {cfg['stock_pool_id']}"
    else:
        assert cfg.get("symbols") or cfg.get("symbols_csv")


@pytest.mark.contract
def test_market_state_profile_referenced_paths_exist() -> None:
    cfg = _load_toml("inputs/configs/profiles/market_state_dataset_baseline.toml")[
        "build_sequence_dataset_market_state"
    ]
    assert cfg["source"] in ("tushare_cache", "tushare_live")
    assert cfg["cache_dir"] == "inputs/data/cache"
    assert str(cfg["output_dir"]).startswith("workspace/datasets")
    if cfg.get("stock_pool_id"):
        assert _pool_resolvable(cfg["stock_pool_id"]), f"stock_pool_id 不可解析: {cfg['stock_pool_id']}"
    else:
        assert cfg.get("symbols_csv") and (REPO_ROOT / cfg["symbols_csv"]).is_file()
    if cfg.get("include_sector_etf_features"):
        assert cfg.get("sector_etf_map_csv") and (
            REPO_ROOT / cfg["sector_etf_map_csv"]
        ).is_file(), "开启板块 ETF 特征时必须提供映射文件"
    # 历史缺陷回归锁：profile 不得再引用已删除的 data/ 旧目录
    for v in (cfg.get("symbols_csv") or "", cfg.get("sector_etf_map_csv") or ""):
        assert not str(v).startswith("data/"), f"profile 引用旧 data/ 路径: {v}"


@pytest.mark.contract
def test_model_mtl_profile_outputs_in_three_zone() -> None:
    cfg = yaml.safe_load(
        (PROFILE_ROOT / "model_mtl.toml").read_text(encoding="utf-8")
    )
    out = cfg["output"]
    assert out["model_dir"] == "workspace/checkpoints"
    assert out["log_dir"] == "workspace/runs"
    inc = cfg["incremental_training"]
    assert inc["warm_start_checkpoint"].startswith("workspace/checkpoints/")
    assert inc["save_checkpoint"].startswith("workspace/checkpoints/")


@pytest.mark.contract
def test_env_templates_three_zone() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    for legacy in ("CACHE_DIR=data/cache", "OUTPUT_DIR=output\n", "MODEL_DIR=models"):
        assert legacy not in env_example, f".env.example 仍含旧路径: {legacy}"
    assert "CACHE_DIR=inputs/data/cache" in env_example
    assert "OUTPUT_DIR=outputs" in env_example
    assert "MODEL_DIR=workspace/checkpoints" in env_example

    load_env = (REPO_ROOT / "scripts/load_env.sh").read_text(encoding="utf-8")
    assert "${OUTPUT_DIR:-outputs}" in load_env
    assert "${MODEL_DIR:-workspace/checkpoints}" in load_env
