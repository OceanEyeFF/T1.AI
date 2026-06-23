"""XGBoost 多 horizon 模型 — 适配 ModelABC 接口。

每个 horizon 独立训练一个 XGBRegressor（3 个独立模型）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ashare_lab.models.base import (
    ModelABC,
    PredictionData,
    PredictionResult,
    TrainingData,
    TrainingResult,
)
from ashare_lab.models.registry import register_model


@dataclass
class XgbConfig:
    """XGBoost 超参数配置。"""

    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: float = 1.0
    gamma: float = 0.0
    reg_alpha: float = 0.0
    reg_lambda: float = 1.0
    n_jobs: int = -1
    early_stopping_rounds: int = 20
    device: str = "cpu"
    random_seed: int = 42


class XGBoostModel(ModelABC):
    """XGBoost 多 horizon 回归模型。

    每个 horizon 独立训练一个 XGBRegressor。
    """

    def __init__(
        self, *, pred_cols: tuple[str, ...] = ("pred_3d", "pred_5d", "pred_10d"), **config: Any
    ) -> None:
        import xgboost as xgb

        self._xgb = xgb
        self._config = XgbConfig(
            **{k: v for k, v in config.items() if k in XgbConfig.__dataclass_fields__}
        )
        self.pred_cols = tuple(pred_cols)
        self._models: list[Any] = []

    @property
    def name(self) -> str:
        return "xgboost"

    @property
    def description(self) -> str:
        return "XGBoost 多 horizon 独立回归（每个 horizon 独立模型）"

    def train(self, data: TrainingData) -> TrainingResult:
        cfg = self._config
        self._models = []
        val_pred = np.zeros((data.X_valid.shape[0], len(self.pred_cols)), dtype=np.float32)
        t0 = time.perf_counter()
        metrics: dict[str, float] = {}

        for h in range(len(self.pred_cols)):
            ytr = data.y_train[:, h]
            yva = data.y_valid[:, h]
            mask_tr = np.isfinite(ytr)
            mask_va = np.isfinite(yva)

            if mask_tr.sum() < 32:
                continue

            model = self._xgb.XGBRegressor(
                n_estimators=cfg.n_estimators,
                max_depth=cfg.max_depth,
                learning_rate=cfg.learning_rate,
                subsample=cfg.subsample,
                colsample_bytree=cfg.colsample_bytree,
                min_child_weight=cfg.min_child_weight,
                gamma=cfg.gamma,
                reg_alpha=cfg.reg_alpha,
                reg_lambda=cfg.reg_lambda,
                objective="reg:squarederror",
                tree_method="hist",
                device=cfg.device,
                random_state=cfg.random_seed + h,
                n_jobs=cfg.n_jobs,
                eval_metric="mae",
                early_stopping_rounds=cfg.early_stopping_rounds
                if cfg.early_stopping_rounds > 0
                else None,
            )
            model.fit(
                data.X_train[mask_tr],
                ytr[mask_tr],
                eval_set=[(data.X_valid[mask_va], yva[mask_va])],
                verbose=False,
            )
            self._models.append(model)
            val_pred[mask_va, h] = model.predict(data.X_valid[mask_va])
            metrics[f"best_iteration_h{h}"] = (
                float(model.best_iteration) if model.best_iteration else 0
            )

        metrics["train_time_s"] = round(time.perf_counter() - t0, 1)
        return TrainingResult(model=self, preds=val_pred, metrics=metrics)

    def predict(self, data: PredictionData) -> PredictionResult:
        preds = np.zeros((data.X.shape[0], len(self.pred_cols)), dtype=np.float32)
        for h, model in enumerate(self._models):
            if model is not None:
                preds[:, h] = model.predict(data.X)
        return PredictionResult(preds=preds)

    def save(self, path: str | Path) -> None:
        import joblib

        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        for h, model in enumerate(self._models):
            if model is not None:
                joblib.dump(model, p / f"model_h{h}.joblib")

    @classmethod
    def load(cls, path: str | Path) -> "XGBoostModel":
        import joblib
        from glob import glob

        p = Path(path)
        inst = cls.__new__(cls)
        import xgboost as xgb

        inst._xgb = xgb
        inst._config = XgbConfig()
        inst._models = []
        for h in range(len(inst.pred_cols)):
            f = p / f"model_h{h}.joblib"
            if f.exists():
                inst._models.append(joblib.load(f))
            else:
                inst._models.append(None)
        return inst


register_model("xgboost", XGBoostModel)
