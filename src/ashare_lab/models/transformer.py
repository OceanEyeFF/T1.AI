"""Transformer模型用于股票超额收益预测

使用标准Transformer Encoder架构，针对时序数据优化。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn


@dataclass
class TransformerConfig:
    """Transformer模型配置"""

    input_dim: int = 6  # 输入特征维度
    d_model: int = 256  # 隐藏层维度
    n_heads: int = 8  # 注意力头数
    n_layers: int = 12  # 编码器层数
    d_ff: int = 1024  # 前馈网络维度
    dropout: float = 0.3  # Dropout比例（强正则化）
    max_seq_len: int = 1  # 最大序列长度（日频数据，每天一条）


class PositionalEncoding(nn.Module):
    """位置编码（虽然序列长度=1，但保留接口以便未来扩展）"""

    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # 创建位置编码矩阵
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


class StockTransformer(nn.Module):
    """股票超额收益预测Transformer模型

    架构：
        输入层 -> Transformer Encoder (n_layers) -> 全连接层 -> 输出

    特点：
        - 强正则化（dropout=0.3）防止过拟合
        - LayerNorm稳定训练
        - 残差连接加速收敛
    """

    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.config = config

        # 输入投影层（将特征维度映射到d_model）
        self.input_projection = nn.Linear(config.input_dim, config.d_model)

        # 位置编码
        self.pos_encoder = PositionalEncoding(
            config.d_model, config.max_seq_len, config.dropout
        )

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=config.d_ff,
            dropout=config.dropout,
            activation="gelu",  # GELU激活函数（比ReLU更平滑）
            batch_first=True,
            norm_first=True,  # Pre-LN架构，训练更稳定
        )

        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.n_layers,
            norm=nn.LayerNorm(config.d_model),
        )

        # 输出头
        self.output_head = nn.Sequential(
            nn.Linear(config.d_model, config.d_model // 2),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model // 2, 1),  # 回归任务，输出1个值
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, seq_len, input_dim] 输入特征

        Returns:
            [batch_size, 1] 预测的超额收益
        """
        # 输入投影：[batch, seq_len, input_dim] -> [batch, seq_len, d_model]
        x = self.input_projection(x)

        # 位置编码
        x = self.pos_encoder(x)

        # Transformer Encoder
        x = self.transformer_encoder(x)

        # 取最后一个时间步（对于seq_len=1，就是唯一的时间步）
        x = x[:, -1, :]  # [batch, d_model]

        # 输出预测
        out = self.output_head(x)  # [batch, 1]

        return out.squeeze(-1)  # [batch]


def create_model(
    input_dim: int = 6,
    d_model: int = 256,
    n_layers: int = 12,
    n_heads: int = 8,
    d_ff: int = 1024,
    dropout: float = 0.3,
) -> StockTransformer:
    """创建Transformer模型的便捷函数

    Args:
        input_dim: 输入特征维度（默认6）
        d_model: 隐藏层维度（默认256）
        n_layers: 编码器层数（默认12）
        n_heads: 注意力头数（默认8）
        d_ff: 前馈网络维度（默认1024）
        dropout: Dropout比例（默认0.3）

    Returns:
        配置好的StockTransformer模型
    """
    config = TransformerConfig(
        input_dim=input_dim,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        dropout=dropout,
    )
    return StockTransformer(config)
