#!/usr/bin/env python
"""Rolling retrain (18m window) + horizon-wise sign calibration for dim19 market-state LSTM."""

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
import torch.nn.functional as F
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

LABEL_COLS = ["label_3d", "label_5d", "label_10d"]
PRED_COLS = ["pred_3d", "pred_5d", "pred_10d"]
LOSS_TYPES = ("l1", "ic_aware", "rank_aware", "ic_rank_aware")
FEATURE_MODES = ("dim19", "auto")
BACKBONES = ("lstm", "transformer")
LR_SCHEDULERS = ("none", "cosine", "cosine_warm_restart", "plateau")
OPTIMIZERS = ("adamw", "adam")
NORM_TYPES = ("layernorm", "rmsnorm")
GRAD_CLIP_MODES = ("none", "norm", "value")


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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


def _extract_xy(df: pd.DataFrame, feature_bases: list[str], seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    x_cols = [f"{b}_t{t}" for t in range(seq_len) for b in feature_bases]
    x = df[x_cols].to_numpy(dtype=np.float32, copy=False).reshape(len(df), seq_len, len(feature_bases))
    x = np.nan_to_num(x, nan=0.0)
    y = df[LABEL_COLS].to_numpy(dtype=np.float32, copy=False)
    return x, y


def _infer_feature_bases(df: pd.DataFrame, seq_len: int) -> list[str]:
    bases: list[str] = []
    seen: set[str] = set()
    for col in df.columns:
        if not col.endswith("_t0"):
            continue
        base = col[:-3]
        if not base or base in seen:
            continue
        required = [f"{base}_t{t}" for t in range(seq_len)]
        if all(c in df.columns for c in required):
            bases.append(base)
            seen.add(base)
    if not bases:
        raise ValueError("no feature columns inferred from dataset (expected pattern '*_t0')")
    return bases


def _masked_l1_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() == 0:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    return torch.mean(torch.abs(pred[mask] - target[mask]))


def _pearson_corr(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() < 2:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    p = pred[mask]
    t = target[mask]
    p = p - p.mean()
    t = t - t.mean()
    denom = torch.sqrt((p.square().sum() * t.square().sum()).clamp_min(1e-8))
    return (p * t).sum() / denom


def _pairwise_rank_logistic_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() < 2:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    p = pred[mask]
    t = target[mask]

    pdiff = p.unsqueeze(1) - p.unsqueeze(0)
    tdiff = t.unsqueeze(1) - t.unsqueeze(0)
    upper = torch.triu(torch.ones_like(tdiff, dtype=torch.bool), diagonal=1)
    pair_mask = upper & (tdiff != 0)
    if pair_mask.sum() == 0:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)

    sign = torch.sign(tdiff[pair_mask])
    margin = sign * pdiff[pair_mask]
    return F.softplus(-margin).mean()


def _compute_head_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    *,
    loss_type: str,
    loss_alpha: float,
    ic_rank_beta: float,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    l1 = _masked_l1_loss(pred, target)
    ic_loss = 1.0 - _pearson_corr(pred, target)
    rank_loss = _pairwise_rank_logistic_loss(pred, target)

    if loss_type == "l1":
        total = l1
    elif loss_type == "ic_aware":
        total = loss_alpha * l1 + (1.0 - loss_alpha) * ic_loss
    elif loss_type == "rank_aware":
        total = loss_alpha * l1 + (1.0 - loss_alpha) * rank_loss
    elif loss_type == "ic_rank_aware":
        total = loss_alpha * l1 + (1.0 - loss_alpha) * (ic_rank_beta * ic_loss + (1.0 - ic_rank_beta) * rank_loss)
    else:
        raise ValueError(f"unsupported loss_type: {loss_type}")

    return total, {"l1": l1, "ic_loss": ic_loss, "rank_loss": rank_loss}


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-8) -> None:
        super().__init__()
        self.eps = float(eps)
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rms = torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return x * rms * self.weight


def _build_norm(dim: int, norm_type: str, norm_eps: float) -> nn.Module:
    if norm_type == "layernorm":
        return nn.LayerNorm(dim, eps=norm_eps)
    if norm_type == "rmsnorm":
        return RMSNorm(dim, eps=norm_eps)
    raise ValueError(f"unsupported norm_type: {norm_type}")


