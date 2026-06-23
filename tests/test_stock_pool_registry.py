from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ashare_lab.stock_pool import (
    export_stock_pool_artifacts,
    get_stock_pool_record,
    load_stock_pool_record,
    load_stock_pool_registry,
    resolve_stock_pool_symbols,
)
from scripts.build_sequence_dataset import _resolve_symbols_input


def _synthetic_daily_bars(symbol: str, periods: int = 120) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    base = np.linspace(10.0, 22.0, periods, dtype=float)
    offset = (sum(ord(ch) for ch in symbol) % 7) * 0.03
    close = base + offset
    out = pd.DataFrame(
        {
            "open": close - 0.15,
            "high": close + 0.2,
            "low": close - 0.25,
            "close": close,
            "volume": np.linspace(1_000_000, 1_300_000, periods, dtype=float),
            "amount": np.linspace(2_000_000, 2_600_000, periods, dtype=float),
        },
        index=dates,
    )
    out.index.name = "date"
    return out


def test_load_stock_pool_record_from_registry_sample() -> None:
    path = Path("inputs/pools/low_manipulation/config.toml")
    record = load_stock_pool_record(path)
    assert record.stock_pool_id == "custom_low_manipulation"
    assert record.stock_pool_version == "v1"
    assert record.symbols_count == 14


def test_load_stock_pool_registry_and_get_single_record() -> None:
    registry = load_stock_pool_registry("inputs/pools")
    assert ("custom_low_manipulation", "v1") in registry
    record = get_stock_pool_record("inputs/pools", stock_pool_id="custom_low_manipulation")
    assert record.pool_family == "custom"


def test_resolve_stock_pool_symbols_and_export_artifacts(tmp_path: Path) -> None:
    registry_root = Path.cwd() / "inputs/pools"
    record = get_stock_pool_record(registry_root, stock_pool_id="custom_low_manipulation")
    symbols = resolve_stock_pool_symbols(record, registry_root=registry_root)
    assert len(symbols) == 14

    artifacts = export_stock_pool_artifacts(
        record, output_dir=tmp_path, registry_root=registry_root
    )
    exported_csv = artifacts["symbols_csv"]
    exported_meta = artifacts["metadata_json"]
    assert exported_csv.exists()
    assert exported_meta.exists()

    payload = json.loads(exported_meta.read_text(encoding="utf-8"))
    assert payload["stock_pool_id"] == "custom_low_manipulation"
    assert payload["stock_pool_version"] == "v1"
    assert int(payload["symbols_count"]) == 14


def test_resolve_symbols_input_supports_stock_pool_registry(tmp_path: Path) -> None:
    symbols, context = _resolve_symbols_input(
        symbols=None,
        symbols_csv=None,
        stock_pool_id="custom_low_manipulation",
        stock_pool_version="v1",
        stock_pool_registry_dir="inputs/pools",
        stock_pool_export_dir=str(tmp_path),
    )
    assert len(symbols) == 14
    assert context["stock_pool_id"] == "custom_low_manipulation"
    assert context["stock_pool_version"] == "v1"
    assert context["symbols_csv"].endswith("custom_low_manipulation/v1/symbols.csv")


def test_invalid_stock_pool_record_missing_required_fields(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.toml"
    bad_path.write_text(
        "\n".join(
            [
                'stock_pool_id = "custom_bad"',
                'stock_pool_version = "v1"',
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_stock_pool_record(bad_path)
    except ValueError as exc:
        assert "missing required stock pool fields" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for missing required stock pool fields")


def test_build_sequence_dataset_cli_smoke_supports_stock_pool_registry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import build_sequence_dataset as dataset_script

    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        dataset_script, "_load_bars", lambda *_args, **_kwargs: _synthetic_daily_bars("000001")
    )

    output_dir = tmp_path / "seq_quick8_dataset"
    export_dir = tmp_path / "stock_pool_exports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_sequence_dataset.py",
            "--start",
            "20240102",
            "--end",
            "20240628",
            "--seq-len",
            "5",
            "--valid-weeks",
            "4",
            "--test-weeks",
            "4",
            "--source",
            "akshare",
            "--output-dir",
            str(output_dir),
            "--stock-pool-id",
            "custom_low_manipulation",
            "--stock-pool-version",
            "v1",
            "--stock-pool-export-dir",
            str(export_dir),
        ],
    )

    dataset_script.main()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert (output_dir / "train.parquet").exists()
    assert (output_dir / "valid.parquet").exists()
    assert (output_dir / "test.parquet").exists()
    assert metadata["dataset_config"]["stock_pool_id"] == "custom_low_manipulation"
    assert metadata["dataset_config"]["stock_pool_version"] == "v1"
    assert metadata["dataset_config"]["symbols_csv"].endswith(
        "custom_low_manipulation/v1/symbols.csv"
    )
    assert metadata["dataset_id"].startswith("seq_low_manipulation_")


def test_build_sequence_dataset_market_state_cli_smoke_supports_stock_pool_registry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import build_sequence_dataset_market_state as market_state_script

    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        market_state_script,
        "_load_bars",
        lambda *_args, **_kwargs: _synthetic_daily_bars("000001"),
    )

    output_dir = tmp_path / "market_state_quick8_dataset"
    export_dir = tmp_path / "stock_pool_exports_market_state"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_sequence_dataset_market_state.py",
            "--start",
            "20240102",
            "--end",
            "20240628",
            "--seq-len",
            "5",
            "--valid-weeks",
            "4",
            "--test-weeks",
            "4",
            "--source",
            "akshare",
            "--output-dir",
            str(output_dir),
            "--stock-pool-id",
            "custom_low_manipulation",
            "--stock-pool-version",
            "v1",
            "--stock-pool-export-dir",
            str(export_dir),
            "--no-include-short-term-features",
            "--no-include-sector-etf-features",
            "--no-include-odp-commodity-features",
            "--request-interval-seconds",
            "0",
        ],
    )

    market_state_script.main()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert (output_dir / "train.parquet").exists()
    assert (output_dir / "valid.parquet").exists()
    assert (output_dir / "test.parquet").exists()
    assert metadata["dataset_config"]["stock_pool_id"] == "custom_low_manipulation"
    assert metadata["dataset_config"]["stock_pool_version"] == "v1"
    assert metadata["dataset_config"]["symbols_csv"].endswith(
        "custom_low_manipulation/v1/symbols.csv"
    )
    assert metadata["dataset_id"].startswith("mkt_low_manipulation_")
