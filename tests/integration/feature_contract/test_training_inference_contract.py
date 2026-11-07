from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from ashare_lab.dataset.preprocessing import RollingRobustScaler
from ashare_lab.features.contract import FeatureContractLoader, FeatureFactory
from ashare_lab.models.artifact_manifest import ModelArtifactError, build_model_artifact_manifest
from ashare_lab.models.transformer import create_mtl_model
from scripts.build_sequence_dataset import _compute_features
from scripts.daily_pipeline import (
    DataSourceFeatureBuilder,
    _load_config,
    _load_model,
    _transformer_architecture,
)
from tests.support.paths import REPO_ROOT


class _BarsSource:
    def __init__(self, bars: dict[str, pd.DataFrame]) -> None:
        self._bars = bars

    def fetch_daily_bars(self, symbols, start_date: str, end_date: str):
        return {symbol: self._bars.get(symbol) for symbol in symbols}


def _bars(periods: int = 140) -> pd.DataFrame:
    dates = pd.date_range("2024-01-02", periods=periods, freq="B")
    close = np.linspace(10.0, 20.0, periods) + np.sin(np.arange(periods)) * 0.2
    return pd.DataFrame(
        {
            "open": close * 0.997,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.linspace(10_000.0, 20_000.0, periods),
            "amount": np.linspace(100_000.0, 200_000.0, periods),
        },
        index=dates,
    )


def _contract_and_scaler(bars: pd.DataFrame):
    contract = FeatureContractLoader.load(
        REPO_ROOT / "inputs/configs/features/mainline_11d_v1.toml"
    )
    raw = FeatureFactory.compute(bars, contract)
    first = raw.iloc[-2 * contract.seq_len : -contract.seq_len].to_numpy(dtype=float)
    second = raw.iloc[-contract.seq_len :].to_numpy(dtype=float)
    assert np.isfinite(first).all() and np.isfinite(second).all()
    scaler = RollingRobustScaler(contract.feature_names).fit(np.stack([first, second]))
    return contract, scaler, raw


def test_dataset_builder_and_daily_inference_share_exact_feature_contract() -> None:
    bars = _bars()
    contract, scaler, expected_frame = _contract_and_scaler(bars)

    training_frame = _compute_features(bars, contract)
    assert tuple(training_frame.columns) == contract.feature_names
    assert training_frame.shape[1] == contract.input_dim

    target = (bars.index[-1] + pd.offsets.BDay(1)).strftime("%Y%m%d")
    builder = DataSourceFeatureBuilder(
        _BarsSource({"000001": bars, "000002": pd.DataFrame()}),
        feature_contract=contract,
        scaler=scaler,
    )
    built = builder.build_sequences(["000001", "000002"], target)

    assert built["symbols"] == ["000001"]
    assert tuple(training_frame.columns) == contract.feature_names
    assert tuple(built["x"].shape) == (1, contract.seq_len, contract.input_dim)
    expected = scaler.transform(
        expected_frame.tail(contract.seq_len).to_numpy(dtype=float)[None, :, :]
    )
    np.testing.assert_allclose(built["x"].numpy(), expected)
    assert "000002" not in built["symbols"]  # no zero-filled surrogate row


def _production_checkpoint(tmp_path: Path, *, input_dim: int = 11, model_family: str = "transformer") -> Path:
    profile_path = REPO_ROOT / "inputs/configs/profiles/model_mtl.toml"
    model_cfg = _load_config(profile_path)["model"]
    architecture = _transformer_architecture(model_cfg)
    contract = FeatureContractLoader.load(REPO_ROOT / model_cfg["feature_contract"])
    bars = _bars()
    _contract, scaler, _raw = _contract_and_scaler(bars)
    model = create_mtl_model(
        input_dim=input_dim,
        d_model=architecture["d_model"],
        n_layers=architecture["n_layers"],
        n_heads=architecture["n_heads"],
        d_ff=architecture["d_ff"],
        dropout=architecture["dropout"],
        max_seq_len=architecture["max_seq_len"],
        min_seq_len=architecture["min_seq_len"],
        loss_weights=tuple(architecture["loss_weights"]),
        loss_type=architecture["loss_type"],
        loss_alpha=architecture["loss_alpha"],
    )
    manifest = build_model_artifact_manifest(
        model_family=model_family,
        architecture=architecture,
        contract=contract,
        label_mode=model_cfg["label_mode"],
        preprocessing={
            "missing_value_policy": contract.missing_value_policy,
            "scaler": scaler.to_dict(),
        },
        dataset_id="test_dataset",
    )
    path = tmp_path / "model.pt"
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "manifest": manifest}, path)
    return path


def test_daily_loader_requires_matching_manifest_and_strict_state_dict(tmp_path: Path) -> None:
    profile_path = REPO_ROOT / "inputs/configs/profiles/model_mtl.toml"
    good = _production_checkpoint(tmp_path)
    model, contract, scaler = _load_model(profile_path, good)
    assert model.config.input_dim == contract.input_dim == 11
    assert tuple(scaler.feature_names) == contract.feature_names

    cross_family = _production_checkpoint(tmp_path / "cross", model_family="rolling_lstm")
    with pytest.raises(ModelArtifactError, match="model_family"):
        _load_model(profile_path, cross_family)

    wrong_dim = _production_checkpoint(tmp_path / "wrong_dim", input_dim=10)
    with pytest.raises(ModelArtifactError, match="state_dict"):
        _load_model(profile_path, wrong_dim)