class MtlLSTM(nn.Module):
    def __init__(
        self,
        *,
        input_dim: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
        loss_weights: tuple[float, float, float],
        loss_type: str,
        loss_alpha: float,
        ic_rank_beta: float,
        norm_type: str,
        norm_eps: float,
    ) -> None:
        super().__init__()
        self.loss_weights = torch.tensor(loss_weights, dtype=torch.float32)
        self.loss_type = loss_type
        self.loss_alpha = float(loss_alpha)
        self.ic_rank_beta = float(ic_rank_beta)
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.norm = _build_norm(hidden_size, norm_type, norm_eps)

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
        weights = self.loss_weights.to(device=labels.device, dtype=labels.dtype)
        per_head: list[torch.Tensor] = []
        details: dict[str, torch.Tensor] = {}

        for idx, pred_key in enumerate(PRED_COLS):
            head_total, head_parts = _compute_head_loss(
                preds[pred_key],
                labels[:, idx],
                loss_type=self.loss_type,
                loss_alpha=self.loss_alpha,
                ic_rank_beta=self.ic_rank_beta,
            )
            per_head.append(head_total)
            horizon = pred_key.replace("pred_", "")
            details[f"obj_{horizon}"] = head_total
            details[f"l1_{horizon}"] = head_parts["l1"]
            details[f"ic_loss_{horizon}"] = head_parts["ic_loss"]
            details[f"rank_loss_{horizon}"] = head_parts["rank_loss"]

        total = torch.stack(per_head).mul(weights).sum()
        return preds, {"total": total, **details}


