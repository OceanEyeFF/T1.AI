#!/usr/bin/env python
"""Rolling retrain (week-based window) + horizon-wise sign calibration for dim19 market-state LSTM."""

from __future__ import annotations

import argparse
import json
import random
import re
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
    aggregate_daily_to_monthly,
    calculate_daily_cs_ic,
    information_coefficient,
    mean_absolute_error,
    rank_information_coefficient,
    summarize_daily_cs,
)
from ashare_lab.evaluation.trade_like_panel import build_primary_trade_like_comparison_panel
from ashare_lab.trend_schema import (
    PRIMARY_TREND_LABEL_COLS,
    PRIMARY_TREND_PRED_COLS,
    PRIMARY_TREND_WEIGHT_BY_LABEL,
    infer_label_cols,
    pred_col_from_label,
    target_name_from_label,
)

try:
    from scripts.config_io import dump_json, extract_arg_overrides
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config_io import dump_json, extract_arg_overrides
try:
    from scripts.env_guard import ensure_required_conda_env
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from env_guard import ensure_required_conda_env

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

DEFAULT_LABEL_COLS = list(PRIMARY_TREND_LABEL_COLS)
DEFAULT_PRED_COLS = list(PRIMARY_TREND_PRED_COLS)
LOSS_TYPES = ("l1", "ic_aware", "rank_aware", "ic_rank_aware")
FEATURE_MODES = ("dim19", "auto")
BACKBONES = ("lstm", "transformer")
LR_SCHEDULERS = ("none", "cosine", "cosine_warm_restart", "plateau")
OPTIMIZERS = ("adamw", "adam")
NORM_TYPES = ("layernorm", "rmsnorm")
GRAD_CLIP_MODES = ("none", "norm", "value")
CONFIG_SECTION_NAME = "run_lstm_rolling_retrain_dim19_regime"
CONFIG_STATUS_CHOICES = ("baseline", "candidate-best", "frozen-best")


def _months_to_weeks(months: int) -> int:
    # Keep deterministic conversion for backward-compatible CLI options.
    return max(1, int(round(float(months) * 52.0 / 12.0)))


def _resolve_window_weeks(
    *,
    weeks: int | None,
    months: int | None,
    default_weeks: int,
    field_name: str,
) -> int:
    if weeks is not None:
        if weeks <= 0:
            raise ValueError(f"{field_name} must be > 0")
        return int(weeks)
    if months is not None:
        if months <= 0:
            raise ValueError(f"{field_name} legacy months input must be > 0")
        return _months_to_weeks(int(months))
    return int(default_weeks)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _infer_label_cols(df: pd.DataFrame) -> list[str]:
    labels = infer_label_cols(df.columns)
    if not labels:
        raise ValueError("dataset has no label columns (expect columns starting with 'label_')")
    return labels


def _is_sign_calibratable_label(label_col: str) -> bool:
    if re.fullmatch(r"label_(\d+)d", label_col):
        return True
    if re.fullmatch(r"label_(\d+)d_close", label_col):
        return True
    return False


def _hlc_1d_index_map(label_cols: list[str]) -> dict[str, int]:
    idx: dict[str, int] = {}
    for name in ("label_1d_high", "label_1d_low", "label_1d_close"):
        if name in label_cols:
            idx[name] = int(label_cols.index(name))
    return idx


def _compute_hlc_1d_consistency(
    pred: np.ndarray,
    y: np.ndarray,
    label_cols: list[str],
) -> dict[str, float]:
    """Compute 1d H/L/C structure consistency metrics.

    Returns empty dict when required 1d HLC labels are not present.
    """
    idx_map = _hlc_1d_index_map(label_cols)
    required = ("label_1d_high", "label_1d_low", "label_1d_close")
    if not all(k in idx_map for k in required):
        return {}

    i_high = idx_map["label_1d_high"]
    i_low = idx_map["label_1d_low"]
    i_close = idx_map["label_1d_close"]

    pred_high = pred[:, i_high]
    pred_low = pred[:, i_low]
    pred_close = pred[:, i_close]

    label_high = y[:, i_high]
    label_low = y[:, i_low]
    label_close = y[:, i_close]

    finite_mask = (
        np.isfinite(pred_high)
        & np.isfinite(pred_low)
        & np.isfinite(pred_close)
        & np.isfinite(label_high)
        & np.isfinite(label_low)
        & np.isfinite(label_close)
    )
    valid_count = int(np.sum(finite_mask))
    if valid_count <= 0:
        return {
            "hlc_1d_valid_count": 0.0,
            "order_violation_rate_1d_hlc": 1.0,
            "range_mae_1d_hlc": 0.0,
            "inside_rate_1d_hlc": 0.0,
        }

    ph = pred_high[finite_mask]
    pl = pred_low[finite_mask]
    pc = pred_close[finite_mask]
    lh = label_high[finite_mask]
    ll = label_low[finite_mask]

    order_violation = (pl > pc) | (pc > ph)
    pred_range = ph - pl
    label_range = lh - ll
    inside = (pc >= ll) & (pc <= lh)

    return {
        "hlc_1d_valid_count": float(valid_count),
        "order_violation_rate_1d_hlc": float(np.mean(order_violation)),
        "range_mae_1d_hlc": float(np.mean(np.abs(pred_range - label_range))),
        "inside_rate_1d_hlc": float(np.mean(inside)),
    }


