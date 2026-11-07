from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts.run_lstm_rolling_retrain_dim19_regime import (
    _load_dataset_feature_contract as load_lstm_feature_contract,
)
from scripts.run_lstm_rolling_retrain_dim19_regime import (
    _load_dataset_label_mode as load_lstm_label_mode,
)
from scripts.run_lstm_rolling_retrain_dim19_regime import (
    _screen_feature_partition as screen_lstm_partition,
)
from scripts.run_xgboost_rolling_retrain_regime import (
    _load_dataset_feature_contract as load_xgb_feature_contract,
)
from scripts.run_xgboost_rolling_retrain_regime import (
    _load_label_mode as load_xgb_label_mode,
)
from ashare_lab.features.contract import FeatureContractLoader
from tests.support.paths import REPO_ROOT
from scripts.run_xgboost_rolling_retrain_regime import (
    _screen_feature_partition as screen_xgb_partition,
)


def _frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for i in range(3):
        row: dict[str, object] = {
            "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i),
            "symbol": "000001",
            "label_3d": 0.01,
            "label_5d": 0.02,
            "label_10d": 0.03,
        }
        for t in range(2):
            row[f"f0_t{t}"] = float(i + t)
            row[f"f1_t{t}"] = float(i + t + 10)
        rows.append(row)
    rows[1]["f1_t1"] = np.nan
    return pd.DataFrame(rows)


def test_lstm_and_xgb_screen_the_same_nonfinite_feature_row() -> None:
    frame = _frame()
    feature_bases = ["f0", "f1"]
    label_cols = ["label_3d", "label_5d", "label_10d"]

    lstm_df, lstm_x, lstm_y, lstm_quality = screen_lstm_partition(
        frame,
        feature_bases=feature_bases,
        seq_len=2,
        label_cols=label_cols,
    )
    xgb_df, xgb_x, xgb_y, xgb_quality = screen_xgb_partition(
        frame,
        feature_bases=feature_bases,
        seq_len=2,
    )

    assert lstm_df.index.tolist() == [0, 1]
    assert xgb_df.index.tolist() == [0, 1]
    assert lstm_x.shape == (2, 2, 2)
    assert xgb_x.shape == (2, 2, 2)
    assert lstm_y.shape == xgb_y.shape == (2, 3)
    assert lstm_quality.to_dict() == xgb_quality.to_dict()
    assert lstm_quality.dropped_rows == 1


def test_rolling_scripts_require_dataset_label_mode_metadata(tmp_path) -> None:
    (tmp_path / "metadata.json").write_text(
        json.dumps({"label_config": {"label_mode": "next_open_to_open"}}),
        encoding="utf-8",
    )

    assert load_lstm_label_mode(tmp_path) == "next_open_to_open"
    assert load_xgb_label_mode(tmp_path) == "next_open_to_open"

    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported label_mode"):
        load_lstm_label_mode(tmp_path)
    with pytest.raises(ValueError, match="unsupported label_mode"):
        load_xgb_label_mode(tmp_path)


def test_rolling_scripts_derive_exact_feature_order_from_dataset_metadata(tmp_path) -> None:
    contract = FeatureContractLoader.load(
        REPO_ROOT / "inputs/configs/features/mainline_11d_v1.toml"
    )
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "label_config": {"label_mode": "close_to_close"},
                "feature_contract": contract.to_metadata(),
                "feature_config": {
                    "seq_len": contract.seq_len,
                    "num_features": contract.input_dim,
                    "feature_names": list(contract.feature_names),
                },
            }
        ),
        encoding="utf-8",
    )

    lstm = load_lstm_feature_contract(tmp_path)
    xgb = load_xgb_feature_contract(tmp_path)

    assert lstm.contract_hash == xgb.contract_hash == contract.contract_hash
    assert lstm.feature_names == xgb.feature_names == contract.feature_names
    assert lstm.seq_len == xgb.seq_len == 20
