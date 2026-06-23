"""LSTM 多任务模型 — 适配 ModelABC 接口。

收敛自 3 份脚本中的 MtlLSTM 副本（WT-R1-A1 审计）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ashare_lab.models.base import (
    ModelABC,
    PredictionData,
    PredictionResult,
    TrainingData,
    TrainingResult,
)
from ashare_lab.models.registry import register_model


# ---------------------------------------------------------------------------
# 损失函数（来自 LSTM #1）
# ---------------------------------------------------------------------------


class RMSNorm(nn.Module):
    """RMS 归一化。"""

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


def _masked_l1_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() == 0:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    return torch.mean(torch.abs(pred[mask] - target[mask]))


def _pearson_corr(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() < 2:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    p = pred[mask] - pred[mask].mean()
    t = target[mask] - target[mask].mean()
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
        total = loss_alpha * l1 + (1.0 - loss_alpha) * (
            ic_rank_beta * ic_loss + (1.0 - ic_rank_beta) * rank_loss
        )
    else:
        raise ValueError(f"unsupported loss_type: {loss_type}")
    return total, {"l1": l1, "ic_loss": ic_loss, "rank_loss": rank_loss}


# ---------------------------------------------------------------------------
# LSTM 模型
# ---------------------------------------------------------------------------


class MtlLSTM(nn.Module):
    """多任务 LSTM — 收敛自 3 份脚本副本。"""

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
        pred_cols: tuple[str, ...],
        loss_weights: tuple[float, ...],
        loss_type: str = "l1",
        loss_alpha: float = 0.3,
        ic_rank_beta: float = 0.5,
        norm_type: str = "layernorm",
        norm_eps: float = 1e-5,
    ) -> None:
        super().__init__()
        self.pred_cols = tuple(pred_cols)
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

        self.heads = nn.ModuleDict({k: _head() for k in self.pred_cols})

    def forward(self, x: torch.Tensor, labels: torch.Tensor | None = None):
        out, _ = self.lstm(x)
        h = self.norm(out[:, -1, :])
        preds = {k: self.heads[k](h).squeeze(-1) for k in self.pred_cols}
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


# ---------------------------------------------------------------------------
# ModelABC 封装
# ---------------------------------------------------------------------------


class LSTMModel(ModelABC):
    """LSTM 多任务模型 — 封装 MtlLSTM。"""

    def __init__(
        self, *, pred_cols: tuple[str, ...] = ("pred_3d", "pred_5d", "pred_10d"), **config: Any
    ) -> None:
        self._config = {**config, "pred_cols": pred_cols}
        self._model = MtlLSTM(
            pred_cols=pred_cols, **{k: v for k, v in config.items() if k != "pred_cols"}
        )
        self._device = torch.device("cpu")

    @property
    def name(self) -> str:
        return "lstm"

    @property
    def description(self) -> str:
        return "多任务 LSTM（支持 l1/ic_aware/rank_aware/ic_rank_aware 损失）"

    def train(self, data: TrainingData) -> TrainingResult:
        self._model.to(self._device).train()
        opt = torch.optim.AdamW(self._model.parameters(), lr=1e-4, weight_decay=1e-5)
        Xt = torch.from_numpy(data.X_train).float().to(self._device)
        yt = torch.from_numpy(data.y_train).float().to(self._device)
        Xv = torch.from_numpy(data.X_valid).float().to(self._device)
        yv = torch.from_numpy(data.y_valid).float().to(self._device)

        best_loss, best_state, no_improve = float("inf"), None, 0
        for _ in range(self._config.get("max_epochs", 50)):
            opt.zero_grad()
            _, losses = self._model(Xt, yt)
            losses["total"].backward()
            opt.step()
            with torch.no_grad():
                _, vl = self._model(Xv, yv)
                v = vl["total"].item()
            if v < best_loss - 1e-5:
                best_loss, best_state, no_improve = (
                    v,
                    {k: v.cpu().clone() for k, v in self._model.state_dict().items()},
                    0,
                )
            else:
                no_improve += 1
                if no_improve >= (self._config.get("patience", 10)):
                    break
        if best_state:
            self._model.load_state_dict(best_state)
        return TrainingResult(model=self, metrics={"best_val_loss": float(best_loss)})

    def predict(self, data: PredictionData) -> PredictionResult:
        self._model.to(self._device).eval()
        with torch.no_grad():
            Xt = torch.from_numpy(data.X).float().to(self._device)
            preds = self._model(Xt)
            preds_np = torch.stack([preds[k] for k in self._model.pred_cols], dim=1).cpu().numpy()
        return PredictionResult(preds=preds_np)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        torch.save({"config": self._config, "state": self._model.state_dict()}, p / "checkpoint.pt")

    @classmethod
    def load(cls, path: str | Path) -> "LSTMModel":
        p = Path(path)
        ckpt = torch.load(p / "checkpoint.pt", map_location="cpu", weights_only=True)
        inst = cls.__new__(cls)
        inst._config = ckpt["config"]
        inst._model = MtlLSTM(**ckpt["config"])
        inst._model.load_state_dict(ckpt["state"])
        inst._device = torch.device("cpu")
        return inst


register_model("lstm", LSTMModel)