class MtlTransformer(nn.Module):
    def __init__(
        self,
        *,
        input_dim: int,
        seq_len: int,
        d_model: int,
        num_layers: int,
        n_heads: int,
        d_ff: int,
        dropout: float,
        loss_weights: tuple[float, float, float],
        loss_type: str,
        loss_alpha: float,
        ic_rank_beta: float,
        norm_type: str,
        norm_eps: float,
    ) -> None:
        super().__init__()
        self.loss_weights = torch.tensor(loss_weights, dtype=torch.float32)
        self.loss_type = loss_type
        self.loss_alpha = float(loss_alpha)
        self.ic_rank_beta = float(ic_rank_beta)

        if d_model % n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")

        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_embed = nn.Parameter(torch.zeros(1, seq_len, d_model))
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.norm = _build_norm(d_model, norm_type, norm_eps)

        def _head() -> nn.Module:
            return nn.Sequential(
                nn.Linear(d_model, d_model // 2),
                nn.GELU(),
                nn.Linear(d_model // 2, 1),
            )

        self.head_3d = _head()
        self.head_5d = _head()
        self.head_10d = _head()

    def forward(self, x: torch.Tensor, labels: torch.Tensor | None = None):
        h = self.input_proj(x)
        h = h + self.pos_embed[:, : h.shape[1], :]
        h = self.encoder(h)
        h = self.norm(h[:, -1, :])
        preds = {
            "pred_3d": self.head_3d(h).squeeze(-1),
            "pred_5d": self.head_5d(h).squeeze(-1),
            "pred_10d": self.head_10d(h).squeeze(-1),
        }
        if labels is None:
            return preds
        weights = self.loss_weights.to(device=labels.device, dtype=labels.dtype)
        per_head: list[torch.Tensor] = []
        details: dict[str, torch.Tensor] = {}

        for idx, pred_key in enumerate(PRED_COLS):
            head_total, head_parts = _compute_head_loss(
                preds[pred_key],
                labels[:, idx],
                loss_type=self.loss_type,
                loss_alpha=self.loss_alpha,
                ic_rank_beta=self.ic_rank_beta,
            )
            per_head.append(head_total)
            horizon = pred_key.replace("pred_", "")
            details[f"obj_{horizon}"] = head_total
            details[f"l1_{horizon}"] = head_parts["l1"]
            details[f"ic_loss_{horizon}"] = head_parts["ic_loss"]
            details[f"rank_loss_{horizon}"] = head_parts["rank_loss"]

        total = torch.stack(per_head).mul(weights).sum()
        return preds, {"total": total, **details}


@torch.no_grad()
def _predict(model: nn.Module, x: np.ndarray, batch_size: int, device: torch.device) -> np.ndarray:
    loader = DataLoader(TensorDataset(torch.from_numpy(x)), batch_size=batch_size, shuffle=False)
    model.eval()
    rows: list[np.ndarray] = []
    for (xb,) in loader:
        out = model(xb.to(device))
        rows.append(
            torch.stack([out["pred_3d"], out["pred_5d"], out["pred_10d"]], dim=1).detach().cpu().numpy()
        )
    return np.concatenate(rows, axis=0)


@torch.no_grad()
def _eval(model: nn.Module, x: np.ndarray, y: np.ndarray, batch_size: int, device: torch.device) -> dict[str, float]:
    pred = _predict(model, x, batch_size=batch_size, device=device)
    return _metrics(pred, y)


@dataclass(frozen=True)
class TrainConfig:
    backbone: str
    hidden_size: int
    num_layers: int
    d_model: int
    n_heads: int
    d_ff: int
    seq_len: int
    dropout: float
    lr: float
    optimizer: str
    weight_decay: float
    lr_scheduler: str
    lr_min: float
    cosine_t_max: int
    warm_restart_t0: int
    warm_restart_t_mult: int
    plateau_factor: float
    plateau_patience: int
    grad_clip_mode: str
    grad_clip_threshold: float
    norm_type: str
    norm_eps: float
    batch_size: int
    max_epochs: int
    patience: int
    loss_weights: tuple[float, float, float]
    loss_type: str
    loss_alpha: float
    ic_rank_beta: float


def _train_one_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    cfg: TrainConfig,
    device: torch.device,
) -> tuple[nn.Module, dict[str, float], int, float]:
    if cfg.backbone == "lstm":
        model = MtlLSTM(
            input_dim=x_train.shape[2],
            hidden_size=cfg.hidden_size,
            num_layers=cfg.num_layers,
            dropout=cfg.dropout,
            loss_weights=cfg.loss_weights,
            loss_type=cfg.loss_type,
            loss_alpha=cfg.loss_alpha,
            ic_rank_beta=cfg.ic_rank_beta,
            norm_type=cfg.norm_type,
            norm_eps=cfg.norm_eps,
        ).to(device)
    elif cfg.backbone == "transformer":
        model = MtlTransformer(
            input_dim=x_train.shape[2],
            seq_len=cfg.seq_len,
            d_model=cfg.d_model,
            num_layers=cfg.num_layers,
            n_heads=cfg.n_heads,
            d_ff=cfg.d_ff,
            dropout=cfg.dropout,
            loss_weights=cfg.loss_weights,
            loss_type=cfg.loss_type,
            loss_alpha=cfg.loss_alpha,
            ic_rank_beta=cfg.ic_rank_beta,
            norm_type=cfg.norm_type,
            norm_eps=cfg.norm_eps,
        ).to(device)
    else:
        raise ValueError(f"unsupported backbone: {cfg.backbone}")

    if cfg.optimizer == "adamw":
        opt: torch.optim.Optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=cfg.lr,
            weight_decay=cfg.weight_decay,
        )
    elif cfg.optimizer == "adam":
        opt = torch.optim.Adam(
            model.parameters(),
            lr=cfg.lr,
            weight_decay=cfg.weight_decay,
        )
    else:
        raise ValueError(f"unsupported optimizer: {cfg.optimizer}")

    scheduler: torch.optim.lr_scheduler.LRScheduler | torch.optim.lr_scheduler.ReduceLROnPlateau | None = None
    if cfg.lr_scheduler == "cosine":
        t_max = int(cfg.cosine_t_max)
        if t_max <= 0:
            t_max = max(1, cfg.max_epochs if cfg.max_epochs > 0 else 40)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            opt,
            T_max=t_max,
            eta_min=float(cfg.lr_min),
        )
    elif cfg.lr_scheduler == "cosine_warm_restart":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            opt,
            T_0=max(1, int(cfg.warm_restart_t0)),
            T_mult=max(1, int(cfg.warm_restart_t_mult)),
            eta_min=float(cfg.lr_min),
        )
    elif cfg.lr_scheduler == "plateau":
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt,
            mode="max",
            factor=float(cfg.plateau_factor),
            patience=int(cfg.plateau_patience),
            min_lr=float(cfg.lr_min),
        )

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
        batch_size=cfg.batch_size,
        shuffle=True,
        pin_memory=torch.cuda.is_available(),
    )
    valid_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_valid), torch.from_numpy(y_valid)),
        batch_size=cfg.batch_size,
        shuffle=False,
        pin_memory=torch.cuda.is_available(),
    )

    best_ic = -1e9
    best_state = None
    stale = 0
    epochs = 0
    t0 = time.perf_counter()

    ep = 0
    while True:
        ep += 1
        epochs = ep
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            _, losses = model(xb, yb)
            losses["total"].backward()
            if cfg.grad_clip_mode == "norm" and cfg.grad_clip_threshold > 0:
                nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip_threshold)
            elif cfg.grad_clip_mode == "value" and cfg.grad_clip_threshold > 0:
                nn.utils.clip_grad_value_(model.parameters(), cfg.grad_clip_threshold)
            opt.step()
            total_loss += float(losses["total"].item())

        # valid metrics
        model.eval()
        vp = [[], [], []]
        vy = [[], [], []]
        for xb, yb in valid_loader:
            out = model(xb.to(device))
            vp[0].append(out["pred_3d"].detach().cpu().numpy())
            vp[1].append(out["pred_5d"].detach().cpu().numpy())
            vp[2].append(out["pred_10d"].detach().cpu().numpy())
            vy[0].append(yb[:, 0].numpy())
            vy[1].append(yb[:, 1].numpy())
            vy[2].append(yb[:, 2].numpy())
        pred = np.stack([np.concatenate(vp[i]) for i in range(3)], axis=1)
        yv = np.stack([np.concatenate(vy[i]) for i in range(3)], axis=1)
        met = _metrics(pred, yv)
        if scheduler is not None:
            if cfg.lr_scheduler == "plateau":
                # plateau scheduler reacts to validation metric.
                scheduler.step(float(met["avg_ic"]))
            else:
                scheduler.step()

        curr_lr = float(opt.param_groups[0]["lr"])
        print(
            f"epoch={ep:02d} train_loss={total_loss/max(1,len(train_loader)):.5f} "
            f"val_ic={met['avg_ic']:.4f} val_rank_ic={met['avg_rank_ic']:.4f} lr={curr_lr:.2e}"
        )

        if met["avg_ic"] > best_ic:
            best_ic = float(met["avg_ic"])
            stale = 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1

        if stale >= cfg.patience:
            break
        if cfg.max_epochs > 0 and ep >= cfg.max_epochs:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device)
    valid_best = _eval(model, x_valid, y_valid, cfg.batch_size, device)
    train_seconds = time.perf_counter() - t0
    return model, valid_best, epochs, float(train_seconds)


