"""多任务Transformer模型

该模块提供面向股票多时间跨度收益预测的多任务Transformer实现，
共享一套Encoder并为3/5/10日三个预测任务提供独立回归头，
支持缺失标签掩码与加权L1损失。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import torch
import torch.nn as nn


@dataclass
class TransformerConfig:
    """多任务Transformer配置"""

    input_dim: int = 6  # 输入特征维度
    d_model: int = 128  # 隐藏层维度
    n_heads: int = 4  # 注意力头数
    n_layers: int = 4  # 编码器层数（限定4-6层）
    d_ff: int = 512  # 前馈网络维度
    dropout: float = 0.1  # Dropout比例
    max_seq_len: int = 512  # 最大可处理序列长度
    min_seq_len: int = 30  # 最小序列长度约束
    loss_weights: tuple[float, float, float] = (1.0, 1.0, 1.0)


class PositionalEncoding(nn.Module):
    """标准正弦位置编码"""

    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]

        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, seq_len, d_model]

        Returns:
            添加位置编码后的张量
        """
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


def _masked_l1_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """单任务带缺失掩码的L1损失。

    target中的NaN位置会被忽略；无有效样本时返回0（常数，不影响梯度传播）。
    """
    if pred.shape != target.shape:
        raise ValueError("prediction and target shape must match for masked L1")

    mask = ~torch.isnan(target)
    if mask.sum() == 0:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)

    diff = torch.where(mask, torch.abs(pred - target), torch.zeros_like(pred))
    return diff.sum() / mask.sum()


def compute_mtl_loss(
    predictions: Mapping[str, torch.Tensor] | Sequence[torch.Tensor],
    labels: torch.Tensor,
    loss_weights: Iterable[float] | torch.Tensor,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """计算三头加权L1损失。

    Args:
        predictions: dict需含`pred_3d/pred_5d/pred_10d`，或长度3的序列。
        labels: [batch, 3] 标签张量（列顺序：3d,5d,10d）。
        loss_weights: 三个头的权重。
    """
    if labels.ndim != 2 or labels.size(1) != 3:
        raise ValueError("labels must have shape [batch, 3]")

    if isinstance(predictions, Mapping):
        preds_tuple = (
            predictions["pred_3d"],
            predictions["pred_5d"],
            predictions["pred_10d"],
        )
    else:
        preds_tuple = tuple(predictions)

    if len(preds_tuple) != 3:
        raise ValueError("predictions must contain three heads")

    weights = torch.as_tensor(loss_weights, device=labels.device, dtype=labels.dtype)
    if weights.numel() != 3:
        raise ValueError("loss_weights must have three elements")

    head_losses = [_masked_l1_loss(preds_tuple[i], labels[:, i]) for i in range(3)]

    total_loss = torch.stack(head_losses).mul(weights).sum()
    return total_loss, {
        "l1_3d": head_losses[0],
        "l1_5d": head_losses[1],
        "l1_10d": head_losses[2],
    }


def freeze_encoder_layers(model: nn.Module, num_layers: int) -> None:
    """冻结Transformer Encoder前`num_layers`层参数。"""
    if not hasattr(model, "transformer_encoder"):
        raise AttributeError("model must have transformer_encoder attribute to freeze layers")

    encoder: nn.TransformerEncoder = model.transformer_encoder
    if num_layers < 0 or num_layers > len(encoder.layers):
        raise ValueError("num_layers must be between 0 and the total encoder layers")

    for idx, layer in enumerate(encoder.layers):
        requires_grad = idx >= num_layers
        for param in layer.parameters():
            param.requires_grad = requires_grad


class EarlyStoppingIC:
    """基于验证集IC的早停逻辑，连续无提升patience轮则停止。"""

    def __init__(self, patience: int = 5, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.best = -float("inf")
        self.counter = 0

    def step(self, current_ic: float) -> bool:
        """返回是否需要早停。"""
        if current_ic > self.best + self.min_delta:
            self.best = current_ic
            self.counter = 0
        else:
            self.counter += 1
        return self.counter >= self.patience


class MTLTransformer(nn.Module):
    """共享编码器 + 三任务回归头的Transformer。"""

    def __init__(self, config: TransformerConfig):
        super().__init__()
        if not 4 <= config.n_layers <= 6:
            raise ValueError("n_layers must be between 4 and 6 for MTL Transformer")
        if config.max_seq_len < config.min_seq_len:
            raise ValueError("max_seq_len must be >= min_seq_len")

        self.config = config
        self.register_buffer("loss_weights", torch.tensor(config.loss_weights, dtype=torch.float32))

        self.input_projection = nn.Linear(config.input_dim, config.d_model)
        self.pos_encoder = PositionalEncoding(config.d_model, config.max_seq_len, config.dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=config.d_ff,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )

        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.n_layers,
            norm=nn.LayerNorm(config.d_model),
        )

        def _make_head() -> nn.Sequential:
            return nn.Sequential(
                nn.Linear(config.d_model, config.d_model // 2),
                nn.GELU(),
                nn.Linear(config.d_model // 2, 1),
            )

        self.head_3d = _make_head()
        self.head_5d = _make_head()
        self.head_10d = _make_head()

    def forward(
        self,
        x: torch.Tensor,
        labels: torch.Tensor | None = None,
        loss_weights: Iterable[float] | torch.Tensor | None = None,
    ) -> Mapping[str, torch.Tensor] | tuple[Mapping[str, torch.Tensor], Mapping[str, torch.Tensor]]:
        """前向推理。

        Args:
            x: [batch, seq_len, input_dim] 特征序列。
            labels: 可选，若提供则返回 (preds, losses)。
            loss_weights: 可选自定义损失权重。
        """
        if x.ndim != 3:
            raise ValueError("input tensor must be 3D: [batch, seq_len, input_dim]")

        batch_size, seq_len, _ = x.shape
        if seq_len < self.config.min_seq_len:
            raise ValueError(
                f"sequence length {seq_len} shorter than required minimum {self.config.min_seq_len}"
            )

        x = self.input_projection(x)
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x)
        pooled = x[:, -1, :]

        predictions: dict[str, torch.Tensor] = {
            "pred_3d": self.head_3d(pooled).squeeze(-1),
            "pred_5d": self.head_5d(pooled).squeeze(-1),
            "pred_10d": self.head_10d(pooled).squeeze(-1),
        }

        if labels is None:
            return predictions

        weights = loss_weights if loss_weights is not None else self.loss_weights
        total_loss, head_losses = compute_mtl_loss(predictions, labels, weights)
        return predictions, {"total": total_loss, **head_losses}


def create_mtl_model(
    input_dim: int = 6,
    d_model: int = 128,
    n_layers: int = 4,
    n_heads: int = 4,
    d_ff: int = 512,
    dropout: float = 0.1,
    max_seq_len: int = 512,
    min_seq_len: int = 30,
    loss_weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> "MTLTransformer":
    """便捷创建多任务Transformer模型。"""

    config = TransformerConfig(
        input_dim=input_dim,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        dropout=dropout,
        max_seq_len=max_seq_len,
        min_seq_len=min_seq_len,
        loss_weights=loss_weights,
    )
    return MTLTransformer(config)


# 向后兼容：旧接口引用到新的多任务模型
create_model = create_mtl_model
StockTransformer = MTLTransformer
