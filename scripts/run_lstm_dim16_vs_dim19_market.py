#!/usr/bin/env python
"""Compare 16-dim baseline features vs 19-dim (16 + market state) on same hyperparameters.

This is an experiment-specific script, not the canonical main-line schema entry.
Primary 3d/5d/10d schema changes should land in `ashare_lab.trend_schema` first.
"""

from __future__ import annotations

import argparse
import json
import random
import time
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
from ashare_lab.models.transformer import compute_mtl_loss

DIM16 = [
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
]
MARKET3 = ["market_mom_5d", "market_vol_20d", "market_amount_z20"]
DIM19 = DIM16 + MARKET3

LABEL_COLS = ["label_3d", "label_5d", "label_10d"]


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _load_split(path: Path, features: list[str], seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_parquet(path)
    cols = [f"{b}_t{t}" for t in range(seq_len) for b in features]
    x = df[cols].to_numpy(dtype=np.float32, copy=False).reshape(len(df), seq_len, len(features))
    x = np.nan_to_num(x, nan=0.0)
    y = df[LABEL_COLS].to_numpy(dtype=np.float32, copy=False)
    return x, y


class MtlLSTM(nn.Module):
    def __init__(self, *, input_dim: int, hidden_size: int, num_layers: int, dropout: float) -> None:
        super().__init__()
        self.loss_weights = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float32)
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

    def forward(self, x: torch.Tensor, labels: torch.Tensor | None = None):
        out, _ = self.lstm(x)
        h = self.norm(out[:, -1, :])
        preds = {
            "pred_3d": self.head_3d(h).squeeze(-1),
            "pred_5d": self.head_5d(h).squeeze(-1),
            "pred_10d": self.head_10d(h).squeeze(-1),
        }
        if labels is None:
            return preds
        total, head = compute_mtl_loss(preds, labels, self.loss_weights.to(labels.device))
        return preds, {"total": total, **head}


def _summarize(preds: list[np.ndarray], labels: list[np.ndarray]) -> dict[str, float]:
    ic = [information_coefficient(preds[i], labels[i]) for i in range(3)]
    ric = [rank_information_coefficient(preds[i], labels[i]) for i in range(3)]
    mae = [mean_absolute_error(preds[i], labels[i]) for i in range(3)]
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