def _metrics(pred: np.ndarray, y: np.ndarray, label_cols: list[str]) -> dict[str, float]:
    if pred.ndim != 2 or y.ndim != 2:
        raise ValueError("pred/y must be 2-D arrays")
    if pred.shape != y.shape:
        raise ValueError(f"pred/y shape mismatch: {pred.shape} vs {y.shape}")
    if pred.shape[1] != len(label_cols):
        raise ValueError(f"label_cols size mismatch: {len(label_cols)} vs {pred.shape[1]}")

    ic_vals: list[float] = []
    ric_vals: list[float] = []
    mae_vals: list[float] = []
    out: dict[str, float] = {}
    for idx, label_col in enumerate(label_cols):
        target = target_name_from_label(label_col)
        ic_v = float(information_coefficient(pred[:, idx], y[:, idx]))
        ric_v = float(rank_information_coefficient(pred[:, idx], y[:, idx]))
        mae_v = float(mean_absolute_error(pred[:, idx], y[:, idx]))
        out[f"ic_{target}"] = ic_v
        out[f"rank_ic_{target}"] = ric_v
        out[f"mae_{target}"] = mae_v
        ic_vals.append(ic_v)
        ric_vals.append(ric_v)
        mae_vals.append(mae_v)

    out["avg_ic"] = float(np.mean(ic_vals))
    out["avg_rank_ic"] = float(np.mean(ric_vals))
    out["avg_mae"] = float(np.mean(mae_vals))
    out.update(_compute_hlc_1d_consistency(pred, y, label_cols))
    return out


def _extract_xy(
    df: pd.DataFrame,
    feature_bases: list[str],
    seq_len: int,
    label_cols: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    x_cols = [f"{b}_t{t}" for t in range(seq_len) for b in feature_bases]
    x = df[x_cols].to_numpy(dtype=np.float32, copy=False).reshape(len(df), seq_len, len(feature_bases))
    x = np.nan_to_num(x, nan=0.0)
    y = df[label_cols].to_numpy(dtype=np.float32, copy=False)
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


def _infer_max_horizon_days(label_cols: list[str]) -> int:
    horizons: list[int] = []
    for col in label_cols:
        m = re.fullmatch(r"label_(\d+)d(?:_.+)?", str(col))
        if m is not None:
            horizons.append(int(m.group(1)))
    if not horizons:
        raise ValueError("failed to infer horizon days from label columns")
    return int(max(horizons))


def _label_mode_shift_days(label_mode: str) -> int:
    if label_mode == "next_open_to_open":
        return 1
    return 0


def _attach_label_maturity_date(
    df: pd.DataFrame,
    *,
    horizon_days: int,
    shift_days: int,
    maturity_col: str = "label_maturity_date",
) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str)
    out = out.sort_values(["symbol", "date"]).reset_index(drop=True)
    steps = int(horizon_days + shift_days)
    if steps <= 0:
        raise ValueError("horizon_days + shift_days must be > 0")
    out[maturity_col] = out.groupby("symbol", sort=False)["date"].shift(-steps)
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


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
        pred_cols: tuple[str, ...],
        loss_weights: tuple[float, ...],
        loss_type: str,
        loss_alpha: float,
        ic_rank_beta: float,
        norm_type: str,
        norm_eps: float,
    ) -> None:
        super().__init__()
        self.pred_cols = tuple(pred_cols)
        if len(self.pred_cols) == 0:
            raise ValueError("pred_cols is empty")
        if len(loss_weights) != len(self.pred_cols):
            raise ValueError("loss_weights length must match pred_cols length")
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

        self.heads = nn.ModuleDict({pred_key: _head() for pred_key in self.pred_cols})

    def forward(self, x: torch.Tensor, labels: torch.Tensor | None = None):
        out, _ = self.lstm(x)
        h = self.norm(out[:, -1, :])
        preds = {pred_key: self.heads[pred_key](h).squeeze(-1) for pred_key in self.pred_cols}
        if labels is None:
            return preds
        weights = self.loss_weights.to(device=labels.device, dtype=labels.dtype)
        per_head: list[torch.Tensor] = []
        details: dict[str, torch.Tensor] = {}

        for idx, pred_key in enumerate(self.pred_cols):
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
        pred_cols: tuple[str, ...],
        loss_weights: tuple[float, ...],
        loss_type: str,
        loss_alpha: float,
        ic_rank_beta: float,
        norm_type: str,
        norm_eps: float,
    ) -> None:
        super().__init__()
        self.pred_cols = tuple(pred_cols)
        if len(self.pred_cols) == 0:
            raise ValueError("pred_cols is empty")
        if len(loss_weights) != len(self.pred_cols):
            raise ValueError("loss_weights length must match pred_cols length")
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

        self.heads = nn.ModuleDict({pred_key: _head() for pred_key in self.pred_cols})

    def forward(self, x: torch.Tensor, labels: torch.Tensor | None = None):
        h = self.input_proj(x)
        h = h + self.pos_embed[:, : h.shape[1], :]
        h = self.encoder(h)
        h = self.norm(h[:, -1, :])
        preds = {pred_key: self.heads[pred_key](h).squeeze(-1) for pred_key in self.pred_cols}
        if labels is None:
            return preds
        weights = self.loss_weights.to(device=labels.device, dtype=labels.dtype)
        per_head: list[torch.Tensor] = []
        details: dict[str, torch.Tensor] = {}

        for idx, pred_key in enumerate(self.pred_cols):
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
def _predict(
    model: nn.Module,
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
    pred_cols: list[str],
) -> np.ndarray:
    loader = DataLoader(TensorDataset(torch.from_numpy(x)), batch_size=batch_size, shuffle=False)
    model.eval()
    rows: list[np.ndarray] = []
    for (xb,) in loader:
        out = model(xb.to(device))
        rows.append(torch.stack([out[pred_key] for pred_key in pred_cols], dim=1).detach().cpu().numpy())
    return np.concatenate(rows, axis=0)


