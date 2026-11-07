from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from ashare_lab.dataset.preprocessing import RollingRobustScaler
from ashare_lab.features.contract import FeatureContractLoader
from ashare_lab.models.artifact_manifest import (
    ModelArtifactError,
    build_model_artifact_manifest,
    validate_model_artifact_manifest,
)
from tests.support.paths import REPO_ROOT


def _contract_and_scaler():
    contract = FeatureContractLoader.load(
        REPO_ROOT / "inputs/configs/features/mainline_11d_v1.toml"
    )
    values = np.arange(4 * contract.seq_len * contract.input_dim, dtype=np.float64).reshape(
        4, contract.seq_len, contract.input_dim
    )
    scaler = RollingRobustScaler(contract.feature_names).fit(values)
    return contract, scaler


def _manifest():
    contract, scaler = _contract_and_scaler()
    architecture = {"d_model": 32, "n_layers": 4, "seq_len": contract.seq_len}
    manifest = build_model_artifact_manifest(
        model_family="transformer",
        architecture=architecture,
        contract=contract,
        label_mode="close_to_close",
        preprocessing={
            "missing_value_policy": contract.missing_value_policy,
            "scaler": scaler.to_dict(),
        },
        dataset_id="dataset_v1",
    )
    return contract, scaler, architecture, manifest


def test_manifest_round_trip_restores_exact_scaler() -> None:
    contract, scaler, architecture, manifest = _manifest()

    restored = validate_model_artifact_manifest(
        manifest,
        expected_model_family="transformer",
        contract=contract,
        expected_architecture=architecture,
        expected_label_mode="close_to_close",
    )
    values = np.ones((1, contract.seq_len, contract.input_dim), dtype=np.float64)
    np.testing.assert_allclose(restored.transform(values), scaler.transform(values))


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda value: value.__setitem__("model_family", "rolling_lstm"), "model_family"),
        (lambda value: value.__setitem__("input_dim", 10), "input_dim"),
        (lambda value: value.__setitem__("seq_len", 30), "seq_len"),
        (lambda value: value.__setitem__("feature_names", list(reversed(value["feature_names"]))), "feature_names"),
        (lambda value: value["architecture"].__setitem__("d_model", 64), "architecture"),
    ],
)
def test_manifest_rejects_cross_model_or_schema_drift(mutate, match: str) -> None:
    contract, _scaler, architecture, manifest = _manifest()
    broken = deepcopy(manifest)
    mutate(broken)

    with pytest.raises(ModelArtifactError, match=match):
        validate_model_artifact_manifest(
            broken,
            expected_model_family="transformer",
            contract=contract,
            expected_architecture=architecture,
            expected_label_mode="close_to_close",
        )


def test_manifest_requires_contract_matching_scaler_state() -> None:
    contract, _scaler, architecture, manifest = _manifest()
    broken = deepcopy(manifest)
    broken["preprocessing"]["scaler"]["feature_names"] = list(reversed(contract.feature_names))

    with pytest.raises(ModelArtifactError, match="scaler"):
        validate_model_artifact_manifest(
            broken,
            expected_model_family="transformer",
            contract=contract,
            expected_architecture=architecture,
            expected_label_mode="close_to_close",
        )
