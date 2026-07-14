"""Minimal stock-pool registry loader / validator / exporter."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .types import StockPoolRecord

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <=3.10 fallback
    import tomli as tomllib

REQUIRED_FIELDS = (
    "stock_pool_id",
    "stock_pool_version",
    "pool_family",
    "pool_label",
    "construction_method",
    "base_universe",
    "symbols_source",
    "symbols_count",
    "rebalance_frequency",
    "effective_start",
    "effective_end",
    "is_default",
    "is_research_only",
    "owner",
    "notes",
)


def _load_toml_mapping(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    payload = tomllib.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"stock pool registry root must be a mapping: {file_path}")
    return dict(payload)


def _expected_pool_family(stock_pool_id: str) -> str:
    if stock_pool_id == "csi300":
        return "csi300"
    if stock_pool_id.startswith("sector_single_"):
        return "sector_single"
    if stock_pool_id.startswith("sector_corr_"):
        return "sector_corr"
    if stock_pool_id.startswith("sector_anti_corr_"):
        return "sector_anti_corr"
    if stock_pool_id.startswith("custom_"):
        return "custom"
    raise ValueError(f"unsupported stock_pool_id family: {stock_pool_id}")


def _validate_record(payload: dict[str, Any], path: Path) -> StockPoolRecord:
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"missing required stock pool fields in {path}: {missing}")

    stock_pool_id = str(payload["stock_pool_id"]).strip()
    pool_family = str(payload["pool_family"]).strip()
    expected_family = _expected_pool_family(stock_pool_id)
    if pool_family != expected_family:
        raise ValueError(
            f"pool_family mismatch in {path}: expected {expected_family}, got {pool_family}"
        )

    symbols_count = int(payload["symbols_count"])
    if symbols_count <= 0:
        raise ValueError(f"symbols_count must be > 0 in {path}")

    record = StockPoolRecord(
        stock_pool_id=stock_pool_id,
        stock_pool_version=str(payload["stock_pool_version"]).strip(),
        pool_family=pool_family,
        pool_label=str(payload["pool_label"]).strip(),
        construction_method=str(payload["construction_method"]).strip(),
        base_universe=str(payload["base_universe"]).strip(),
        symbols_source=str(payload["symbols_source"]).strip(),
        symbols_count=symbols_count,
        rebalance_frequency=str(payload["rebalance_frequency"]).strip(),
        effective_start=str(payload["effective_start"]).strip(),
        effective_end=str(payload["effective_end"]).strip(),
        is_default=bool(payload["is_default"]),
        is_research_only=bool(payload["is_research_only"]),
        owner=str(payload["owner"]).strip(),
        notes=str(payload["notes"]).strip(),
        symbols_csv=str(payload.get("symbols_csv", "")).strip(),
        registry_path=str(path),
    )
    return record


def load_stock_pool_record(path: str | Path) -> StockPoolRecord:
    file_path = Path(path)
    payload = _load_toml_mapping(file_path)
    return _validate_record(payload, file_path)


def load_stock_pool_registry(registry_dir: str | Path) -> dict[tuple[str, str], StockPoolRecord]:
    root = Path(registry_dir)
    records: dict[tuple[str, str], StockPoolRecord] = {}
    for file_path in sorted(root.rglob("*.toml")):
        record = load_stock_pool_record(file_path)
        key = (record.stock_pool_id, record.stock_pool_version)
        if key in records:
            raise ValueError(f"duplicate stock pool record: {key}")
        records[key] = record
    return records


def get_stock_pool_record(
    registry_dir: str | Path,
    *,
    stock_pool_id: str,
    stock_pool_version: str | None = None,
) -> StockPoolRecord:
    records = load_stock_pool_registry(registry_dir)
    if stock_pool_version:
        key = (stock_pool_id, stock_pool_version)
        if key not in records:
            raise KeyError(f"stock pool not found: {key}")
        return records[key]

    matches = [record for (pool_id, _), record in records.items() if pool_id == stock_pool_id]
    if not matches:
        raise KeyError(f"stock pool not found: {stock_pool_id}")
    if len(matches) > 1:
        raise KeyError(f"multiple versions found for stock pool: {stock_pool_id}")
    return matches[0]


def _read_symbols_csv(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for column in ("symbol", "code", "ts_code"):
            if column in (reader.fieldnames or []):
                values = []
                for row in reader:
                    value = str(row.get(column, "")).strip()
                    if value:
                        values.append(value.zfill(6) if column == "code" else value)
                unique = sorted(set(values))
                if not unique:
                    raise ValueError(f"no symbols found in {path}")
                return unique
    raise ValueError(f"{path} must contain one of columns: symbol, code, ts_code")


def _resolve_symbols_csv_path(
    record: StockPoolRecord,
    *,
    registry_root: str | Path,
) -> Path:
    """Resolve symbols CSV relative to registry_root, with repo-relative fallback.

    Preferred form after MS-R3: paths relative to the registry root
    (e.g. ``low_manipulation/symbols.csv`` under ``inputs/pools``).
    Older configs may store repo-relative paths like ``inputs/pools/.../symbols.csv``.
    """
    raw = Path(str(record.symbols_csv).strip())
    if raw.is_absolute():
        return raw.resolve()

    under_registry = (Path(registry_root) / raw).resolve()
    if under_registry.exists():
        return under_registry

    cwd_candidate = raw.resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return under_registry


def resolve_stock_pool_symbols(
    record: StockPoolRecord,
    *,
    registry_root: str | Path,
) -> list[str]:
    if not record.symbols_csv:
        raise ValueError(
            f"stock pool {record.stock_pool_id}/{record.stock_pool_version} has no symbols_csv"
        )
    csv_path = _resolve_symbols_csv_path(record, registry_root=registry_root)
    symbols = _read_symbols_csv(csv_path)
    if len(symbols) != record.symbols_count:
        raise ValueError(
            f"symbols_count mismatch for {record.stock_pool_id}/{record.stock_pool_version}: "
            f"expected {record.symbols_count}, got {len(symbols)}"
        )
    return symbols


def export_stock_pool_artifacts(
    record: StockPoolRecord,
    *,
    output_dir: str | Path,
    registry_root: str | Path,
    generated_at: datetime | None = None,
) -> dict[str, Path]:
    generated_at = generated_at or datetime.now().astimezone()
    symbols = resolve_stock_pool_symbols(record, registry_root=registry_root)
    target_dir = Path(output_dir) / record.stock_pool_id / record.stock_pool_version
    target_dir.mkdir(parents=True, exist_ok=True)

    symbols_csv_path = target_dir / "symbols.csv"
    with symbols_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol"])
        for symbol in symbols:
            writer.writerow([symbol])

    metadata_path = target_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "stock_pool_id": record.stock_pool_id,
                "stock_pool_version": record.stock_pool_version,
                "pool_family": record.pool_family,
                "construction_method": record.construction_method,
                "base_universe": record.base_universe,
                "symbols_source": record.symbols_source,
                "symbols_count": len(symbols),
                "rebalance_frequency": record.rebalance_frequency,
                "effective_start": record.effective_start,
                "effective_end": record.effective_end,
                "is_default": record.is_default,
                "is_research_only": record.is_research_only,
                "owner": record.owner,
                "notes": record.notes,
                "generated_at": generated_at.isoformat(timespec="seconds"),
                "registry_path": record.registry_path,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"symbols_csv": symbols_csv_path, "metadata_json": metadata_path}
