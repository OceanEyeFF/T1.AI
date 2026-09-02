"""audit_lag_horizon_analysis CLI 合同（4.2 时效分析）。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.audit_lag_horizon_analysis import main


def _synthetic_oos(path: Path) -> None:
    """60 symbol × 60 天，pred_5d/label_5d 带正相关、预测提前 5 天有效。"""
    rng = np.random.default_rng(7)
    rows = []
    for i, sym in enumerate([f"60{i:04d}" for i in range(6)]):
        dates = pd.date_range("2026-01-05", periods=40, freq="B")
        signal = rng.normal(0, 1, 40)
        label = signal * 0.5 + rng.normal(0, 0.5, 40)
        for j, d in enumerate(dates):
            rows.append({"date": d, "symbol": sym, "pred_5d": signal[j], "label_5d": label[j]})
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_lag_analysis_outputs_json(tmp_path: Path) -> None:
    oos = tmp_path / "oos.parquet"
    _synthetic_oos(oos)
    out = tmp_path / "lag.json"
    rc = main(["--oos-parquet", str(oos), "--horizons", "5", "--output", str(out)])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] in {"PASS", "REVIEW"}
    assert len(report["rows"]) == 5  # lag=1..5
    for row in report["rows"]:
        assert row["horizon"] == 5
        assert "daily_cs_ic" in row and "drop_vs_lag1" in row
