"""Strict model-artifact manifests bound to a Feature Contract.

Checkpoint state dictionaries alone do not identify model family, feature
meaning, or preprocessing state.  This module makes those compatibility
requirements explicit and fail-closed before a model is loaded for inference.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ashare_lab.dataset.preprocessing import FeatureQualityError, RollingRobustScaler
from ashare_lab.features.contract import FeatureContract

MANIFEST_SCHEMA_VERSION = 1


class ModelArtifactError(ValueError):
    """Raised when a checkpoint/report cannot prove safe compatibility."""


def _json_value(value: Any, *, context: str) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ModelArtifactError(f"{context} must be JSON-serializable and finite") from exc


def _nonempty_string(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelArtifactError(f"{context} must be a non-empty string")
    return value.strip()


def _require_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelArtifactError(f"{context} must be a mapping")
    return value


def build_model_artifact_manifest(
    *,
    model_family: str,
    architecture: Mapping[str, Any],
    contract: FeatureContract,
    label_mode: str,
    preprocessing: Mapping[str, Any],
    dataset_id: str = "",
) -> dict[str, Any]:
    """Build one self-contained manifest for a trained model artifact."""

    family = _nonempty_string(model_family, context="model_family")
    if label_mode not in {"close_to_close", "next_open_to_open"}:
        raise ModelArtifactError(f"unsupported label_mode: {label_mode!r}")
    architecture_value = _json_value(dict(architecture), context="architecture")
    if not architecture_value:
        raise ModelArtifactError("architecture must not be empty")
    preprocessing_value = _json_value(dict(preprocessing), context="preprocessing")
    _validate_preprocessing(preprocessing_value, contract=contract)
    manifest: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "model_family": family,
        "architecture": architecture_value,
        "feature_contract_id": contract.contract_id,
        "feature_contract_hash": contract.contract_hash,
        "feature_names": list(contract.feature_names),
        "input_dim": contract.input_dim,
        "seq_len": contract.seq_len,
        "label_mode": label_mode,
        "preprocessing": preprocessing_value,
    }
    if dataset_id:
        manifest["dataset_id"] = str(dataset_id)
    return manifest


def _validate_preprocessing(preprocessing: Any, *, contract: FeatureContract) -> RollingRobustScaler:
    raw = _require_mapping(preprocessing, context="preprocessing")
    if raw.get("missing_value_policy") != contract.missing_value_policy:
        raise ModelArtifactError(
            "preprocessing missing_value_policy does not match feature contract: "
            f"expected {contract.missing_value_policy!r}, got {raw.get('missing_value_policy')!r}"
        )
    try:
        scaler = RollingRobustScaler.from_dict(dict(raw.get("scaler", {})))
    except FeatureQualityError as exc:
        raise ModelArtifactError("preprocessing.scaler is missing or invalid") from exc
    if tuple(scaler.feature_names) != contract.feature_names:
        raise ModelArtifactError(
            "preprocessing scaler feature order does not match feature contract: "
            f"expected {list(contract.feature_names)!r}, got {list(scaler.feature_names)!r}"
        )
    return scaler


def validate_model_artifact_manifest(
    manifest: Any,
    *,
    expected_model_family: str,
    contract: FeatureContract,
    expected_architecture: Mapping[str, Any] | None = None,
    expected_label_mode: str | None = None,
) -> RollingRobustScaler:
    """Validate every compatibility axis before loading a state dictionary.

    Returns the restored scaler only after all checks pass, so callers cannot
    accidentally re-fit or omit preprocessing during inference.
    """

    raw = _require_mapping(manifest, context="checkpoint manifest")
    if raw.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ModelArtifactError(
            f"unsupported checkpoint manifest schema: {raw.get('manifest_schema_version')!r}"
        )
    if raw.get("model_family") != expected_model_family:
        raise ModelArtifactError(
            "checkpoint model_family mismatch: "
            f"expected {expected_model_family!r}, got {raw.get('model_family')!r}"
        )
    expected_fields = {
        "feature_contract_id": contract.contract_id,
        "feature_contract_hash": contract.contract_hash,
        "feature_names": list(contract.feature_names),
        "input_dim": contract.input_dim,
        "seq_len": contract.seq_len,
    }
    for field, expected in expected_fields.items():
        if raw.get(field) != expected:
            raise ModelArtifactError(
                f"checkpoint {field} mismatch: expected {expected!r}, got {raw.get(field)!r}"
            )
    if expected_label_mode is not None and raw.get("label_mode") != expected_label_mode:
        raise ModelArtifactError(
            "checkpoint label_mode mismatch: "
            f"expected {expected_label_mode!r}, got {raw.get('label_mode')!r}"
        )
    if expected_architecture is not None:
        expected = _json_value(dict(expected_architecture), context="expected architecture")
        if raw.get("architecture") != expected:
            raise ModelArtifactError("checkpoint architecture does not match the active model profile")
    return _validate_preprocessing(raw.get("preprocessing"), contract=contract)


__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "ModelArtifactError",
    "build_model_artifact_manifest",
    "validate_model_artifact_manifest",
]
