"""出厂 profile 引用路径与主线数据合同。"""

from __future__ import annotations

import pytest
import tomllib

from ashare_lab.features.contract import FeatureContractLoader
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
    contract_path = REPO_ROOT / cfg["feature_contract"]
    contract = FeatureContractLoader.load(contract_path)
    assert contract.contract_id == "mainline_11d_v1"
    assert contract.seq_len == 20
    assert contract.input_dim == 11
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
def test_model_mtl_profile_is_inference_only() -> None:
    cfg = _load_toml("inputs/configs/profiles/model_mtl.toml")
    assert set(cfg) == {"model"}
    model = cfg["model"]
    assert model["family"] == "transformer"
    assert "input_dim" not in model
    contract = FeatureContractLoader.load(REPO_ROOT / model["feature_contract"])
    assert contract.input_dim == 11
    assert model["label_mode"] == "close_to_close"


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
