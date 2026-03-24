from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.runtime_metadata import (
    build_default_report_path,
    build_effective_config_payload,
    canonicalize_config_status,
    resolve_experiment_context,
)


def test_canonicalize_config_status_accepts_legacy_aliases() -> None:
    assert canonicalize_config_status("candidate-best") == "candidate"
    assert canonicalize_config_status("frozen-best") == "frozen"
    assert canonicalize_config_status("baseline") == "baseline"


def test_resolve_experiment_context_infers_dataset_contract_from_metadata(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "metadata.json").write_text(
        json.dumps(
            {
                "dataset_config": {
                    "symbols_csv": "data/symbols_lstm_quick8.csv",
                    "num_symbols": 8,
                    "start_date": "20230101",
                    "end_date": "20260305",
                },
                "feature_config": {
                    "num_features": 53,
                },
            }
        ),
        encoding="utf-8",
    )

    ctx = resolve_experiment_context(
        dataset_dir=dataset_dir,
        model_track="mainline_3510d",
        config_profile="xgb_rolling_baseline",
        config_status="candidate-best",
    )

    assert ctx["config_status"] == "candidate"
    assert ctx["stock_pool_id"] == "custom_quick8"
    assert ctx["stock_pool_version"] == "v1"
    assert ctx["evaluation_window_id"] == "fixed_20230101_20250701"
    assert ctx["dataset_id"] == "seq_quick8_53d_20230101_20260305"


def test_build_default_report_path_uses_model_track_subdir() -> None:
    generated_at = datetime(2026, 3, 23, 9, 30, tzinfo=timezone.utc)
    path = build_default_report_path(
        backbone="xgb",
        model_track="mainline_3510d",
        config_profile="xgb_rolling_baseline",
        generated_at=generated_at,
    )
    assert path == Path("output/reports/mainline_3510d/xgb_baseline_20260323.json")


def test_build_effective_config_payload_contains_required_contract_fields() -> None:
    generated_at = datetime(2026, 3, 23, 9, 30, tzinfo=timezone.utc)
    payload = build_effective_config_payload(
        context={
            "model_track": "mainline_3510d",
            "config_profile": "lstm_rolling_baseline",
            "config_status": "baseline",
            "stock_pool_id": "custom_quick8",
            "stock_pool_version": "v1",
            "evaluation_window_id": "fixed_20230101_20250701",
            "dataset_id": "seq_quick8_53d_20230101_20260305",
        },
        seed=42,
        script="run_lstm_rolling_retrain_dim19_regime",
        config_file="configs/experiments/lstm_rolling_baseline.toml",
        generated_at=generated_at,
        args_mapping={"seed": 42},
    )

    assert payload["experiment_id"] == "lstm_rolling_baseline_mainline_3510d_20260323"
    assert payload["stock_pool_id"] == "custom_quick8"
    assert payload["evaluation_window_id"] == "fixed_20230101_20250701"
    assert payload["dataset_id"] == "seq_quick8_53d_20230101_20260305"
    assert payload["args"] == {"seed": 42}
