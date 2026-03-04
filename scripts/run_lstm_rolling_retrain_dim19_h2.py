#!/usr/bin/env python
"""Rolling retrain for 2-head LSTM (5d/10d only) on dim19 market-state features."""

from __future__ import annotations

import argparse
import json
import random
import time
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

FEATURES_DIM19 = [
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "volume_ratio_5d",
    "relative_volume",
    "volume_change",
    "amount_change",
    "rsi_14",
    "macd_line",
    "macd_signal",
    "macd_hist",
    "bollinger_deviation",
    "price_slope_5d",
    "price_slope_20d",
    "market_mom_5d",
    "market_vol_20d",
    "market_amount_z20",
]

LABEL_COLS = ["label_5d", "label_10d"]
PRED_COLS = ["pred_5d", "pred_10d"]


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _masked_l1(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() == 0:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    return torch.mean(torch.abs(pred[mask] - target[mask]))


def _extract_xy(df: pd.DataFrame, feature_bases: list[str], seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    x_cols = [f"{b}_t{t}" for t in range(seq_len) for b in feature_bases]
    x = df[x_cols].to_numpy(dtype=np.float32, copy=False).reshape(len(df), seq_len, len(feature_bases))
    x = np.nan_to_num(x, nan=0.0)
    y = df[LABEL_COLS].to_numpy(dtype=np.float32, copy=False)
    return x, y


def _metrics(pred: np.ndarray, y: np.ndarray) -> dict[str, float]:
    ic_5 = float(information_coefficient(pred[:, 0], y[:, 0]))
    ic_10 = float(information_coefficient(pred[:, 1], y[:, 1]))
    ric_5 = float(rank_information_coefficient(pred[:, 0], y[:, 0]))
    ric_10 = float(rank_information_coefficient(pred[:, 1], y[:, 1]))
    mae_5 = float(mean_absolute_error(pred[:, 0], y[:, 0]))
    mae_10 = float(mean_absolute_error(pred[:, 1], y[:, 1]))
    return {
        "ic_5d": ic_5,
        "ic_10d": ic_10,
        "avg_ic_5_10": float(np.mean([ic_5, ic_10])),
        "rank_ic_5d": ric_5,
        "rank_ic_10d": ric_10,
        "avg_rank_ic_5_10": float(np.mean([ric_5, ric_10])),
        "mae_5d": mae_5,
        "mae_10d": mae_10,
        "avg_mae_5_10": float(np.mean([mae_5, mae_10])),
    }


class LstmH2(nn.Module):
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

        self.head_5d = _head()
        self.head_10d = _head()

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        out, _ = self.lstm(x)
        h = self.norm(out[:, -1, :])
        return {
            "pred_5d": self.head_5d(h).squeeze(-1),
            "pred_10d": self.head_10d(h).squeeze(-1),
        }


@torch.no_grad()
def _predict(model: nn.Module, x: np.ndarray, batch_size: int, device: torch.device) -> np.ndarray:
    model.eval()
    dl = DataLoader(TensorDataset(torch.from_numpy(x)), batch_size=batch_size, shuffle=False)
    out: list[np.ndarray] = []
    for (xb,) in dl:
        p = model(xb.to(device))
        out.append(torch.stack([p["pred_5d"], p["pred_10d"]], dim=1).cpu().numpy())
    return np.concatenate(out, axis=0)


@dataclass(frozen=True)
class TrainConfig:
    hidden_size: int
    num_layers: int
    dropout: float
    lr: float
    batch_size: int
    max_epochs: int
    patience: int
    w5: float
    w10: float


def _train_one(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    cfg: TrainConfig,
    device: torch.device,
) -> tuple[nn.Module, dict[str, float], int, float]:
    model = LstmH2(
        input_dim=x_train.shape[2],
        hidden_size=cfg.hidden_size,
        num_layers=cfg.num_layers,
        dropout=cfg.dropout,
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=1e-5)

    dl_train = DataLoader(
        TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
        batch_size=cfg.batch_size,
        shuffle=True,
        pin_memory=torch.cuda.is_available(),
    )

    best_ic = -1e9
    best_state = None
    stale = 0
    epochs = 0
    t0 = time.perf_counter()

    for ep in range(1, cfg.max_epochs + 1):
        epochs = ep
        model.train()
        total = 0.0
        for xb, yb in dl_train:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            out = model(xb)
            loss_5 = _masked_l1(out["pred_5d"], yb[:, 0])
            loss_10 = _masked_l1(out["pred_10d"], yb[:, 1])
            loss = cfg.w5 * loss_5 + cfg.w10 * loss_10
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += float(loss.item())

        pred_v = _predict(model, x_valid, cfg.batch_size, device)
        met_v = _metrics(pred_v, y_valid)
        print(
            f"epoch={ep:02d} train_loss={total/max(1,len(dl_train)):.5f} "
            f"val_ic_5_10={met_v['avg_ic_5_10']:.4f} val_rank_5_10={met_v['avg_rank_ic_5_10']:.4f}"
        )

        if met_v["avg_ic_5_10"] > best_ic:
            best_ic = float(met_v["avg_ic_5_10"])
            stale = 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1

        if stale >= cfg.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device)

    train_seconds = float(time.perf_counter() - t0)
    valid_best = _metrics(_predict(model, x_valid, cfg.batch_size, device), y_valid)
    return model, valid_best, epochs, train_seconds


def _select_train_valid_for_month(
    all_df: pd.DataFrame,
    month_start: pd.Timestamp,
    *,
    train_window_months: int,
    valid_window_months: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    left = month_start - pd.DateOffset(months=train_window_months)
    pool = all_df[(all_df["date"] >= left) & (all_df["date"] < month_start)].copy()
    if pool.empty:
        raise RuntimeError(f"empty rolling pool before {month_start.date()}")

    valid_left = month_start - pd.DateOffset(months=valid_window_months)
    valid_df = pool[(pool["date"] >= valid_left) & (pool["date"] < month_start)].copy()
    train_df = pool[pool["date"] < valid_left].copy()
    if train_df.empty or valid_df.empty:
        ud = np.array(sorted(pool["date"].unique()))
        cut = max(1, int(len(ud) * 0.85))
        train_dates = set(pd.to_datetime(ud[:cut]))
        valid_dates = set(pd.to_datetime(ud[cut:]))
        train_df = pool[pool["date"].isin(train_dates)].copy()
        valid_df = pool[pool["date"].isin(valid_dates)].copy()
    if train_df.empty or valid_df.empty:
        raise RuntimeError(f"failed split before {month_start.date()}")
    return train_df, valid_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Rolling retrain for 5d/10d-only LSTM.")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--seq-len", type=int, required=True)
    parser.add_argument("--train-window-months", type=int, default=18)
    parser.add_argument("--valid-window-months", type=int, default=2)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--w5", type=float, default=1.0)
    parser.add_argument("--w10", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report", required=True)
    parser.add_argument(
        "--save-oos-parquet",
        default="",
        help="可选：保存 OOS 逐样本预测（date/symbol/label/pred）到 parquet，用于 daily-CS 统一评估",
    )
    args = parser.parse_args()

    _set_seed(args.seed)
    cfg = TrainConfig(
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
        w5=args.w5,
        w10=args.w10,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ddir = Path(args.dataset_dir)
    train_df = pd.read_parquet(ddir / "train.parquet")
    valid_df = pd.read_parquet(ddir / "valid.parquet")
    test_df = pd.read_parquet(ddir / "test.parquet")
    full = pd.concat([train_df, valid_df, test_df], ignore_index=True)
    full["date"] = pd.to_datetime(full["date"])
    full["symbol"] = full["symbol"].astype(str)
    full = full.sort_values(["date", "symbol"]).reset_index(drop=True)

    eval_df = test_df.copy()
    eval_df["date"] = pd.to_datetime(eval_df["date"])
    eval_df["symbol"] = eval_df["symbol"].astype(str)
    eval_df = eval_df.sort_values(["date", "symbol"]).reset_index(drop=True)
    months = sorted(eval_df["date"].dt.to_period("M").unique())

    oos_rows: list[pd.DataFrame] = []
    month_logs: list[dict[str, object]] = []
    total_train_sec = 0.0

    for i, m in enumerate(months):
        month = str(m)
        mstart = pd.Period(month, freq="M").start_time
        mdf = eval_df[eval_df["date"].dt.to_period("M") == m].copy()
        if mdf.empty:
            continue
        print(f"\n=== month {month} ===")
        tr_df, va_df = _select_train_valid_for_month(
            full,
            month_start=mstart,
            train_window_months=args.train_window_months,
            valid_window_months=args.valid_window_months,
        )
        print(
            f"train_rows={len(tr_df)} valid_rows={len(va_df)} month_rows={len(mdf)} "
            f"train_range=[{tr_df['date'].min().date()}..{tr_df['date'].max().date()}]"
        )

        _set_seed(args.seed + i)
        x_tr, y_tr = _extract_xy(tr_df, FEATURES_DIM19, args.seq_len)
        x_va, y_va = _extract_xy(va_df, FEATURES_DIM19, args.seq_len)
        x_mo, y_mo = _extract_xy(mdf, FEATURES_DIM19, args.seq_len)

        model, val_met, epochs, train_sec = _train_one(x_tr, y_tr, x_va, y_va, cfg, device)
        total_train_sec += float(train_sec)
        p_mo = _predict(model, x_mo, cfg.batch_size, device)
        m_met = _metrics(p_mo, y_mo)
        print(f"month_raw_avg_ic_5_10={m_met['avg_ic_5_10']:.4f}")

        out = mdf[["date", "symbol"] + LABEL_COLS].copy()
        out["pred_5d"] = p_mo[:, 0]
        out["pred_10d"] = p_mo[:, 1]
        oos_rows.append(out)

        month_logs.append(
            {
                "month": month,
                "month_rows": int(len(mdf)),
                "train_rows": int(len(tr_df)),
                "valid_rows": int(len(va_df)),
                "epochs_ran": int(epochs),
                "train_seconds": float(train_sec),
                "valid_avg_ic_5_10": float(val_met["avg_ic_5_10"]),
                "month_avg_ic_5_10": float(m_met["avg_ic_5_10"]),
                "month_ic_5d": float(m_met["ic_5d"]),
                "month_ic_10d": float(m_met["ic_10d"]),
            }
        )

    if not oos_rows:
        raise RuntimeError("no oos predictions produced")

    oos = pd.concat(oos_rows, ignore_index=True)
    y = oos[LABEL_COLS].to_numpy(dtype=float, copy=False)
    p = oos[PRED_COLS].to_numpy(dtype=float, copy=False)
    oos_met = _metrics(p, y)

    out = {
        "config": {
            "dataset_dir": str(ddir),
            "seq_len": int(args.seq_len),
            "features": FEATURES_DIM19,
            "horizons": [5, 10],
            "train_window_months": int(args.train_window_months),
            "valid_window_months": int(args.valid_window_months),
            "hidden_size": int(args.hidden_size),
            "num_layers": int(args.num_layers),
            "dropout": float(args.dropout),
            "lr": float(args.lr),
            "batch_size": int(args.batch_size),
            "max_epochs": int(args.max_epochs),
            "patience": int(args.patience),
            "loss_weights": {"5d": float(args.w5), "10d": float(args.w10)},
            "seed": int(args.seed),
            "device": str(device),
            "months": [str(m) for m in months],
        },
        "raw_oos_metrics_h2": oos_met,
        "monthly_logs": month_logs,
        "total_train_seconds": float(total_train_sec),
    }

    if args.save_oos_parquet:
        oos_path = Path(args.save_oos_parquet)
        oos_path.parent.mkdir(parents=True, exist_ok=True)
        oos.to_parquet(oos_path, index=False)
        out["oos_predictions_path"] = str(oos_path)
        print(f"Saved OOS parquet: {oos_path}")

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved report: {report}")


if __name__ == "__main__":
    main()
