"""CLI 默认值三区对齐合同 + akshare choice 拒绝（双路 CodeReview P1）。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.paths import REPO_ROOT

# ---------------------------------------------------------------- 默认值契约


@pytest.mark.contract
def test_daily_pipeline_defaults() -> None:
    from scripts.daily_pipeline import _parse_args

    args = _parse_args(["--date", "20250101"])
    assert args.config == "inputs/configs/pipeline.toml"
    assert args.data_source_config == "inputs/configs/data_source.toml"
    assert args.model_config == "inputs/configs/profiles/model_mtl.toml"


@pytest.mark.contract
def test_validate_recommendations_defaults() -> None:
    from scripts.validate_recommendations import _parse_args

    args = _parse_args(["--input", "x.json"])
    assert args.source == "tushare"
    assert args.db_path == "outputs/recommendations.db"


@pytest.mark.contract
def test_evaluate_recommendation_defaults() -> None:
    from scripts.evaluate_recommendation import _parse_args

    args = _parse_args(["--pred-file", "p.csv", "--actual-file", "a.csv"])
    assert args.output_dir == "outputs/reports/validation"
    assert args.db_path == "outputs/recommendations.db"


@pytest.mark.contract
def test_build_sequence_dataset_defaults() -> None:
    from scripts.build_sequence_dataset import _build_parser

    args = _build_parser().parse_args(["--start", "20240101", "--end", "20240131"])
    assert args.source == "tushare"
    assert args.cache_dir == "inputs/data/cache"
    assert args.output_dir == "workspace/datasets"
    assert args.stock_pool_export_dir == "outputs/stock_pools"


@pytest.mark.contract
def test_build_sequence_dataset_market_state_defaults() -> None:
    from scripts.build_sequence_dataset_market_state import _build_parser

    args = _build_parser().parse_args([])
    assert args.source == "tushare_live"
    assert args.cache_dir == "inputs/data/cache"
    assert args.stock_pool_export_dir == "outputs/stock_pools"


@pytest.mark.contract
def test_run_backtest_defaults() -> None:
    from scripts.run_backtest import _parse_args

    args = _parse_args(["--symbols", "600000", "--start", "20240101", "--end", "20240131"])
    assert args.source == "tushare"
    assert args.cache_dir == "inputs/data/cache"
    assert args.out_dir == "outputs/reports"


@pytest.mark.contract
def test_run_sim_replay_defaults() -> None:
    from scripts.run_sim_replay import _parse_args

    args = _parse_args(["--symbol", "600000", "--start", "20240101", "--end", "20240131"])
    assert args.source == "tushare"
    assert args.out_dir == "outputs/sim"


# ---------------------------------------------------------------- akshare 拒绝


@pytest.mark.contract
@pytest.mark.parametrize(
    ("script", "required"),
    [
        ("scripts/build_sequence_dataset.py", ["--start", "20240101", "--end", "20240131"]),
        ("scripts/build_sequence_dataset_market_state.py", ["--stock-pool-id", "x"]),
        ("scripts/validate_recommendations.py", ["--input", "missing.json"]),
        ("scripts/run_backtest.py", ["--symbols", "600000", "--start", "20240101", "--end", "20240131"]),
        ("scripts/run_sim_replay.py", ["--symbol", "600000", "--start", "20240101", "--end", "20240131"]),
    ],
)
def test_akshare_rejected_by_cli_choice(script: str, required: list[str]) -> None:
    proc = subprocess.run(
        [sys.executable, script, *required, "--source", "akshare"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src:."},
        check=False,
    )
    assert proc.returncode == 2, proc.stderr + proc.stdout
    assert "invalid choice" in proc.stderr or "仅支持" in proc.stderr


@pytest.mark.contract
def test_config_file_cannot_bypass_source_choices(tmp_path: Path) -> None:
    """配置文件里的 source 同样受 choice 校验（防 set_defaults 绕过）。"""
    bad = tmp_path / "bad.toml"
    bad.write_text(
        '[build_sequence_dataset]\n'
        'start="20240101"\n'
        'end="20240131"\n'
        'source="akshare"\n',
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "scripts/build_sequence_dataset.py", "--config-file", str(bad)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src:."},
        check=False,
    )
    assert proc.returncode == 2, proc.stderr + proc.stdout
    assert "仅支持 tushare/odp" in proc.stderr


@pytest.mark.contract
def test_rolling_retrain_dataset_dir_defaults() -> None:
    from scripts.run_lstm_rolling_retrain_dim19_regime import _build_parser as lstm_parser
    from scripts.run_xgboost_rolling_retrain_regime import _build_parser as xgb_parser

    lstm = lstm_parser().parse_args([])
    assert str(lstm.dataset_dir).startswith("workspace/datasets/")

    xgb = xgb_parser().parse_args([])
    assert str(xgb.dataset_dir).startswith("workspace/datasets/")
