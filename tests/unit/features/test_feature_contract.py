from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ashare_lab.features.contract import (
    FeatureContractError,
    FeatureContractLoader,
    FeatureFactory,
)
from tests.support.paths import REPO_ROOT

CONTRACT_PATH = REPO_ROOT / "inputs/configs/features/mainline_11d_v1.toml"


def _write_contract(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_mainline_contract_derives_dimension_and_hash_is_path_independent(tmp_path: Path) -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    first = tmp_path / "one" / "contract.toml"
    second = tmp_path / "two" / "contract.toml"
    _write_contract(first, text)
    _write_contract(second, text)

    a = FeatureContractLoader.load(first)
    b = FeatureContractLoader.load(second)

    assert a.contract_id == "mainline_11d_v1"
    assert a.seq_len == 20
    assert a.input_dim == a.expected_input_dim == 11
    assert a.contract_hash == b.contract_hash
    assert a.feature_names == (
        "return_1d",
        "return_5d",
        "return_20d",
        "volume_ratio_5d",
        "volume_change",
        "amount_change",
        "rsi_14",
        "macd_hist",
        "bollinger_deviation",
        "price_slope_5d",
        "price_slope_20d",
    )


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ('factory = "return_1d"', 'factory = "untrusted_import"', "unknown feature factory"),
        ('expected_input_dim = 11', 'expected_input_dim = 12', "does not match"),
        ('id = "return_5d"', 'id = "return_1d"', "duplicate feature id"),
    ],
)
def test_loader_rejects_unsafe_or_inconsistent_contracts(
    tmp_path: Path, old: str, new: str, match: str
) -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8").replace(old, new, 1)
    path = tmp_path / "bad.toml"
    _write_contract(path, text)

    with pytest.raises(FeatureContractError, match=match):
        FeatureContractLoader.load(path)


def test_factory_rejects_actual_output_not_matching_contract(tmp_path: Path) -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8").replace(
        'output_columns = ["return_1d"]', 'output_columns = ["wrong_name"]', 1
    )
    path = tmp_path / "wrong_output.toml"
    _write_contract(path, text)
    contract = FeatureContractLoader.load(path)

    with pytest.raises(FeatureContractError, match="output mismatch"):
        FeatureFactory.build(contract)


def test_factory_produces_exact_ordered_mainline_frame() -> None:
    contract = FeatureContractLoader.load(CONTRACT_PATH)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    close = np.linspace(10.0, 20.0, len(dates)) + np.sin(np.arange(len(dates))) * 0.2
    bars = pd.DataFrame(
        {
            "open": close * 0.998,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.linspace(1_000.0, 2_000.0, len(dates)),
            "amount": np.linspace(10_000.0, 20_000.0, len(dates)),
        },
        index=dates,
    )

    features = FeatureFactory.compute(bars, contract)

    assert tuple(features.columns) == contract.feature_names
    assert features.shape == (len(bars), contract.input_dim)
    assert np.isfinite(features.tail(contract.seq_len).to_numpy()).all()


def test_semantic_feature_change_creates_a_new_contract_hash(tmp_path: Path) -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    changed = (
        text.replace('id = "mainline_11d_v1"', 'id = "mainline_11d_v2"', 1)
        .replace('id = "rsi_14"', 'id = "rsi_10"', 1)
        .replace('params = { period = 14 }', 'params = { period = 10 }', 1)
        .replace('output_columns = ["rsi_14"]', 'output_columns = ["rsi_10"]', 1)
    )
    changed_path = tmp_path / "mainline_11d_v2.toml"
    _write_contract(changed_path, changed)

    original = FeatureContractLoader.load(CONTRACT_PATH)
    modified = FeatureContractLoader.load(changed_path)

    assert modified.input_dim == original.input_dim
    assert modified.contract_hash != original.contract_hash
    assert modified.feature_names != original.feature_names
    FeatureFactory.build(modified)


def test_dataset_metadata_contract_cannot_be_reordered() -> None:
    contract = FeatureContractLoader.load(CONTRACT_PATH)
    metadata = {
        "feature_contract": contract.to_metadata(),
        "feature_config": {
            "seq_len": contract.seq_len,
            "num_features": contract.input_dim,
            "feature_names": list(contract.feature_names),
        },
    }
    loaded = FeatureContractLoader.from_dataset_metadata(metadata)
    FeatureContractLoader.validate_dataset_feature_layout(metadata, loaded)

    metadata["feature_config"]["feature_names"] = list(reversed(contract.feature_names))
    with pytest.raises(FeatureContractError, match="feature_names"):
        FeatureContractLoader.validate_dataset_feature_layout(metadata, loaded)
