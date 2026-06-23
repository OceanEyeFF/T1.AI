"""Transformer 模型 — 适配 ModelABC 接口。

向后兼容：旧代码 `from ashare_lab.models.transformer import create_mtl_model` 仍可用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from ashare_lab.models.base import (
    ModelABC,
    PredictionData,
    PredictionResult,
    TrainingData,
    TrainingResult,
)
from ashare_lab.models.registry import register_model

from ._mtl_transformer import MTLTransformer, TransformerConfig

# 向后兼容：重新导出 -------
from ._mtl_transformer import (
    EarlyStoppingIC,
    PositionalEncoding,
    StockTransformer,
    compute_ic_aware_mtl_loss,
    compute_mtl_loss,
    create_model,
    create_mtl_model,
    freeze_encoder_layers,
)


class TransformerModel(ModelABC):
    """共享编码器 + 多任务回归头的 Transformer。

    继承自 ModelABC，封装 MTLTransformer 的训练/推理/保存/加载。
    """

    def __init__(self, **config: Any) -> None:
        cfg = TransformerConfig(**config)
        self._config = cfg
        self._model = MTLTransformer(cfg)
        self._device = torch.device("cpu")

    # ---- ModelABC 接口 ----

    @property
    def name(self) -> str:
        return "transformer"

    @property
    def description(self) -> str:
        return "共享编码器 + 多任务回归头 Transformer"

    def train(self, data: TrainingData) -> TrainingResult:
        self._model.to(self._device)
        self._model.train()
        optimizer = torch.optim.AdamW(self._model.parameters(), lr=1e-4, weight_decay=1e-5)

        Xt = torch.from_numpy(data.X_train).float().to(self._device)
        yt = torch.from_numpy(data.y_train).float().to(self._device)
        Xv = torch.from_numpy(data.X_valid).float().to(self._device)
        yv = torch.from_numpy(data.y_valid).float().to(self._device)

        best_loss = float("inf")
        best_state = None
        patience = 10
        no_improve = 0

        for epoch in range(self._config.get("max_epochs", 50)):
            optimizer.zero_grad()
            _, losses = self._model(Xt, yt)
            loss = losses["total"]
            loss.backward()
            optimizer.step()

            with torch.no_grad():
                _, val_losses = self._model(Xv, yv)
                val_loss = val_losses["total"].item()

            if val_loss < best_loss - 1e-5:
                best_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in self._model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        if best_state is not None:
            self._model.load_state_dict(best_state)

        preds, _ = self._model(Xv)
        preds_np = torch.stack([preds[k] for k in self._model.heads.keys()], dim=1).cpu().numpy()

        return TrainingResult(
            model=self,
            preds=preds_np,
            metrics={"best_val_loss": float(best_loss)},
        )

    def predict(self, data: PredictionData) -> PredictionResult:
        self._model.to(self._device)
        self._model.eval()
        with torch.no_grad():
            Xt = torch.from_numpy(data.X).float().to(self._device)
            preds = self._model(Xt)
            preds_np = (
                torch.stack([preds[k] for k in self._model.heads.keys()], dim=1).cpu().numpy()
            )
        return PredictionResult(preds=preds_np)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.state_dict(), p / "checkpoint.pt")

    @classmethod
    def load(cls, path: str | Path) -> "TransformerModel":
        from ._mtl_transformer import TransformerConfig as TC, MTLTransformer as MT

        p = Path(path)
        state = torch.load(p / "checkpoint.pt", map_location="cpu", weights_only=True)
        # 从 state_dict 推断 config
        config = TC()
        model = MT(config)
        model.load_state_dict(state)
        inst = cls.__new__(cls)
        inst._config = config
        inst._model = model
        inst._device = torch.device("cpu")
        return inst


# 注册
register_model("transformer", TransformerModel)