@torch.no_grad()
def _eval_model(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    p = [[], [], []]
    y = [[], [], []]
    for xb, yb in loader:
        out = model(xb.to(device))
        p[0].append(out["pred_3d"].cpu().numpy())
        p[1].append(out["pred_5d"].cpu().numpy())
        p[2].append(out["pred_10d"].cpu().numpy())
        y[0].append(yb[:, 0].numpy())
        y[1].append(yb[:, 1].numpy())
        y[2].append(yb[:, 2].numpy())
    preds = [np.concatenate(p[i]) for i in range(3)]
    labels = [np.concatenate(y[i]) for i in range(3)]
    return _summarize(preds, labels)


def _train_one(
    name: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    *,
    hidden_size: int,
    num_layers: int,
    dropout: float,
    lr: float,
    batch_size: int,
    max_epochs: int,
    patience: int,
    device: torch.device,
) -> dict[str, object]:
    model = MtlLSTM(
        input_dim=x_train.shape[2],
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=torch.cuda.is_available(),
    )
    valid_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_valid), torch.from_numpy(y_valid)),
        batch_size=batch_size,
        shuffle=False,
        pin_memory=torch.cuda.is_available(),
    )
    test_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_test), torch.from_numpy(y_test)),
        batch_size=batch_size,
        shuffle=False,
        pin_memory=torch.cuda.is_available(),
    )

    best_ic = -1e9
    best_state = None
    stale = 0
    history: list[dict[str, float]] = []

    t0 = time.perf_counter()
    for epoch in range(1, max_epochs + 1):
        model.train()
        total = 0.0
        for xb, yb in train_loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            _, losses = model(xb, yb)
            losses["total"].backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += float(losses["total"].item())

        val = _eval_model(model, valid_loader, device)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": total / max(1, len(train_loader)),
                "valid_avg_ic": float(val["avg_ic"]),
            }
        )
        print(
            f"[{name}] epoch={epoch:02d} train_loss={history[-1]['train_loss']:.5f} "
            f"val_ic={val['avg_ic']:.4f} val_rank_ic={val['avg_rank_ic']:.4f}"
        )

        if val["avg_ic"] > best_ic:
            best_ic = float(val["avg_ic"])
            stale = 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1

        if stale >= patience:
            print(f"[{name}] early_stop epoch={epoch} best_val_ic={best_ic:.4f}")
            break

    train_sec = time.perf_counter() - t0
    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device)

    valid_best = _eval_model(model, valid_loader, device)
    t1 = time.perf_counter()
    test = _eval_model(model, test_loader, device)
    infer_sec = time.perf_counter() - t1

    ckpt = Path(f"models/best_lstm_sector70_{name}.pt")
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict()}, ckpt)

    return {
        "name": name,
        "input_dim": int(x_train.shape[2]),
        "best_valid_ic": float(best_ic),
        "train_seconds": float(train_sec),
        "inference_seconds_test": float(infer_sec),
        "valid_metrics": valid_best,
        "test_metrics": test,
        "checkpoint": str(ckpt),
        "epochs_ran": int(len(history)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare dim16 baseline vs dim19 with market-state features.")
    parser.add_argument("--dataset-dir", default="data/datasets/lstm_sector70_19d_mkt_20210101_20260120")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report", default="output/reports/lstm_sector70_dim16_vs_dim19_mkt_20260303.json")
    args = parser.parse_args()

    _set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ddir = Path(args.dataset_dir)

    x16_tr, y_tr = _load_split(ddir / "train.parquet", DIM16, args.seq_len)
    x16_va, y_va = _load_split(ddir / "valid.parquet", DIM16, args.seq_len)
    x16_te, y_te = _load_split(ddir / "test.parquet", DIM16, args.seq_len)

    x19_tr, _ = _load_split(ddir / "train.parquet", DIM19, args.seq_len)
    x19_va, _ = _load_split(ddir / "valid.parquet", DIM19, args.seq_len)
    x19_te, _ = _load_split(ddir / "test.parquet", DIM19, args.seq_len)

    r16 = _train_one(
        "dim16_on19ds",
        x16_tr,
        y_tr,
        x16_va,
        y_va,
        x16_te,
        y_te,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
        device=device,
    )
    r19 = _train_one(
        "dim19_mkt",
        x19_tr,
        y_tr,
        x19_va,
        y_va,
        x19_te,
        y_te,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
        device=device,
    )

    out = {
        "config": {
            "dataset_dir": str(ddir),
            "seq_len": int(args.seq_len),
            "hidden_size": int(args.hidden_size),
            "num_layers": int(args.num_layers),
            "dropout": float(args.dropout),
            "learning_rate": float(args.lr),
            "batch_size": int(args.batch_size),
            "max_epochs": int(args.max_epochs),
            "patience": int(args.patience),
            "seed": int(args.seed),
            "device": str(device),
            "train_rows": int(len(y_tr)),
            "valid_rows": int(len(y_va)),
            "test_rows": int(len(y_te)),
        },
        "dim16_on19ds": r16,
        "dim19_mkt": r19,
        "delta_valid_best_ic_19_minus_16": float(r19["best_valid_ic"] - r16["best_valid_ic"]),
        "delta_test_avg_ic_19_minus_16": float(r19["test_metrics"]["avg_ic"] - r16["test_metrics"]["avg_ic"]),
        "delta_test_avg_rank_ic_19_minus_16": float(
            r19["test_metrics"]["avg_rank_ic"] - r16["test_metrics"]["avg_rank_ic"]
        ),
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
