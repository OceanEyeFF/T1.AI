#!/usr/bin/env python
"""Walk-forward sign calibration for trained LSTM multi-horizon predictions.

Goal:
  Detect regime sign flips and apply monthly walk-forward sign correction.

Default behavior:
  - Load one checkpoint and one dataset split directory.
  - Build raw predictions on valid/test.
  - For each test month, decide sign from historical IC on past data only
    (valid + earlier test months), then apply to that month.
  - Output raw vs calibrated metrics and monthly sign decisions.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ashare_lab.evaluation.metrics import (
    information_coefficient,
    mean_absolute_error,
    rank_information_coefficient,
)
from ashare_lab.trend_schema import PRIMARY_TREND_LABEL_COLS, PRIMARY_TREND_PRED_COLS


DEFAULT_FEATURES_11 = [
    "return_1d",
    "return_5d",
    "return_20d",
    "volume_ratio_5d",
    "volume_change",
    "amount_change",
    "rsi_14",
    "macd_hist",
    "bollinger_deviation",
    "price_slope_5d",
    "price_slope_20d",
]

LABEL_COLS = list(PRIMARY_TREND_LABEL_COLS)
PRED_COLS = list(PRIMARY_TREND_PRED_COLS)


@dataclass(frozen=True)
class ModelShape:
    input_dim: int
    hidden_size: int
    num_layers: int


class MtlLSTM(nn.Module):
    def __init__(self, *, input_dim: int, hidden_size: int, num_layers: int, dropout: float) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(hidden_size)

        def _head() -> nn.Module:
            return nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.GELU(),
                nn.Linear(hidden_size // 2, 1),
            )

        self.head_3d = _head()
        self.head_5d = _head()
        self.head_10d = _head()

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        out, _ = self.lstm(x)
        h = self.norm(out[:, -1, :])
        return (
            self.head_3d(h).squeeze(-1),
            self.head_5d(h).squeeze(-1),
            self.head_10d(h).squeeze(-1),
        )


def _infer_model_shape(state_dict: dict[str, torch.Tensor]) -> ModelShape:
    w0 = state_dict["lstm.weight_ih_l0"]
    hidden_size = int(w0.shape[0] // 4)
    input_dim = int(w0.shape[1])
    num_layers = len([k for k in state_dict.keys() if k.startswith("lstm.weight_ih_l")])
    return ModelShape(input_dim=input_dim, hidden_size=hidden_size, num_layers=num_layers)


def _load_split(path: Path, feature_bases: list[str], seq_len: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    df = pd.read_parquet(path)
    x_cols = [f"{base}_t{t}" for t in range(seq_len) for base in feature_bases]
    x_flat = df[x_cols].to_numpy(dtype=np.float32, copy=False)
    x = x_flat.reshape(len(df), seq_len, len(feature_bases))
    x = np.nan_to_num(x, nan=0.0)
    y = df[LABEL_COLS].to_numpy(dtype=np.float32, copy=False)
    meta = df[["date", "symbol"]].copy()
    meta["date"] = pd.to_datetime(meta["date"])
    meta["symbol"] = meta["symbol"].astype(str)
    return meta, x, y


@torch.no_grad()
def _predict(model: nn.Module, x: np.ndarray, batch_size: int, device: torch.device) -> np.ndarray:
    loader = DataLoader(TensorDataset(torch.from_numpy(x)), batch_size=batch_size, shuffle=False)
    preds: list[np.ndarray] = []
    model.eval()
    for (xb,) in loader:
        p3, p5, p10 = model(xb.to(device))
        pred = torch.stack([p3, p5, p10], dim=1).cpu().numpy()
        preds.append(pred)
    return np.concatenate(preds, axis=0)


def _metrics(pred: np.ndarray, y: np.ndarray) -> dict[str, float]:
    ic = [information_coefficient(pred[:, i], y[:, i]) for i in range(3)]
    ric = [rank_information_coefficient(pred[:, i], y[:, i]) for i in range(3)]
    mae = [mean_absolute_error(pred[:, i], y[:, i]) for i in range(3)]
    return {
        "ic_3d": float(ic[0]),
        "ic_5d": float(ic[1]),
        "ic_10d": float(ic[2]),
        "avg_ic": float(np.mean(ic)),
        "rank_ic_3d": float(ric[0]),
        "rank_ic_5d": float(ric[1]),
        "rank_ic_10d": float(ric[2]),
        "avg_rank_ic": float(np.mean(ric)),
        "mae_3d": float(mae[0]),
        "mae_5d": float(mae[1]),
        "mae_10d": float(mae[2]),
        "avg_mae": float(np.mean(mae)),
    }


def _history_ic(history: pd.DataFrame, col_pred: str, col_label: str) -> float:
    if history.empty:
        return 0.0
    return float(information_coefficient(history[col_pred].to_numpy(), history[col_label].to_numpy()))


def _months_to_weeks(months: int) -> int:
    return max(1, int(round(float(months) * 52.0 / 12.0)))


def _walkforward_calibrate(
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    calibration_weeks: int,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    months = sorted(test_df["date"].dt.to_period("M").unique())
    out = test_df.copy()
    out["pred_3d_cal"] = out["pred_3d"]
    out["pred_5d_cal"] = out["pred_5d"]
    out["pred_10d_cal"] = out["pred_10d"]

    decision_rows: list[dict[str, object]] = []
    hist = valid_df.copy()
    hist = hist.sort_values("date")

    for m in months:
        month_mask = out["date"].dt.to_period("M") == m
        month_df = out.loc[month_mask].copy()
        if month_df.empty:
            continue

        month_start = month_df["date"].min()
        if calibration_weeks > 0:
            hist_cut = month_start - pd.DateOffset(weeks=calibration_weeks)
            hist_use = hist.loc[(hist["date"] >= hist_cut) & (hist["date"] < month_start)].copy()
        else:
            hist_use = hist.loc[hist["date"] < month_start].copy()

        ic3 = _history_ic(hist_use, "pred_3d", "label_3d")
        ic5 = _history_ic(hist_use, "pred_5d", "label_5d")
        ic10 = _history_ic(hist_use, "pred_10d", "label_10d")
        avg_ic = float(np.mean([ic3, ic5, ic10]))
        sign = -1.0 if avg_ic < 0 else 1.0

        out.loc[month_mask, "pred_3d_cal"] = sign * out.loc[month_mask, "pred_3d"]
        out.loc[month_mask, "pred_5d_cal"] = sign * out.loc[month_mask, "pred_5d"]
        out.loc[month_mask, "pred_10d_cal"] = sign * out.loc[month_mask, "pred_10d"]

        raw_m = _metrics(
            month_df[["pred_3d", "pred_5d", "pred_10d"]].to_numpy(),
            month_df[LABEL_COLS].to_numpy(),
        )
        cal_m = _metrics(
            (sign * month_df[["pred_3d", "pred_5d", "pred_10d"]].to_numpy()),
            month_df[LABEL_COLS].to_numpy(),
        )

        decision_rows.append(
            {
                "month": str(m),
                "history_samples": int(len(hist_use)),
                "history_avg_ic": avg_ic,
                "sign": int(sign),
                "month_raw_avg_ic": raw_m["avg_ic"],
                "month_cal_avg_ic": cal_m["avg_ic"],
            }
        )

        # Walk-forward: after this month finishes, it becomes history for next month
        hist = pd.concat([hist, month_df], ignore_index=True)
        hist = hist.sort_values("date")

    return out, decision_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward sign calibration for LSTM predictions.")
    parser.add_argument("--dataset-dir", default="data/datasets/lstm_sector70_16d_20210101_20260120")
    parser.add_argument("--checkpoint", default="models/best_lstm_sector70_dim11_on16ds.pt")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--calibration-weeks", type=int, default=None, help="校准历史窗口（周），默认 12；0 表示全部历史")
    parser.add_argument(
        "--calibration-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：校准窗口（月）",
    )
    parser.add_argument(
        "--features",
        default=",".join(DEFAULT_FEATURES_11),
        help="comma separated feature bases in model input order",
    )
    parser.add_argument(
        "--report",
        default="output/reports/lstm_walkforward_sign_calibration_20260303.json",
    )
    args = parser.parse_args()

    if args.calibration_weeks is not None and args.calibration_weeks < 0:
        raise ValueError("calibration_weeks must be >= 0")
    if args.calibration_months is not None and args.calibration_months < 0:
        raise ValueError("calibration_months must be >= 0")
    if args.calibration_weeks is not None:
        calibration_weeks = int(args.calibration_weeks)
    elif args.calibration_months is not None:
        calibration_weeks = _months_to_weeks(int(args.calibration_months))
    else:
        calibration_weeks = 12

    feature_bases = [x.strip() for x in str(args.features).split(",") if x.strip()]
    dataset_dir = Path(args.dataset_dir)
    ckpt_path = Path(args.checkpoint)
    report_path = Path(args.report)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(ckpt_path, map_location="cpu")
    state = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
    shape = _infer_model_shape(state)
    if len(feature_bases) != shape.input_dim:
        raise ValueError(
            f"feature count {len(feature_bases)} != checkpoint input_dim {shape.input_dim}; "
            "please pass --features in exact model input order"
        )

    model = MtlLSTM(
        input_dim=shape.input_dim,
        hidden_size=shape.hidden_size,
        num_layers=shape.num_layers,
        dropout=args.dropout,
    )
    model.load_state_dict(state)
    model.to(device)

    valid_meta, x_valid, y_valid = _load_split(dataset_dir / "valid.parquet", feature_bases, args.seq_len)
    test_meta, x_test, y_test = _load_split(dataset_dir / "test.parquet", feature_bases, args.seq_len)

    p_valid = _predict(model, x_valid, args.batch_size, device)
    p_test = _predict(model, x_test, args.batch_size, device)

    valid_df = valid_meta.copy()
    test_df = test_meta.copy()
    for i, c in enumerate(PRED_COLS):
        valid_df[c] = p_valid[:, i]
        test_df[c] = p_test[:, i]
    for i, c in enumerate(LABEL_COLS):
        valid_df[c] = y_valid[:, i]
        test_df[c] = y_test[:, i]

    raw_metrics = _metrics(test_df[PRED_COLS].to_numpy(), test_df[LABEL_COLS].to_numpy())

    calibrated_df, monthly_decisions = _walkforward_calibrate(
        valid_df=valid_df,
        test_df=test_df,
        calibration_weeks=calibration_weeks,
    )
    cal_metrics = _metrics(
        calibrated_df[["pred_3d_cal", "pred_5d_cal", "pred_10d_cal"]].to_numpy(),
        calibrated_df[LABEL_COLS].to_numpy(),
    )

    out = {
        "config": {
            "dataset_dir": str(dataset_dir),
            "checkpoint": str(ckpt_path),
            "seq_len": int(args.seq_len),
            "feature_bases": feature_bases,
            "calibration_weeks": int(calibration_weeks),
            "window_unit": "week",
            "calibration_months_legacy_input": (
                None if args.calibration_months is None else int(args.calibration_months)
            ),
            "device": str(device),
            "valid_rows": int(len(valid_df)),
            "test_rows": int(len(test_df)),
        },
        "raw_test_metrics": raw_metrics,
        "calibrated_test_metrics": cal_metrics,
        "delta_cal_minus_raw": {
            "avg_ic": float(cal_metrics["avg_ic"] - raw_metrics["avg_ic"]),
            "avg_rank_ic": float(cal_metrics["avg_rank_ic"] - raw_metrics["avg_rank_ic"]),
            "avg_mae": float(cal_metrics["avg_mae"] - raw_metrics["avg_mae"]),
        },
        "monthly_decisions": monthly_decisions,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
