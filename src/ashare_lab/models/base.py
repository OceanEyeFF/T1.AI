"""模型抽象基类。

统一接口：train / predict / save / load。
每个模型是自包含子文件夹（model.py + config.toml + checkpoints/）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# 训练/预测数据类型
# ---------------------------------------------------------------------------


@dataclass
class TrainingData:
    """训练数据容器。"""

    # X_train / X_valid: (N, seq_len, input_dim) 或 (N, input_dim)
    X_train: np.ndarray
    y_train: np.ndarray  # (N, num_horizons) 或 (N,)
    X_valid: np.ndarray
    y_valid: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionData:
    """预测数据容器。"""

    X: np.ndarray  # (N, seq_len, input_dim) 或 (N, input_dim)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingResult:
    """训练结果。"""

    model: Any  # 训练后的模型实例
    preds: np.ndarray | None = None  # valid 预测
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    """预测结果。"""

    preds: np.ndarray  # (N, num_horizons)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 模型抽象基类
# ---------------------------------------------------------------------------


class ModelABC(ABC):
    """模型抽象基类。

    子类实现 train/predict/save/load。
    每个模型放在独立的子文件夹中：

        transformer/
        ├── __init__.py
        ├── model.py       # class TransformerModel(ModelABC)
        ├── config.toml     # 模型超参数
        └── checkpoints/    # 训练产出
    """

    @abstractmethod
    def train(self, data: TrainingData) -> TrainingResult:
        """训练模型。

        Args:
            data: 训练 + 验证数据

        Returns:
            TrainingResult(model, preds, metrics, metadata)
        """
        ...

    @abstractmethod
    def predict(self, data: PredictionData) -> PredictionResult:
        """推理预测。

        Args:
            data: 预测输入

        Returns:
            PredictionResult(preds, metadata)
        """
        ...

    @abstractmethod
    def save(self, path: str | Path) -> None:
        """保存模型到指定路径。

        Args:
            path: 目录路径（checkpoint 文件写在 path 下）
        """
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: str | Path) -> "ModelABC":
        """从指定路径加载模型。

        Args:
            path: 目录路径（checkpoint 文件从 path 下读取）

        Returns:
            恢复的模型实例
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称，用作文件夹名和 registry key。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """一句话描述。"""
        ...