@torch.no_grad()
def _eval(
    model: nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
    *,
    label_cols: list[str],
    pred_cols: list[str],
) -> dict[str, float]:
    pred = _predict(model, x, batch_size=batch_size, device=device, pred_cols=pred_cols)
    return _metrics(pred, y, label_cols=label_cols)


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
    label_cols: tuple[str, ...]
    pred_cols: tuple[str, ...]
    loss_weights: tuple[float, ...]
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
            pred_cols=cfg.pred_cols,
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
            pred_cols=cfg.pred_cols,
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
        n_heads = len(cfg.pred_cols)
        vp = [[] for _ in range(n_heads)]
        vy = [[] for _ in range(n_heads)]
        for xb, yb in valid_loader:
            out = model(xb.to(device))
            for i_head, pred_key in enumerate(cfg.pred_cols):
                vp[i_head].append(out[pred_key].detach().cpu().numpy())
                vy[i_head].append(yb[:, i_head].numpy())
        pred = np.stack([np.concatenate(vp[i]) for i in range(n_heads)], axis=1)
        yv = np.stack([np.concatenate(vy[i]) for i in range(n_heads)], axis=1)
        met = _metrics(pred, yv, label_cols=list(cfg.label_cols))
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
    valid_best = _eval(
        model,
        x_valid,
        y_valid,
        cfg.batch_size,
        device,
        label_cols=list(cfg.label_cols),
        pred_cols=list(cfg.pred_cols),
    )
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


