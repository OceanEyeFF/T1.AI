from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.config_io import extract_arg_overrides, load_mapping_config


def test_load_mapping_config_json(tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"a": 1, "b": "x"}), encoding="utf-8")
    cfg = load_mapping_config(path)
    assert cfg["a"] == 1
    assert cfg["b"] == "x"


def test_extract_arg_overrides_with_section(tmp_path: Path) -> None:
    path = tmp_path / "cfg.toml"
    path.write_text(
        "\n".join(
            [
                "[run_lstm_rolling_retrain_dim19_regime]",
                "lr = 0.0001",
                "batch_size = 64",
            ]
        ),
        encoding="utf-8",
    )
    overrides, section = extract_arg_overrides(
        config_path=path,
        allowed_keys={"lr", "batch_size"},
        section_candidates=("run_lstm_rolling_retrain_dim19_regime",),
    )
    assert section == "run_lstm_rolling_retrain_dim19_regime"
    assert overrides["lr"] == 0.0001
    assert overrides["batch_size"] == 64


def test_extract_arg_overrides_rejects_unknown_key(tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"lr": 1e-4, "unknown_key": 1}), encoding="utf-8")
    try:
        extract_arg_overrides(
            config_path=path,
            allowed_keys={"lr"},
            section_candidates=(),
        )
    except ValueError as exc:
        assert "unknown config keys" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for unknown key")


def test_extract_arg_overrides_tolerates_known_metadata_keys(tmp_path: Path) -> None:
    path = tmp_path / "cfg.toml"
    path.write_text(
        "\n".join(
            [
                "[run_xgboost_rolling_retrain_regime]",
                "learning_rate = 0.03",
                'model_track = "mainline_3510d"',
                'config_profile = "xgb_rolling_baseline"',
                'config_status = "baseline"',
                'stock_pool_id = "csi300"',
                'stock_pool_version = "v1"',
                'evaluation_window_id = "fixed_20230101_20250701"',
                'dataset_id = "seq_csi300_19d_20230101_20260120"',
            ]
        ),
        encoding="utf-8",
    )

    overrides, section = extract_arg_overrides(
        config_path=path,
        allowed_keys={"learning_rate"},
        section_candidates=("run_xgboost_rolling_retrain_regime",),
    )

    assert section == "run_xgboost_rolling_retrain_regime"
    assert overrides == {"learning_rate": 0.03}
