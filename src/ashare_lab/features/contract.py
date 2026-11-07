"""Versioned, fail-closed feature contracts shared by training and inference.

A :class:`FeatureContract` is deliberately more specific than an ``input_dim``
setting.  It locks the feature names, ordering, construction parameters and
sequence length that give a model input its meaning.  The dimensionality is
always derived from the ordered output columns and never accepted as a second
source of truth.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import tomllib

from ashare_lab.features.base import BaseFeature
from ashare_lab.features.momentum import Return1D, Return5D, Return20D
from ashare_lab.features.price_slope import PriceSlope
from ashare_lab.features.technical import RSI, BollingerDeviation, MACDHist
from ashare_lab.features.volume import AmountChange, VolumeChange, VolumeRatio


class FeatureContractError(ValueError):
    """Raised when a feature contract or its materialized output is unsafe."""


@dataclass(frozen=True)
class FeatureSpec:
    """One ordered feature block in a :class:`FeatureContract`."""

    feature_id: str
    factory: str
    params: Mapping[str, Any]
    output_columns: tuple[str, ...]


@dataclass(frozen=True)
class FeatureContract:
    """Immutable, path-independent model-input schema."""

    contract_id: str
    version: int
    seq_len: int
    expected_input_dim: int
    missing_value_policy: str
    features: tuple[FeatureSpec, ...]
    contract_hash: str

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(column for spec in self.features for column in spec.output_columns)

    @property
    def input_dim(self) -> int:
        return len(self.feature_names)

    def assert_sequence_shape(self, shape: Sequence[int], *, context: str) -> None:
        """Reject a batch that does not exactly match this contract."""

        if len(shape) != 3:
            raise FeatureContractError(
                f"{context} must have shape [batch, seq_len, input_dim], got {tuple(shape)}"
            )
        if int(shape[1]) != self.seq_len or int(shape[2]) != self.input_dim:
            raise FeatureContractError(
                f"{context} shape mismatch: expected [batch, {self.seq_len}, {self.input_dim}], "
                f"got {tuple(shape)}"
            )

    def canonical_definition(self) -> dict[str, Any]:
        """Return the full path-free definition used for stable hashing."""

        return {
            "contract": {
                "id": self.contract_id,
                "version": self.version,
                "seq_len": self.seq_len,
                "expected_input_dim": self.expected_input_dim,
                "missing_value_policy": self.missing_value_policy,
            },
            "features": [
                {
                    "id": spec.feature_id,
                    "factory": spec.factory,
                    "params": dict(spec.params),
                    "output_columns": list(spec.output_columns),
                }
                for spec in self.features
            ],
        }

    def to_metadata(self, *, source: str | Path | None = None) -> dict[str, Any]:
        """Serialize the schema information required by dataset/model artifacts."""

        out: dict[str, Any] = {
            "feature_contract_id": self.contract_id,
            "feature_contract_hash": self.contract_hash,
            "version": self.version,
            "seq_len": self.seq_len,
            "input_dim": self.input_dim,
            "feature_names": list(self.feature_names),
            "missing_value_policy": self.missing_value_policy,
            "definition": self.canonical_definition(),
        }
        if source is not None:
            out["source"] = str(source)
        return out


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _contract_hash(definition: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(definition).encode("utf-8")).hexdigest()


def _required_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FeatureContractError(f"{context} must be a mapping")
    return value


def _required_nonempty_string(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FeatureContractError(f"{context} must be a non-empty string")
    return value.strip()


def _required_positive_int(value: Any, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FeatureContractError(f"{context} must be a positive integer")
    return int(value)


def _validate_keys(raw: Mapping[str, Any], *, allowed: set[str], context: str) -> None:
    extras = sorted(set(raw) - allowed)
    if extras:
        raise FeatureContractError(f"{context} has unsupported fields: {', '.join(extras)}")


def _build_contract(definition: Mapping[str, Any]) -> FeatureContract:
    _validate_keys(definition, allowed={"contract", "features"}, context="feature contract")
    raw_contract = _required_mapping(definition.get("contract"), context="contract")
    _validate_keys(
        raw_contract,
        allowed={"id", "version", "seq_len", "expected_input_dim", "missing_value_policy"},
        context="contract",
    )
    contract_id = _required_nonempty_string(raw_contract.get("id"), context="contract.id")
    version = _required_positive_int(raw_contract.get("version"), context="contract.version")
    seq_len = _required_positive_int(raw_contract.get("seq_len"), context="contract.seq_len")
    expected_input_dim = _required_positive_int(
        raw_contract.get("expected_input_dim"), context="contract.expected_input_dim"
    )
    missing_value_policy = _required_nonempty_string(
        raw_contract.get("missing_value_policy"), context="contract.missing_value_policy"
    )
    if missing_value_policy != "reject_nonfinite":
        raise FeatureContractError(
            "contract.missing_value_policy must be 'reject_nonfinite'; "
            "zero-imputation is not an allowed contract fallback"
        )

    raw_features = definition.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise FeatureContractError("features must be a non-empty list")

    specs: list[FeatureSpec] = []
    feature_ids: set[str] = set()
    output_columns: set[str] = set()
    for index, raw_feature in enumerate(raw_features):
        context = f"features[{index}]"
        item = _required_mapping(raw_feature, context=context)
        _validate_keys(item, allowed={"id", "factory", "params", "output_columns"}, context=context)
        feature_id = _required_nonempty_string(item.get("id"), context=f"{context}.id")
        factory = _required_nonempty_string(item.get("factory"), context=f"{context}.factory")
        if factory not in FEATURE_FACTORY_REGISTRY:
            raise FeatureContractError(f"unknown feature factory: {factory}")
        raw_params = _required_mapping(item.get("params"), context=f"{context}.params")
        raw_outputs = item.get("output_columns")
        if not isinstance(raw_outputs, list) or not raw_outputs:
            raise FeatureContractError(f"{context}.output_columns must be a non-empty list")
        outputs = tuple(
            _required_nonempty_string(column, context=f"{context}.output_columns") for column in raw_outputs
        )
        if len(set(outputs)) != len(outputs):
            raise FeatureContractError(f"{context}.output_columns contains duplicates")
        if feature_id in feature_ids:
            raise FeatureContractError(f"duplicate feature id: {feature_id}")
        duplicate_columns = sorted(output_columns.intersection(outputs))
        if duplicate_columns:
            raise FeatureContractError(f"duplicate output columns: {', '.join(duplicate_columns)}")
        feature_ids.add(feature_id)
        output_columns.update(outputs)
        specs.append(
            FeatureSpec(
                feature_id=feature_id,
                factory=factory,
                params=dict(raw_params),
                output_columns=outputs,
            )
        )

    actual_dim = sum(len(spec.output_columns) for spec in specs)
    if actual_dim != expected_input_dim:
        raise FeatureContractError(
            f"contract.expected_input_dim={expected_input_dim} does not match "
            f"the {actual_dim} configured output columns"
        )

    normalized_definition: dict[str, Any] = {
        "contract": {
            "id": contract_id,
            "version": version,
            "seq_len": seq_len,
            "expected_input_dim": expected_input_dim,
            "missing_value_policy": missing_value_policy,
        },
        "features": [
            {
                "id": spec.feature_id,
                "factory": spec.factory,
                "params": dict(spec.params),
                "output_columns": list(spec.output_columns),
            }
            for spec in specs
        ],
    }
    return FeatureContract(
        contract_id=contract_id,
        version=version,
        seq_len=seq_len,
        expected_input_dim=expected_input_dim,
        missing_value_policy=missing_value_policy,
        features=tuple(specs),
        contract_hash=_contract_hash(normalized_definition),
    )


class FeatureContractLoader:
    """Load and validate a feature contract without path-dependent identity."""

    @staticmethod
    def load(path: str | Path) -> FeatureContract:
        contract_path = Path(path)
        try:
            with contract_path.open("rb") as handle:
                raw = tomllib.load(handle)
        except FileNotFoundError as exc:
            raise FeatureContractError(f"feature contract does not exist: {contract_path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise FeatureContractError(f"invalid feature contract TOML: {contract_path}") from exc
        return _build_contract(_required_mapping(raw, context="feature contract"))

    @staticmethod
    def from_metadata(raw: Any) -> FeatureContract:
        metadata = _required_mapping(raw, context="feature_contract metadata")
        definition = _required_mapping(metadata.get("definition"), context="feature_contract.definition")
        contract = _build_contract(definition)
        expected = {
            "feature_contract_id": contract.contract_id,
            "feature_contract_hash": contract.contract_hash,
            "seq_len": contract.seq_len,
            "input_dim": contract.input_dim,
            "feature_names": list(contract.feature_names),
            "missing_value_policy": contract.missing_value_policy,
        }
        for field, expected_value in expected.items():
            if metadata.get(field) != expected_value:
                raise FeatureContractError(
                    f"feature_contract metadata mismatch for {field}: "
                    f"expected {expected_value!r}, got {metadata.get(field)!r}"
                )
        return contract

    @staticmethod
    def from_dataset_metadata(
        dataset_metadata: Any, *, expected_contract: FeatureContract | None = None
    ) -> FeatureContract:
        """Load a contract embedded in dataset metadata and optionally pin it."""

        metadata = _required_mapping(dataset_metadata, context="dataset metadata")
        contract = FeatureContractLoader.from_metadata(metadata.get("feature_contract"))
        if expected_contract is not None and contract.contract_hash != expected_contract.contract_hash:
            raise FeatureContractError(
                "dataset feature contract does not match the requested contract: "
                f"dataset={contract.contract_id}@{contract.contract_hash[:12]}, "
                f"requested={expected_contract.contract_id}@{expected_contract.contract_hash[:12]}"
            )
        return contract

    @staticmethod
    def validate_dataset_feature_layout(dataset_metadata: Any, contract: FeatureContract) -> None:
        """Ensure parquet metadata did not drift away from its embedded contract."""

        metadata = _required_mapping(dataset_metadata, context="dataset metadata")
        feature_config = _required_mapping(metadata.get("feature_config"), context="dataset feature_config")
        expected = {
            "seq_len": contract.seq_len,
            "num_features": contract.input_dim,
            "feature_names": list(contract.feature_names),
        }
        for field, expected_value in expected.items():
            if feature_config.get(field) != expected_value:
                raise FeatureContractError(
                    f"dataset feature_config mismatch for {field}: "
                    f"expected {expected_value!r}, got {feature_config.get(field)!r}"
                )


FeatureBuilder = Callable[[Mapping[str, Any]], BaseFeature]


def _construct(cls: type[BaseFeature], params: Mapping[str, Any], *, allowed: set[str]) -> BaseFeature:
    unexpected = sorted(set(params) - allowed)
    if unexpected:
        raise FeatureContractError(
            f"factory {cls.__name__} received unsupported params: {', '.join(unexpected)}"
        )
    try:
        return cls(**dict(params))  # type: ignore[call-arg]
    except (TypeError, ValueError) as exc:
        raise FeatureContractError(f"invalid params for factory {cls.__name__}: {dict(params)!r}") from exc


FEATURE_FACTORY_REGISTRY: dict[str, FeatureBuilder] = {
    "return_1d": lambda params: _construct(Return1D, params, allowed=set()),
    "return_5d": lambda params: _construct(Return5D, params, allowed=set()),
    "return_20d": lambda params: _construct(Return20D, params, allowed=set()),
    "volume_ratio": lambda params: _construct(VolumeRatio, params, allowed={"window"}),
    "volume_change": lambda params: _construct(VolumeChange, params, allowed=set()),
    "amount_change": lambda params: _construct(AmountChange, params, allowed=set()),
    "rsi": lambda params: _construct(RSI, params, allowed={"period"}),
    "macd_hist": lambda params: _construct(MACDHist, params, allowed={"short", "long", "signal"}),
    "bollinger_deviation": lambda params: _construct(
        BollingerDeviation, params, allowed={"window", "num_std"}
    ),
    "price_slope": lambda params: _construct(PriceSlope, params, allowed={"window"}),
}


class FeatureFactory:
    """Materialize only allow-listed features and verify their actual outputs."""

    @staticmethod
    def build(contract: FeatureContract) -> tuple[BaseFeature, ...]:
        built: list[BaseFeature] = []
        for spec in contract.features:
            factory = FEATURE_FACTORY_REGISTRY.get(spec.factory)
            if factory is None:
                raise FeatureContractError(f"unknown feature factory: {spec.factory}")
            feature = factory(spec.params)
            if not isinstance(feature, BaseFeature):  # defensive registry contract
                raise FeatureContractError(f"factory {spec.factory} did not produce a BaseFeature")
            if tuple(spec.output_columns) != (feature.name,):
                raise FeatureContractError(
                    f"feature {spec.feature_id} output mismatch: factory {spec.factory} produces "
                    f"{feature.name!r}, contract declares {list(spec.output_columns)!r}"
                )
            built.append(feature)
        return tuple(built)

    @classmethod
    def compute(cls, data: pd.DataFrame, contract: FeatureContract) -> pd.DataFrame:
        """Compute one exactly ordered, contract-validated feature frame."""

        frames: list[pd.DataFrame] = []
        for spec, feature in zip(contract.features, cls.build(contract), strict=True):
            result = feature.compute(data)
            if isinstance(result, pd.Series):
                if not result.index.equals(data.index):
                    raise FeatureContractError(
                        f"feature {spec.feature_id} returned an index that does not match input data"
                    )
                frame = result.to_frame(name=spec.output_columns[0])
            elif isinstance(result, pd.DataFrame):
                if not result.index.equals(data.index):
                    raise FeatureContractError(
                        f"feature {spec.feature_id} returned an index that does not match input data"
                    )
                if tuple(str(column) for column in result.columns) != spec.output_columns:
                    raise FeatureContractError(
                        f"feature {spec.feature_id} output columns mismatch: expected "
                        f"{list(spec.output_columns)!r}, got {list(result.columns)!r}"
                    )
                frame = result.copy()
                frame.columns = list(spec.output_columns)
            else:
                raise FeatureContractError(
                    f"feature {spec.feature_id} returned unsupported type {type(result).__name__}"
                )
            if tuple(frame.columns) != spec.output_columns:
                raise FeatureContractError(
                    f"feature {spec.feature_id} actual output columns do not match its contract"
                )
            frames.append(frame)

        output = pd.concat(frames, axis=1)
        if tuple(output.columns) != contract.feature_names:
            raise FeatureContractError(
                f"feature factory output order mismatch: expected {list(contract.feature_names)!r}, "
                f"got {list(output.columns)!r}"
            )
        return output


__all__ = [
    "FEATURE_FACTORY_REGISTRY",
    "FeatureContract",
    "FeatureContractError",
    "FeatureContractLoader",
    "FeatureFactory",
    "FeatureSpec",
]