def _parse_head_weight_overrides(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    raw = str(text).strip()
    if not raw:
        return out
    for item in raw.split(","):
        part = item.strip()
        if not part:
            continue
        if ":" in part:
            key, val = part.split(":", 1)
        elif "=" in part:
            key, val = part.split("=", 1)
        else:
            raise ValueError(
                "invalid --head-loss-weights format; expected 'label_xxx:1.0,label_yyy:0.5'"
            )
        col = key.strip()
        weight = float(val.strip())
        if weight < 0:
            raise ValueError(f"head weight must be >= 0, got {weight} for {col}")
        out[col] = weight
    return out


def _resolve_loss_weights(
    *,
    label_cols: list[str],
    w3: float,
    w5: float,
    w10: float,
    extra_head_weight: float,
    head_loss_weights: str,
) -> tuple[float, ...]:
    if w3 < 0 or w5 < 0 or w10 < 0:
        raise ValueError("w3/w5/w10 must be non-negative")
    if extra_head_weight < 0:
        raise ValueError("extra_head_weight must be non-negative")
    overrides = _parse_head_weight_overrides(head_loss_weights)
    weights: list[float] = []
    for col in label_cols:
        if col in overrides:
            w = float(overrides[col])
        elif col in PRIMARY_TREND_WEIGHT_BY_LABEL:
            weight_key = PRIMARY_TREND_WEIGHT_BY_LABEL[col]
            if weight_key == "w3":
                w = float(w3)
            elif weight_key == "w5":
                w = float(w5)
            else:
                w = float(w10)
        else:
            w = float(extra_head_weight)
        weights.append(w)
    if sum(weights) <= 0:
        raise ValueError("resolved loss weights sum to 0")
    return tuple(weights)


def _build_mainline_model_profile(
    *,
    model_track: str,
    config_profile: str,
    config_status: str,
    label_cols: list[str],
    pred_cols: list[str],
) -> dict[str, object]:
    primary_label_cols = [col for col in PRIMARY_TREND_LABEL_COLS if col in label_cols]
    primary_pred_cols = [col for col in PRIMARY_TREND_PRED_COLS if col in pred_cols]
    aggregation_ready = (
        str(model_track) == "mainline_3510d"
        and primary_label_cols == list(PRIMARY_TREND_LABEL_COLS)
        and primary_pred_cols == list(PRIMARY_TREND_PRED_COLS)
    )
    return {
        "model_track": str(model_track),
        "config_profile": str(config_profile),
        "config_status": str(config_status),
        "primary_label_columns": primary_label_cols,
        "primary_prediction_columns": primary_pred_cols,
        "aggregation_target": ("alpha_score" if aggregation_ready else ""),
        "aggregation_ready": bool(aggregation_ready),
    }


def _build_comparison_panel(
    oos: pd.DataFrame,
    *,
    top_n: int,
) -> dict[str, object]:
    return build_primary_trade_like_comparison_panel(oos, top_n=top_n)


def _build_config_status_policy(config_status: str) -> dict[str, object]:
    return {
        "current_status": str(config_status),
        "definitions": {
            "baseline": "当前默认工作参数，用于稳定复现与后续对照，不代表最优参数。",
            "candidate-best": "在统一 OOS 窗口下相对 baseline 展现出更好或更稳结果的候选参数。",
            "frozen-best": "已通过重复验证并确认冻结为当前主线默认候选的参数档位。",
        },
        "promotion_rules": {
            "baseline_to_candidate-best": [
                "必须与 baseline 使用同一 OOS 时间窗、同一评估协议、同一主指标口径",
                "trade_like comparison_panel 至少通过默认 gate，且不依赖协议漂移制造优势",
                "相对 baseline 的主目标指标提升应可复述为同窗对照结果",
            ],
            "candidate-best_to_frozen-best": [
                "必须完成重复验证，结论不依赖单次随机种子或单个时间窗",
                "必须保持主线 schema、聚合输出与默认报告口径一致",
                "必须由显式冻结动作确认，不能把临时领先结果直接写回默认 baseline",
            ],
        },
    }


def _select_train_valid_for_month(
    train_pool: pd.DataFrame,
    month_start: pd.Timestamp,
    *,
    train_window_weeks: int,
    valid_window_weeks: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    left = month_start - pd.DateOffset(weeks=train_window_weeks)
    pool_raw = train_pool[(train_pool["date"] >= left) & (train_pool["date"] < month_start)].copy()
    pool = pool_raw[
        pool_raw["label_maturity_date"].notna() & (pool_raw["label_maturity_date"] < month_start)
    ].copy()
    split_stats = {
        "pool_rows_before_maturity": int(len(pool_raw)),
        "pool_rows_after_maturity": int(len(pool)),
    }
    if pool.empty:
        raise RuntimeError(f"empty rolling pool before {month_start.date()} after maturity filter")

    valid_left = month_start - pd.DateOffset(weeks=valid_window_weeks)
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

    return train_df, valid_df, split_stats


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rolling retrain + horizon sign calibration.")
    parser.add_argument("--config-file", default="", help="JSON/TOML config file path (args mapping)")
    parser.add_argument(
        "--effective-config-out",
        default="",
        help="optional: save effective merged config (after CLI overrides) to JSON",
    )
    parser.add_argument("--dataset-dir", default="data/datasets/lstm_sector70_19d_mkt_20210101_20260120")
    parser.add_argument("--backbone", choices=list(BACKBONES), default="lstm")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--train-window-weeks", type=int, default=None, help="训练窗口（周），默认 78")
    parser.add_argument("--valid-window-weeks", type=int, default=None, help="验证窗口（周），默认 8")
    parser.add_argument("--calibration-weeks", type=int, default=None, help="校准历史窗口（周），默认 12")
    parser.add_argument(
        "--train-window-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：训练窗口（月）",
    )
    parser.add_argument(
        "--valid-window-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：验证窗口（月）",
    )
    parser.add_argument(
        "--calibration-months",
        type=int,
        default=None,
        help="兼容参数（已弃用）：校准窗口（月）",
    )
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
    parser.add_argument(
        "--extra-head-weight",
        type=float,
        default=1.0,
        help="非 3d/5d/10d 头的默认损失权重（例如 1d_high/1d_low/1d_close）",
    )
    parser.add_argument(
        "--head-loss-weights",
        default="",
        help="可选：按标签列名覆写权重，如 label_1d_high:0.5,label_1d_low:0.5,label_1d_close:1.0",
    )
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
    parser.add_argument(
        "--model-track",
        default="mainline_3510d",
        help="模型线标识，默认 mainline_3510d",
    )
    parser.add_argument(
        "--config-profile",
        default="lstm_rolling_baseline",
        help="当前配置档位名称，写入报告用于区分 baseline/candidate/frozen",
    )
    parser.add_argument(
        "--config-status",
        choices=list(CONFIG_STATUS_CHOICES),
        default="baseline",
        help="当前配置状态：baseline / candidate-best / frozen-best",
    )
    parser.add_argument(
        "--label-mode",
        default="close_to_close",
        choices=["close_to_close", "next_open_to_open"],
        help="标签口径，写入 evaluation_protocol（默认 close_to_close）",
    )
    parser.add_argument("--save-weekly-checkpoints", action="store_true")
    parser.add_argument(
        "--save-monthly-checkpoints",
        action="store_true",
        help="兼容参数（已弃用）：等价于 --save-weekly-checkpoints",
    )
    parser.add_argument(
        "--save-oos-parquet",
        default="",
        help="可选：保存 OOS 逐样本预测（含 raw/cal）到 parquet，用于 daily-CS 统一评估",
    )
    parser.add_argument(
        "--comparison-top-n",
        type=int,
        default=10,
        help="主线比较面板按 alpha_score 取前 N 名做等权交易近似评估",
    )
    parser.add_argument(
        "--report",
        default="output/reports/lstm_dim19_rolling78w_horizoncal_20260303.json",
    )
    return parser


def _argparse_allowed_keys(parser: argparse.ArgumentParser) -> set[str]:
    return {a.dest for a in parser._actions if a.dest != "help"}


def main() -> None:
    ensure_required_conda_env("ashare-lab")
    parser = _build_parser()
    pre_args, _ = parser.parse_known_args()
    config_section_used: str | None = None
    if pre_args.config_file:
        allowed_keys = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        overrides, config_section_used = extract_arg_overrides(
            config_path=pre_args.config_file,
            allowed_keys=allowed_keys,
            section_candidates=(CONFIG_SECTION_NAME, "lstm"),
        )
        parser.set_defaults(**overrides)
    args = parser.parse_args()
    config_file_resolved = (
        str(Path(args.config_file).resolve()) if str(args.config_file).strip() else ""
    )

    train_window_weeks = _resolve_window_weeks(
        weeks=args.train_window_weeks,
        months=args.train_window_months,
        default_weeks=78,
        field_name="train_window_weeks",
    )
    valid_window_weeks = _resolve_window_weeks(
        weeks=args.valid_window_weeks,
        months=args.valid_window_months,
        default_weeks=8,
        field_name="valid_window_weeks",
    )
    calibration_weeks = _resolve_window_weeks(
        weeks=args.calibration_weeks,
        months=args.calibration_months,
        default_weeks=12,
        field_name="calibration_weeks",
    )

    if args.w3 < 0 or args.w5 < 0 or args.w10 < 0:
        raise ValueError("w3/w5/w10 must be non-negative")
    if args.extra_head_weight < 0:
        raise ValueError("extra_head_weight must be non-negative")
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
    if args.comparison_top_n <= 0:
        raise ValueError("comparison_top_n must be > 0")

    effective_config_path = ""
    effective_config_out = str(args.effective_config_out).strip()
    if effective_config_out:
        effective_config_path = effective_config_out
    elif config_file_resolved:
        report_path = Path(args.report)
        effective_config_path = str(
            report_path.with_name(f"{report_path.stem}_effective_config.json")
        )

    if effective_config_path:
        allowed_effective = _argparse_allowed_keys(parser) - {"config_file", "effective_config_out"}
        effective_args = {k: getattr(args, k) for k in sorted(allowed_effective)}
        saved = dump_json(
            effective_config_path,
            {
                "script": CONFIG_SECTION_NAME,
                "config_file": config_file_resolved or None,
                "config_section": config_section_used,
                "args": effective_args,
            },
        )
        print(f"Saved effective config: {saved}")

    _set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ddir = Path(args.dataset_dir)
    train_df = pd.read_parquet(ddir / "train.parquet")
    valid_df = pd.read_parquet(ddir / "valid.parquet")
    test_df = pd.read_parquet(ddir / "test.parquet")
    label_cols = _infer_label_cols(train_df)
    pred_cols = [pred_col_from_label(c) for c in label_cols]
    mainline_model_profile = _build_mainline_model_profile(
        model_track=str(args.model_track),
        config_profile=str(args.config_profile),
        config_status=str(args.config_status),
        label_cols=label_cols,
        pred_cols=pred_cols,
    )
    loss_weights = _resolve_loss_weights(
        label_cols=label_cols,
        w3=float(args.w3),
        w5=float(args.w5),
        w10=float(args.w10),
        extra_head_weight=float(args.extra_head_weight),
        head_loss_weights=str(args.head_loss_weights),
    )
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
        label_cols=tuple(label_cols),
        pred_cols=tuple(pred_cols),
        loss_weights=tuple(loss_weights),
        loss_type=str(args.loss_type),
        loss_alpha=float(args.loss_alpha),
        ic_rank_beta=float(args.ic_rank_beta),
    )

    full_df = pd.concat([train_df, valid_df, test_df], ignore_index=True)
    full_df["date"] = pd.to_datetime(full_df["date"])
    full_df["symbol"] = full_df["symbol"].astype(str)
    full_df = full_df.sort_values(["date", "symbol"]).reset_index(drop=True)
    missing_label_cols = [c for c in label_cols if c not in full_df.columns]
    if missing_label_cols:
        preview = ", ".join(missing_label_cols[:5])
        raise ValueError(f"dataset missing required label columns (showing up to 5): {preview}")

    maturity_horizon_days = _infer_max_horizon_days(label_cols)
    maturity_shift_days = _label_mode_shift_days(str(args.label_mode))
    full_df = _attach_label_maturity_date(
        full_df,
        horizon_days=maturity_horizon_days,
        shift_days=maturity_shift_days,
    )

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
    retrain_weeks = sorted(eval_df["date"].dt.to_period("W-FRI").unique())
    legacy_months = sorted(eval_df["date"].dt.to_period("M").unique())

    # history for walk-forward calibration uses realized OOS predictions from prior retrain periods
    hist_rows: list[pd.DataFrame] = []
    oos_rows: list[pd.DataFrame] = []
    week_logs: list[dict[str, object]] = []
    save_weekly_checkpoints = bool(args.save_weekly_checkpoints or args.save_monthly_checkpoints)
    signable_specs: list[tuple[int, str, str, str]] = []
    for idx, (label_col, pred_col) in enumerate(zip(label_cols, pred_cols)):
        if _is_sign_calibratable_label(label_col):
            signable_specs.append((idx, label_col, pred_col, target_name_from_label(label_col)))

    ckpt_dir = Path("models/rolling_dim19")
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    for i, w in enumerate(retrain_weeks):
        week = str(w)
        week_mask = eval_df["date"].dt.to_period("W-FRI") == w
        week_df = eval_df.loc[week_mask].copy()
        if week_df.empty:
            continue
        week_start = week_df["date"].min()
        week_end = week_df["date"].max()

        print(f"\n=== week {week} ({week_start.date()}..{week_end.date()}) ===")
        tr_df, va_df, split_stats = _select_train_valid_for_month(
            full_df,
            month_start=week_start,
            train_window_weeks=train_window_weeks,
            valid_window_weeks=valid_window_weeks,
        )
        print(
            f"train_rows={len(tr_df)} valid_rows={len(va_df)} week_rows={len(week_df)} "
            f"train_range=[{tr_df['date'].min().date()}..{tr_df['date'].max().date()}] "
            f"pool_before={split_stats['pool_rows_before_maturity']} "
            f"pool_after={split_stats['pool_rows_after_maturity']}"
        )

        # month-specific seed for reproducibility and mild de-correlation
        _set_seed(args.seed + i)

        x_tr, y_tr = _extract_xy(tr_df, feature_bases, args.seq_len, label_cols=label_cols)
        x_va, y_va = _extract_xy(va_df, feature_bases, args.seq_len, label_cols=label_cols)
        x_wk, y_wk = _extract_xy(week_df, feature_bases, args.seq_len, label_cols=label_cols)

        model, val_metrics, epochs_ran, train_seconds = _train_one_model(x_tr, y_tr, x_va, y_va, cfg, device)
        pred_val = _predict(model, x_va, cfg.batch_size, device, pred_cols=pred_cols)
        pred_week = _predict(model, x_wk, cfg.batch_size, device, pred_cols=pred_cols)

        # build calibration score per horizon from trailing realized history
        hist_df = pd.concat(hist_rows, ignore_index=True) if hist_rows else pd.DataFrame()
        hist_rows_before_maturity = 0
        hist_rows_after_maturity = 0
        if not hist_df.empty:
            hist_df["date"] = pd.to_datetime(hist_df["date"])
            hist_df["symbol"] = hist_df["symbol"].astype(str)
            hist_df = _attach_label_maturity_date(
                hist_df,
                horizon_days=maturity_horizon_days,
                shift_days=maturity_shift_days,
            )
            hist_left = week_start - pd.DateOffset(weeks=calibration_weeks)
            hist_window = hist_df[(hist_df["date"] >= hist_left) & (hist_df["date"] < week_start)].copy()
            hist_rows_before_maturity = int(len(hist_window))
            hist_use = hist_window[
                hist_window["label_maturity_date"].notna() & (hist_window["label_maturity_date"] < week_start)
            ].copy()
            hist_rows_after_maturity = int(len(hist_use))
        else:
            hist_use = pd.DataFrame()

        signs: list[int] = [1 for _ in label_cols]
        decisions: list[dict[str, float | int]] = []
        for idx, label_col, pred_col, target_name in signable_specs:
            val_ic = float(information_coefficient(pred_val[:, idx], y_va[:, idx]))
            hist_ic = float("nan")
            if not hist_use.empty:
                hist_ic = float(
                    information_coefficient(
                        hist_use[pred_col].to_numpy(dtype=float, copy=False),
                        hist_use[label_col].to_numpy(dtype=float, copy=False),
                    )
                )
            score = hist_ic if np.isfinite(hist_ic) else val_ic
            sign, reason = _choose_sign_consensus(hist_ic, val_ic, args.sign_threshold)
            signs[idx] = int(sign)
            decisions.append(
                {
                    "target": target_name,
                    "val_ic": val_ic,
                    "hist_ic": hist_ic,
                    "score_used": float(score),
                    "sign": int(sign),
                    "rule": reason,
                }
            )

        pred_cal = pred_week.copy()
        for idx in range(len(label_cols)):
            pred_cal[:, idx] = signs[idx] * pred_cal[:, idx]

        week_raw = _metrics(pred_week, y_wk, label_cols=label_cols)
        week_cal = _metrics(pred_cal, y_wk, label_cols=label_cols)
        print(
            f"week_raw_avg_ic={week_raw['avg_ic']:.4f} week_cal_avg_ic={week_cal['avg_ic']:.4f} "
            f"signs={signs}"
        )

        week_out = week_df[["date", "symbol"] + label_cols].copy()
        for h, c in enumerate(pred_cols):
            week_out[c] = pred_week[:, h]
            week_out[f"{c}_cal"] = pred_cal[:, h]
        oos_rows.append(week_out)
        hist_rows.append(week_out[["date", "symbol"] + label_cols + pred_cols].copy())

        if save_weekly_checkpoints:
            ckpt_path = ckpt_dir / f"best_dim19_week_end_{week_end.strftime('%Y%m%d')}.pt"
            torch.save({"model_state_dict": model.state_dict()}, ckpt_path)
        week_logs.append(
            {
                "week": week,
                "week_start": str(week_start.date()),
                "week_end": str(week_end.date()),
                "week_rows": int(len(week_df)),
                "train_rows": int(len(tr_df)),
                "valid_rows": int(len(va_df)),
                "pool_rows_before_maturity": int(split_stats["pool_rows_before_maturity"]),
                "pool_rows_after_maturity": int(split_stats["pool_rows_after_maturity"]),
                "hist_rows_before_maturity": int(hist_rows_before_maturity),
                "hist_rows_after_maturity": int(hist_rows_after_maturity),
                "epochs_ran": int(epochs_ran),
                "train_seconds": float(train_seconds),
                "valid_avg_ic": float(val_metrics["avg_ic"]),
                "raw_avg_ic": float(week_raw["avg_ic"]),
                "cal_avg_ic": float(week_cal["avg_ic"]),
                "signs": signs,
                "decisions": decisions,
            }
        )

    if not oos_rows:
        raise RuntimeError("no out-of-sample predictions generated")

    oos = pd.concat(oos_rows, ignore_index=True)
    y = oos[label_cols].to_numpy(dtype=float, copy=False)
    raw = oos[pred_cols].to_numpy(dtype=float, copy=False)
    cal = oos[[f"{c}_cal" for c in pred_cols]].to_numpy(dtype=float, copy=False)

    raw_metrics = _metrics(raw, y, label_cols=label_cols)
    cal_metrics = _metrics(cal, y, label_cols=label_cols)
    comparison_panel = _build_comparison_panel(oos, top_n=int(args.comparison_top_n))
    config_status_policy = _build_config_status_policy(str(args.config_status))

    # --- evaluation_protocol ---
    evaluation_protocol = {
        "signal_time_mode": "close",
        "execution_time_mode": "next_open",
        "label_mode": str(args.label_mode),
        "return_mode": str(args.label_mode),
        "cost_model": "none",
        "daily_cs_mode": "required",
    }

    # --- daily_cs ---
    oos["date"] = pd.to_datetime(oos["date"])
    cs_idx = pd.MultiIndex.from_frame(oos[["date", "symbol"]])
    daily_cs: dict[str, dict] = {}
    for label_col, pred_col in zip(label_cols, pred_cols):
        hkey = target_name_from_label(label_col)
        pred_s = pd.Series(oos[pred_col].to_numpy(dtype=float), index=cs_idx)
        label_s = pd.Series(oos[label_col].to_numpy(dtype=float), index=cs_idx)
        ic_daily = calculate_daily_cs_ic(pred_s, label_s, method="pearson")
        ric_daily = calculate_daily_cs_ic(pred_s, label_s, method="spearman")
        # Ensure JSON-safe types for monthly records (numpy -> Python native)
        monthly_records = aggregate_daily_to_monthly(ic_daily).to_dict(orient="records")
        for rec in monthly_records:
            for k, v in rec.items():
                if isinstance(v, (np.integer,)):
                    rec[k] = int(v)
                elif isinstance(v, (np.floating,)):
                    rec[k] = float(v)
        daily_cs[hkey] = {
            "ic": summarize_daily_cs(ic_daily),
            "rank_ic": summarize_daily_cs(ric_daily),
            "monthly": monthly_records,
        }

    out = {
        "config": {
            "dataset_dir": str(ddir),
            "backbone": str(args.backbone),
            "feature_mode": str(args.feature_mode),
            "features": feature_bases,
            "seq_len": int(args.seq_len),
            "train_window_weeks": int(train_window_weeks),
            "valid_window_weeks": int(valid_window_weeks),
            "calibration_weeks": int(calibration_weeks),
            "window_unit": "week",
            "train_window_months_legacy_input": (
                None if args.train_window_months is None else int(args.train_window_months)
            ),
            "valid_window_months_legacy_input": (
                None if args.valid_window_months is None else int(args.valid_window_months)
            ),
            "calibration_months_legacy_input": (
                None if args.calibration_months is None else int(args.calibration_months)
            ),
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
            "label_columns": label_cols,
            "prediction_columns": pred_cols,
            "loss_weights": {
                target_name_from_label(label_cols[i]): float(cfg.loss_weights[i])
                for i in range(len(label_cols))
            },
            "extra_head_weight": float(args.extra_head_weight),
            "head_loss_weights_override": _parse_head_weight_overrides(str(args.head_loss_weights)),
            "loss_type": str(args.loss_type),
            "loss_alpha": float(args.loss_alpha),
            "ic_rank_beta": float(args.ic_rank_beta),
            "seed": int(args.seed),
            "model_track": str(args.model_track),
            "config_profile": str(args.config_profile),
            "config_status": str(args.config_status),
            "comparison_top_n": int(args.comparison_top_n),
            "label_mode": str(args.label_mode),
            "maturity_gate_enabled": True,
            "maturity_gate_horizon_days": int(maturity_horizon_days),
            "maturity_gate_shift_days": int(maturity_shift_days),
            "device": str(device),
            "retrain_weeks": [str(w) for w in retrain_weeks],
            "retrain_frequency": "weekly",
            "prediction_frequency": "daily",
            "retrain_week_freq": "W-FRI",
            "save_weekly_checkpoints": bool(save_weekly_checkpoints),
            "months": [str(m) for m in legacy_months],
            "config_file": config_file_resolved,
            "config_section": config_section_used,
            "effective_config_path": effective_config_path,
        },
        "raw_oos_metrics": raw_metrics,
        "calibrated_oos_metrics": cal_metrics,
        "delta_cal_minus_raw": {
            "avg_ic": float(cal_metrics["avg_ic"] - raw_metrics["avg_ic"]),
            "avg_rank_ic": float(cal_metrics["avg_rank_ic"] - raw_metrics["avg_rank_ic"]),
            "avg_mae": float(cal_metrics["avg_mae"] - raw_metrics["avg_mae"]),
        },
        "weekly_logs": week_logs,
        "monthly_logs": week_logs,
        "evaluation_protocol": evaluation_protocol,
        "daily_cs": daily_cs,
        "mainline_model_profile": mainline_model_profile,
        "comparison_panel": comparison_panel,
        "config_status_policy": config_status_policy,
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
