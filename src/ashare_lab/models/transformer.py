"""向后兼容层 — 从 transformer 子文件夹重新导出核心符号。

新代码请使用：
    from ashare_lab.models import create_model
    model = create_model("transformer", d_model=128, ...)
"""

from .transformer._mtl_transformer import (
    MTLTransformer,
    PositionalEncoding,
    StockTransformer,
    TransformerConfig,
    compute_ic_aware_mtl_loss,
    compute_mtl_loss,
    create_model,
    create_mtl_model,
    freeze_encoder_layers,
)

__all__ = [
    "MTLTransformer",
    "PositionalEncoding",
    "StockTransformer",
    "TransformerConfig",
    "compute_ic_aware_mtl_loss",
    "compute_mtl_loss",
    "create_model",
    "create_mtl_model",
    "freeze_encoder_layers",
]
