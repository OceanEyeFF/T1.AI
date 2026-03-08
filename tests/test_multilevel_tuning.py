from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.run_multilevel_tuning import (
    _build_lstm_specs,
    _build_train_command,
    _build_xgb_specs,
    _filter_train_args,
    _levels_from_arg,
    _snapshot_lstm,
)


def _mock_lstm_config() -> dict:
    return {
        "dataset_dir": "data/datasets/mock",
        "feature_mode": "auto",
        "features": ["return_1d", "return_5d"],
        "seq_len": 20,
        "train_window_weeks": 104,
        "valid_window_weeks": 8,
        "calibration_weeks": 12,
        "sign_threshold": 0.02,
        "backbone": "lstm",
        "hidden_size": 64,
        "num_layers": 2,
        "d_model": 64,
        "n_heads": 4,
        "d_ff": 128,
        "dropout": 0.3,
        "lr": 5e-5,
        "optimizer": "adamw",
        "weight_decay": 1e-5,
        "lr_scheduler": "cosine_warm_restart",
        "lr_min": 1e-6,
        "cosine_t_max": 20,
        "warm_restart_t0": 8,
        "warm_restart_t_mult": 2,
        "plateau_factor": 0.5,
        "plateau_patience": 3,
        "grad_clip_mode": "norm",
        "grad_clip_threshold": 1.0,
        "norm_type": "layernorm",
        "norm_eps": 1e-8,
        "batch_size": 32,
        "max_epochs": 40,
        "patience": 20,
        "loss_weights": {"3d": 0.1, "5d": 0.45, "10d": 0.45},
        "loss_type": "ic_aware",
        "loss_alpha": 0.176,
        "ic_rank_beta": 0.5,
        "seed": 42,
        "label_mode": "close_to_close",
    }


def _mock_xgb_base() -> dict:
    return {
        "dataset_dir": "data/datasets/mock",
        "feature_mode": "auto",
        "features": ["return_1d", "return_5d"],
        "seq_len": 20,
        "train_window_weeks": 104,
        "valid_window_weeks": 8,
        "calibration_weeks": 12,
        "sign_threshold": 0.02,
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 1.0,
        "gamma": 0.0,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
        "n_jobs": 8,
        "early_stopping_rounds": 40,
        "device": "cpu",
        "seed": 42,
    }


def test_snapshot_lstm_extracts_loss_weights() -> None:
    base = _snapshot_lstm(_mock_lstm_config())
    assert base["w3"] == 0.1
    assert base["w5"] == 0.45
    assert base["w10"] == 0.45
    assert base["feature_count"] == 2


def test_build_lstm_specs_l1_non_empty_and_unique() -> None:
    base = _snapshot_lstm(_mock_lstm_config())
    specs = _build_lstm_specs("L1", base)
    assert specs
    names = [s.name for s in specs]
    assert len(names) == len(set(names))
    assert any("lr_" in n for n in names)
    assert any("dropout_" in n for n in names)


def test_build_xgb_specs_l2_non_empty() -> None:
    specs = _build_xgb_specs("L2", _mock_xgb_base())
    assert specs
    assert any("childw_" in s.name for s in specs)
    assert any("trainw_" in s.name for s in specs)


def test_build_train_command_contains_required_flags() -> None:
    base = _snapshot_lstm(_mock_lstm_config())
    cmd = _build_train_command(
        python_exec="python",
        model="lstm",
        args_dict=base,
        report_path=Path("output/reports/a.json"),
        oos_path=Path("output/reports/a_oos.parquet"),
    )
    cmd_text = " ".join(cmd)
    assert "scripts/run_lstm_rolling_retrain_dim19_regime.py" in cmd_text
    assert "--dataset-dir" in cmd
    assert "--save-oos-parquet" in cmd
    assert "--report" in cmd


def test_build_train_command_prefers_config_file() -> None:
    base = _snapshot_lstm(_mock_lstm_config())
    cmd = _build_train_command(
        python_exec="python",
        model="lstm",
        args_dict=base,
        report_path=Path("output/reports/a.json"),
        oos_path=Path("output/reports/a_oos.parquet"),
        config_file=Path("configs/experiments/lstm_rolling_baseline.toml"),
    )
    assert "--config-file" in cmd
    assert "configs/experiments/lstm_rolling_baseline.toml" in " ".join(cmd)
    # 配置文件模式下不需要展开全部参数
    assert "--dataset-dir" not in cmd


def test_levels_from_arg() -> None:
    assert _levels_from_arg("L1") == ["L1"]
    assert _levels_from_arg("all") == ["L1", "L2", "L3"]


def test_filter_train_args_drops_non_parser_keys() -> None:
    base = _snapshot_lstm(_mock_lstm_config())
    filtered = _filter_train_args("lstm", base)
    assert "feature_count" not in filtered
    assert "features" not in filtered
    assert "dataset_dir" in filtered


def test_multilevel_tuning_dry_run_works_without_baseline_reports(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = tmp_path / "reports"
    cmd = [
        "conda",
        "run",
        "-n",
        "ashare-lab",
        "python",
        "scripts/run_multilevel_tuning.py",
        "--model",
        "both",
        "--level",
        "L1",
        "--max-runs-per-level",
        "1",
        "--output-dir",
        str(out_dir),
        "--tag",
        "pytest",
    ]
    res = subprocess.run(cmd, cwd=repo_root, check=False, capture_output=True, text=True)
    assert res.returncode == 0, f"stderr:\n{res.stderr}\nstdout:\n{res.stdout}"
    assert (out_dir / "multilevel_tuning_manifest_pytest.json").exists()
