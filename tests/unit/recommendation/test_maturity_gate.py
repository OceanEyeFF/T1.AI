import sys
from pathlib import Path

import pandas as pd


from scripts.run_lstm_rolling_retrain_dim19_regime import (
    _attach_label_maturity_date,
    _infer_max_horizon_days,
    _select_train_valid_for_month,
)


def _make_panel(n_days: int = 40) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=n_days)
    rows: list[dict[str, object]] = []
    for symbol in ("000001", "000002"):
        for d in dates:
            rows.append({"date": d, "symbol": symbol})
    return pd.DataFrame(rows).sort_values(["date", "symbol"]).reset_index(drop=True)


def test_infer_max_horizon_days_from_labels() -> None:
    assert _infer_max_horizon_days(["label_3d", "label_5d", "label_10d"]) == 10


def test_attach_label_maturity_date_with_shift() -> None:
    df = _make_panel(n_days=15)
    out = _attach_label_maturity_date(df, horizon_days=3, shift_days=1)
    sym = out[out["symbol"] == "000001"].sort_values("date").reset_index(drop=True)
    assert sym.loc[0, "label_maturity_date"] == sym.loc[4, "date"]
    assert pd.isna(sym.loc[len(sym) - 4, "label_maturity_date"])


def test_select_train_valid_applies_maturity_gate() -> None:
    df = _make_panel(n_days=40)
    df = _attach_label_maturity_date(df, horizon_days=3, shift_days=0)
    month_start = pd.Timestamp("2024-02-20")
    train_df, valid_df, stats = _select_train_valid_for_month(
        df,
        month_start=month_start,
        train_window_weeks=12,
        valid_window_weeks=3,
    )

    assert not train_df.empty
    assert not valid_df.empty
    assert int(stats["pool_rows_before_maturity"]) >= int(stats["pool_rows_after_maturity"])
    assert train_df["label_maturity_date"].max() < month_start
    assert valid_df["label_maturity_date"].max() < month_start