def _horizon_sign_with_threshold(score: float, threshold: float) -> int:
    if not np.isfinite(score):
        return 1
    if abs(score) < threshold:
        return 1
    return 1 if score >= 0 else -1


def _choose_sign_consensus(hist_ic: float, val_ic: float, threshold: float) -> tuple[int, str]:
    """Conservative sign decision to reduce false flips.

    Rules:
      1) If both history and validation IC are available:
         - flip only when both exceed threshold and have the same sign.
         - otherwise keep sign=+1 (no flip).
      2) If only one score is available:
         - use thresholded sign from that score.
      3) If neither is available:
         - keep sign=+1.
    """
    hist_ok = np.isfinite(hist_ic)
    val_ok = np.isfinite(val_ic)

    if hist_ok and val_ok:
        if abs(hist_ic) >= threshold and abs(val_ic) >= threshold and np.sign(hist_ic) == np.sign(val_ic):
            return (1 if hist_ic >= 0 else -1), "hist_val_consensus"
        return 1, "no_consensus_or_low_conf"

    if hist_ok:
        return _horizon_sign_with_threshold(hist_ic, threshold), "hist_only"
    if val_ok:
        return _horizon_sign_with_threshold(val_ic, threshold), "val_only"
    return 1, "no_signal"


def _select_train_valid_for_month(
    train_pool: pd.DataFrame,
    month_start: pd.Timestamp,
    *,
    train_window_months: int,
    valid_window_months: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    left = month_start - pd.DateOffset(months=train_window_months)
    pool = train_pool[(train_pool["date"] >= left) & (train_pool["date"] < month_start)].copy()
    if pool.empty:
        raise RuntimeError(f"empty rolling pool before {month_start.date()}")

    valid_left = month_start - pd.DateOffset(months=valid_window_months)
    valid_df = pool[(pool["date"] >= valid_left) & (pool["date"] < month_start)].copy()
    train_df = pool[pool["date"] < valid_left].copy()

    if train_df.empty or valid_df.empty:
        # fallback date split if month-window split is too short
        ud = np.array(sorted(pool["date"].unique()))
        cut = max(1, int(len(ud) * 0.85))
        train_dates = set(pd.to_datetime(ud[:cut]))
        valid_dates = set(pd.to_datetime(ud[cut:]))
        train_df = pool[pool["date"].isin(train_dates)].copy()
        valid_df = pool[pool["date"].isin(valid_dates)].copy()
        if train_df.empty or valid_df.empty:
            raise RuntimeError(f"unable to split train/valid before {month_start.date()}")

    return train_df, valid_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Rolling retrain + horizon sign calibration.")
    parser.add_argument("--dataset-dir", default="data/datasets/lstm_sector70_19d_mkt_20210101_20260120")
    parser.add_argument("--backbone", choices=list(BACKBONES), default="lstm")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--train-window-months", type=int, default=18)
    parser.add_argument("--valid-window-months", type=int, default=2)
    parser.add_argument("--calibration-months", type=int, default=3)
    parser.add_argument("--sign-threshold", type=float, default=0.02)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--d-model", type=int, default=64, help="transformer 隐层维度")
    parser.add_argument("--n-heads", type=int, default=4, help="transformer 注意力头数")
    parser.add_argument("--d-ff", type=int, default=128, help="transformer 前馈层维度")
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--optimizer", choices=list(OPTIMIZERS), default="adamw")
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--lr-scheduler", choices=list(LR_SCHEDULERS), default="none")
    parser.add_argument("--lr-min", type=float, default=1e-6, help="调度器最低学习率")
    parser.add_argument("--cosine-t-max", type=int, default=20, help="cosine 半周期长度（epoch）")
    parser.add_argument("--warm-restart-t0", type=int, default=8, help="cosine warm restart 初始周期长度")
    parser.add_argument("--warm-restart-t-mult", type=int, default=2, help="cosine warm restart 周期倍增系数")
    parser.add_argument("--plateau-factor", type=float, default=0.5, help="plateau 学习率衰减系数")
    parser.add_argument("--plateau-patience", type=int, default=3, help="plateau 指标无提升容忍轮数")
    parser.add_argument("--grad-clip-mode", choices=list(GRAD_CLIP_MODES), default="norm")
    parser.add_argument("--grad-clip-threshold", type=float, default=1.0)
    parser.add_argument("--norm-type", choices=list(NORM_TYPES), default="layernorm")
    parser.add_argument("--norm-eps", type=float, default=1e-8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-epochs", type=int, default=40, help="最大训练轮数；<=0 表示不设上限，仅靠早停")
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--w3", type=float, default=1.0)
    parser.add_argument("--w5", type=float, default=1.0)
    parser.add_argument("--w10", type=float, default=1.0)
    parser.add_argument("--loss-type", choices=list(LOSS_TYPES), default="l1")
    parser.add_argument("--loss-alpha", type=float, default=0.3, help="混合损失里 L1 占比，范围 [0,1]")
    parser.add_argument(
        "--feature-mode",
        choices=list(FEATURE_MODES),
        default="dim19",
        help="dim19: 使用固定19维；auto: 从数据集自动推断全部特征",
    )
    parser.add_argument(
        "--ic-rank-beta",
        type=float,
        default=0.5,
        help="仅在 ic_rank_aware 下生效：非L1部分中 IC loss 占比，范围 [0,1]",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-monthly-checkpoints", action="store_true")
    parser.add_argument(
        "--save-oos-parquet",
        default="",
        help="可选：保存 OOS 逐样本预测（含 raw/cal）到 parquet，用于 daily-CS 统一评估",
    )
    parser.add_argument(
        "--report",
        default="output/reports/lstm_dim19_rolling18m_horizoncal_20260303.json",
    )
    args = parser.parse_args()

    if args.w3 < 0 or args.w5 < 0 or args.w10 < 0 or (args.w3 + args.w5 + args.w10) <= 0:
        raise ValueError("loss weights must be non-negative and sum to > 0")
    if not (0.0 <= args.loss_alpha <= 1.0):
        raise ValueError("loss_alpha must be within [0,1]")
    if not (0.0 <= args.ic_rank_beta <= 1.0):
        raise ValueError("ic_rank_beta must be within [0,1]")
    if args.backbone == "transformer" and args.d_model % args.n_heads != 0:
        raise ValueError("for transformer: d_model must be divisible by n_heads")
    if args.weight_decay < 0:
        raise ValueError("weight_decay must be >= 0")
    if args.lr_min < 0:
        raise ValueError("lr_min must be >= 0")
    if args.cosine_t_max == 0:
        raise ValueError("cosine_t_max must be != 0")
    if args.warm_restart_t0 <= 0:
        raise ValueError("warm_restart_t0 must be > 0")
    if args.warm_restart_t_mult < 1:
        raise ValueError("warm_restart_t_mult must be >= 1")
    if not (0.0 < args.plateau_factor < 1.0):
        raise ValueError("plateau_factor must be in (0,1)")
    if args.plateau_patience < 0:
        raise ValueError("plateau_patience must be >= 0")
    if args.grad_clip_threshold < 0:
        raise ValueError("grad_clip_threshold must be >= 0")
    if args.norm_eps <= 0:
        raise ValueError("norm_eps must be > 0")

    _set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cfg = TrainConfig(
        backbone=str(args.backbone),
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        d_model=args.d_model,
        n_heads=args.n_heads,
        d_ff=args.d_ff,
        seq_len=args.seq_len,
        dropout=args.dropout,
        lr=args.lr,
        optimizer=str(args.optimizer),
        weight_decay=float(args.weight_decay),
        lr_scheduler=str(args.lr_scheduler),
        lr_min=float(args.lr_min),
        cosine_t_max=int(args.cosine_t_max),
        warm_restart_t0=int(args.warm_restart_t0),
        warm_restart_t_mult=int(args.warm_restart_t_mult),
        plateau_factor=float(args.plateau_factor),
        plateau_patience=int(args.plateau_patience),
        grad_clip_mode=str(args.grad_clip_mode),
        grad_clip_threshold=float(args.grad_clip_threshold),
        norm_type=str(args.norm_type),
        norm_eps=float(args.norm_eps),
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
        loss_weights=(float(args.w3), float(args.w5), float(args.w10)),
        loss_type=str(args.loss_type),
        loss_alpha=float(args.loss_alpha),
        ic_rank_beta=float(args.ic_rank_beta),
    )

    ddir = Path(args.dataset_dir)
    train_df = pd.read_parquet(ddir / "train.parquet")
    valid_df = pd.read_parquet(ddir / "valid.parquet")
    test_df = pd.read_parquet(ddir / "test.parquet")
    full_df = pd.concat([train_df, valid_df, test_df], ignore_index=True)
    full_df["date"] = pd.to_datetime(full_df["date"])
    full_df["symbol"] = full_df["symbol"].astype(str)
    full_df = full_df.sort_values(["date", "symbol"]).reset_index(drop=True)

    if args.feature_mode == "dim19":
        feature_bases = list(FEATURES_DIM19)
    else:
        feature_bases = _infer_feature_bases(train_df, args.seq_len)

    required_x = [f"{b}_t{t}" for b in feature_bases for t in range(args.seq_len)]
    missing_x = [c for c in required_x if c not in full_df.columns]
    if missing_x:
        preview = ", ".join(missing_x[:5])
        raise ValueError(f"dataset missing required feature columns (showing up to 5): {preview}")

    eval_df = test_df.copy()
    eval_df["date"] = pd.to_datetime(eval_df["date"])
    eval_df["symbol"] = eval_df["symbol"].astype(str)
    eval_df = eval_df.sort_values(["date", "symbol"]).reset_index(drop=True)
    months = sorted(eval_df["date"].dt.to_period("M").unique())

    # history for walk-forward calibration uses realized OOS predictions from prior months
    hist_rows: list[pd.DataFrame] = []
    oos_rows: list[pd.DataFrame] = []
    month_logs: list[dict[str, object]] = []

    ckpt_dir = Path("models/rolling_dim19")
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    for i, m in enumerate(months):
        month = str(m)
        month_start = pd.Period(month, freq="M").start_time
        month_mask = eval_df["date"].dt.to_period("M") == m
        month_df = eval_df.loc[month_mask].copy()
        if month_df.empty:
            continue

        print(f"\n=== month {month} ===")
        tr_df, va_df = _select_train_valid_for_month(
            full_df,
            month_start=month_start,
            train_window_months=args.train_window_months,
            valid_window_months=args.valid_window_months,
        )
        print(
            f"train_rows={len(tr_df)} valid_rows={len(va_df)} month_rows={len(month_df)} "
            f"train_range=[{tr_df['date'].min().date()}..{tr_df['date'].max().date()}]"
        )

        # month-specific seed for reproducibility and mild de-correlation
        _set_seed(args.seed + i)

        x_tr, y_tr = _extract_xy(tr_df, feature_bases, args.seq_len)
        x_va, y_va = _extract_xy(va_df, feature_bases, args.seq_len)
        x_mo, y_mo = _extract_xy(month_df, feature_bases, args.seq_len)

        model, val_metrics, epochs_ran, train_seconds = _train_one_model(x_tr, y_tr, x_va, y_va, cfg, device)
        pred_val = _predict(model, x_va, cfg.batch_size, device)
        pred_month = _predict(model, x_mo, cfg.batch_size, device)

        # build calibration score per horizon from trailing realized history
        hist_df = pd.concat(hist_rows, ignore_index=True) if hist_rows else pd.DataFrame()
        if not hist_df.empty:
            hist_df["date"] = pd.to_datetime(hist_df["date"])
            hist_left = month_start - pd.DateOffset(months=args.calibration_months)
            hist_use = hist_df[(hist_df["date"] >= hist_left) & (hist_df["date"] < month_start)].copy()
        else:
            hist_use = pd.DataFrame()

        signs: list[int] = []
        decisions: list[dict[str, float | int]] = []
        for h in range(3):
            val_ic = float(information_coefficient(pred_val[:, h], y_va[:, h]))
            hist_ic = float("nan")
            if not hist_use.empty:
                hist_ic = float(
                    information_coefficient(
                        hist_use[PRED_COLS[h]].to_numpy(dtype=float, copy=False),
                        hist_use[LABEL_COLS[h]].to_numpy(dtype=float, copy=False),
                    )
                )
            score = hist_ic if np.isfinite(hist_ic) else val_ic
            sign, reason = _choose_sign_consensus(hist_ic, val_ic, args.sign_threshold)
            signs.append(sign)
            decisions.append(
                {
                    "horizon": int([3, 5, 10][h]),
                    "val_ic": val_ic,
                    "hist_ic": hist_ic,
                    "score_used": float(score),
                    "sign": int(sign),
                    "rule": reason,
                }
            )

        pred_cal = pred_month.copy()
        for h in range(3):
            pred_cal[:, h] = signs[h] * pred_cal[:, h]

        month_raw = _metrics(pred_month, y_mo)
        month_cal = _metrics(pred_cal, y_mo)
        print(
            f"month_raw_avg_ic={month_raw['avg_ic']:.4f} month_cal_avg_ic={month_cal['avg_ic']:.4f} "
            f"signs={signs}"
        )

        month_out = month_df[["date", "symbol"] + LABEL_COLS].copy()
        for h, c in enumerate(PRED_COLS):
            month_out[c] = pred_month[:, h]
            month_out[f"{c}_cal"] = pred_cal[:, h]
        oos_rows.append(month_out)
        hist_rows.append(month_out[["date"] + LABEL_COLS + PRED_COLS].copy())

        if args.save_monthly_checkpoints:
            ckpt_path = ckpt_dir / f"best_dim19_{month}.pt"
            torch.save({"model_state_dict": model.state_dict()}, ckpt_path)
        month_logs.append(
            {
                "month": month,
                "month_rows": int(len(month_df)),
                "train_rows": int(len(tr_df)),
                "valid_rows": int(len(va_df)),
                "epochs_ran": int(epochs_ran),
                "train_seconds": float(train_seconds),
                "valid_avg_ic": float(val_metrics["avg_ic"]),
                "raw_avg_ic": float(month_raw["avg_ic"]),
                "cal_avg_ic": float(month_cal["avg_ic"]),
                "signs": signs,
                "decisions": decisions,
            }
        )

    if not oos_rows:
        raise RuntimeError("no out-of-sample predictions generated")

    oos = pd.concat(oos_rows, ignore_index=True)
    y = oos[LABEL_COLS].to_numpy(dtype=float, copy=False)
    raw = oos[PRED_COLS].to_numpy(dtype=float, copy=False)
    cal = oos[[f"{c}_cal" for c in PRED_COLS]].to_numpy(dtype=float, copy=False)

    raw_metrics = _metrics(raw, y)
    cal_metrics = _metrics(cal, y)

    out = {
        "config": {
            "dataset_dir": str(ddir),
            "backbone": str(args.backbone),
            "feature_mode": str(args.feature_mode),
            "features": feature_bases,
            "seq_len": int(args.seq_len),
            "train_window_months": int(args.train_window_months),
            "valid_window_months": int(args.valid_window_months),
            "calibration_months": int(args.calibration_months),
            "sign_threshold": float(args.sign_threshold),
            "hidden_size": int(args.hidden_size),
            "num_layers": int(args.num_layers),
            "d_model": int(args.d_model),
            "n_heads": int(args.n_heads),
            "d_ff": int(args.d_ff),
            "dropout": float(args.dropout),
            "lr": float(args.lr),
            "optimizer": str(args.optimizer),
            "weight_decay": float(args.weight_decay),
            "lr_scheduler": str(args.lr_scheduler),
            "lr_min": float(args.lr_min),
            "cosine_t_max": int(args.cosine_t_max),
            "warm_restart_t0": int(args.warm_restart_t0),
            "warm_restart_t_mult": int(args.warm_restart_t_mult),
            "plateau_factor": float(args.plateau_factor),
            "plateau_patience": int(args.plateau_patience),
            "grad_clip_mode": str(args.grad_clip_mode),
            "grad_clip_threshold": float(args.grad_clip_threshold),
            "norm_type": str(args.norm_type),
            "norm_eps": float(args.norm_eps),
            "batch_size": int(args.batch_size),
            "max_epochs": int(args.max_epochs),
            "patience": int(args.patience),
            "loss_weights": {"3d": float(args.w3), "5d": float(args.w5), "10d": float(args.w10)},
            "loss_type": str(args.loss_type),
            "loss_alpha": float(args.loss_alpha),
            "ic_rank_beta": float(args.ic_rank_beta),
            "seed": int(args.seed),
            "device": str(device),
            "months": [str(m) for m in months],
        },
        "raw_oos_metrics": raw_metrics,
        "calibrated_oos_metrics": cal_metrics,
        "delta_cal_minus_raw": {
            "avg_ic": float(cal_metrics["avg_ic"] - raw_metrics["avg_ic"]),
            "avg_rank_ic": float(cal_metrics["avg_rank_ic"] - raw_metrics["avg_rank_ic"]),
            "avg_mae": float(cal_metrics["avg_mae"] - raw_metrics["avg_mae"]),
        },
        "monthly_logs": month_logs,
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
