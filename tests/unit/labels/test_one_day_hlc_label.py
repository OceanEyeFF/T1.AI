from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_lab.labels.multi_horizon import OneDayHLCLabel


def _sample_bars() -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "open": [10.0, 10.5, 10.8, 11.0],
            "high": [10.2, 10.9, 11.1, 11.4],
            "low": [9.8, 10.2, 10.6, 10.8],
            "close": [10.1, 10.7, 10.9, 11.2],
            "volume": [1000.0, 1200.0, 1100.0, 1300.0],
        },
        index=idx,
    )


def test_one_day_hlc_close_to_close() -> None:
    bars = _sample_bars()
    out = OneDayHLCLabel(label_mode="close_to_close").compute(bars)

    # t=2026-01-01 -> next day high/low/close relative to close[t]=10.1
    assert np.isclose(out.loc["2026-01-01", "label_1d_high"], 10.9 / 10.1 - 1.0)
    assert np.isclose(out.loc["2026-01-01", "label_1d_low"], 10.2 / 10.1 - 1.0)
    assert np.isclose(out.loc["2026-01-01", "label_1d_close"], 10.7 / 10.1 - 1.0)
    # tail has no t+1 target
    assert np.isnan(out.loc["2026-01-04", "label_1d_high"])


def test_one_day_hlc_next_open_to_open_with_suspension_mask() -> None:
    bars = _sample_bars()
    bars.loc["2026-01-03", "volume"] = 0.0  # makes t=2026-01-02 invalid
    out = OneDayHLCLabel(label_mode="next_open_to_open").compute(bars)

    # t=2026-01-01 -> base is open[t+1]=10.5
    assert np.isclose(out.loc["2026-01-01", "label_1d_high"], 10.9 / 10.5 - 1.0)
    assert np.isclose(out.loc["2026-01-01", "label_1d_low"], 10.2 / 10.5 - 1.0)
    assert np.isclose(out.loc["2026-01-01", "label_1d_close"], 10.7 / 10.5 - 1.0)

    # t=2026-01-02 references day 2026-01-03 where volume=0 -> invalid
    assert np.isnan(out.loc["2026-01-02", "label_1d_high"])
    assert np.isnan(out.loc["2026-01-02", "label_1d_low"])
    assert np.isnan(out.loc["2026-01-02", "label_1d_close"])
