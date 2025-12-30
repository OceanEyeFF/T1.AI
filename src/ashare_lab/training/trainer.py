"""Transformer模型训练器

支持early stopping、学习率调度、模型检查点保存等功能。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from ashare_lab.evaluation.metrics import evaluate_model

logger = logging.getLogger(__name__)


@dataclass
class TrainerConfig:
    """训练器配置"""

    # 训练超参数
    batch_size: int = 512
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    max_epochs: int = 100

    # Early stopping
    patience: int = 10  # 验证集性能不提升的容忍轮数
    min_delta: float = 1e-5  # 最小改进阈值

    # 学习率调度
    lr_scheduler: str = "reduce_on_plateau"  # 'reduce_on_plateau' or 'cosine'
    lr_patience: int = 5
    lr_factor: float = 0.5

    # 设备
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    # 检查点
    save_dir: Path = Path("runs/checkpoints")
    save_best_only: bool = True


class StockDataset(Dataset):
    """股票数据集（PyTorch Dataset）"""

    def __init__(
        self,
        data: pd.DataFrame,
        feature_cols: list[str],
        label_col: str = "label",
    ):
        """
        Args:
            data: 数据DataFrame
            feature_cols: 特征列名列表
            label_col: 标签列名
        """
        # 移除含有NaN的行
        self.data = data.dropna(subset=feature_cols + [label_col])

        self.features = self.data[feature_cols].values.astype(np.float32)
        self.labels = self.data[label_col].values.astype(np.float32)

        # 添加序列维度（seq_len=1）
        self.features = self.features[:, np.newaxis, :]  # [n_samples, 1, n_features]

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return (
            torch.from_numpy(self.features[idx]),  # [1, n_features]
            torch.tensor(self.labels[idx]),  # scalar
        )


class EarlyStopping:
    """Early Stopping机制"""

    def __init__(self, patience: int = 10, min_delta: float = 1e-5):
        """
        Args:
            patience: 容忍的轮数
            min_delta: 最小改进阈值
        """
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score = None
        self.early_stop = False

    def __call__(self, val_loss: float) -> bool:
        """
        Args:
            val_loss: 验证集损失

        Returns:
            是否应该停止训练
        """
        score = -val_loss  # 转换为越大越好

        if self.best_score is None:
            self.best_score = score
        elif score < self.best_score + self.min_delta:
            self.counter += 1
            logger.info(f"EarlyStopping counter: {self.counter}/{self.patience}")
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.counter = 0

        return self.early_stop


class Trainer:
    """Transformer模型训练器"""

    def __init__(
        self,
        model: nn.Module,
        config: TrainerConfig,
        train_data: pd.DataFrame,
        valid_data: pd.DataFrame,
        feature_cols: list[str],
    ):
        """
        Args:
            model: Transformer模型
            config: 训练器配置
            train_data: 训练集DataFrame
            valid_data: 验证集DataFrame
            feature_cols: 特征列名列表
        """
        self.model = model
        self.config = config
        self.feature_cols = feature_cols

        # 数据集和DataLoader
        self.train_dataset = StockDataset(train_data, feature_cols)
        self.valid_dataset = StockDataset(valid_data, feature_cols)

        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=config.batch_size,
            shuffle=True,
            num_workers=0,  # Windows兼容性
        )

        self.valid_loader = DataLoader(
            self.valid_dataset,
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=0,
        )

        # 设备
        self.device = torch.device(config.device)
        self.model.to(self.device)

        # 损失函数和优化器
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )

        # 学习率调度器
        if config.lr_scheduler == "reduce_on_plateau":
            self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer,
                mode="min",
                factor=config.lr_factor,
                patience=config.lr_patience,
            )
        elif config.lr_scheduler == "cosine":
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=config.max_epochs,
            )

        # Early Stopping
        self.early_stopping = EarlyStopping(
            patience=config.patience,
            min_delta=config.min_delta,
        )

        # 历史记录
        self.history = {
            "train_loss": [],
            "valid_loss": [],
            "valid_ic": [],
            "valid_rank_ic": [],
            "learning_rate": [],
        }

        # 最佳模型
        self.best_valid_loss = float("inf")
        self.best_epoch = 0

    def train_epoch(self) -> float:
        """训练一个epoch

        Returns:
            平均训练损失
        """
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for features, labels in self.train_loader:
            features = features.to(self.device)
            labels = labels.to(self.device)

            # 前向传播
            self.optimizer.zero_grad()
            predictions = self.model(features)
            loss = self.criterion(predictions, labels)

            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)  # 梯度裁剪
            self.optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        return total_loss / n_batches

    @torch.no_grad()
    def validate(self) -> dict[str, float]:
        """在验证集上评估

        Returns:
            评估指标字典
        """
        self.model.eval()
        total_loss = 0.0
        n_batches = 0

        all_predictions = []
        all_labels = []

        for features, labels in self.valid_loader:
            features = features.to(self.device)
            labels = labels.to(self.device)

            predictions = self.model(features)
            loss = self.criterion(predictions, labels)

            total_loss += loss.item()
            n_batches += 1

            all_predictions.append(predictions.cpu().numpy())
            all_labels.append(labels.cpu().numpy())

        # 合并所有批次
        all_predictions = np.concatenate(all_predictions)
        all_labels = np.concatenate(all_labels)

        # 计算评估指标
        metrics = evaluate_model(all_predictions, all_labels)
        metrics["loss"] = total_loss / n_batches

        return metrics

    def train(self) -> dict:
        """完整训练流程

        Returns:
            训练历史字典
        """
        logger.info("=" * 60)
        logger.info("开始训练...")
        logger.info(f"设备: {self.device}")
        logger.info(f"训练样本数: {len(self.train_dataset)}")
        logger.info(f"验证样本数: {len(self.valid_dataset)}")
        logger.info("=" * 60)

        for epoch in range(1, self.config.max_epochs + 1):
            # 训练
            train_loss = self.train_epoch()

            # 验证
            valid_metrics = self.validate()
            valid_loss = valid_metrics["loss"]

            # 记录
            current_lr = self.optimizer.param_groups[0]["lr"]
            self.history["train_loss"].append(train_loss)
            self.history["valid_loss"].append(valid_loss)
            self.history["valid_ic"].append(valid_metrics["ic"])
            self.history["valid_rank_ic"].append(valid_metrics["rank_ic"])
            self.history["learning_rate"].append(current_lr)

            # 日志
            logger.info(
                f"Epoch {epoch}/{self.config.max_epochs} - "
                f"Train Loss: {train_loss:.6f}, "
                f"Valid Loss: {valid_loss:.6f}, "
                f"IC: {valid_metrics['ic']:.4f}, "
                f"RankIC: {valid_metrics['rank_ic']:.4f}, "
                f"LR: {current_lr:.2e}"
            )

            # 学习率调度
            if self.config.lr_scheduler == "reduce_on_plateau":
                self.scheduler.step(valid_loss)
            else:
                self.scheduler.step()

            # 保存最佳模型
            if valid_loss < self.best_valid_loss:
                self.best_valid_loss = valid_loss
                self.best_epoch = epoch
                self.save_checkpoint("best_model.pt")
                logger.info(f"✅ 保存最佳模型（Epoch {epoch}）")

            # Early Stopping
            if self.early_stopping(valid_loss):
                logger.info(f"Early stopping triggered at epoch {epoch}")
                break

        logger.info("=" * 60)
        logger.info("训练完成！")
        logger.info(f"最佳Epoch: {self.best_epoch}")
        logger.info(f"最佳验证损失: {self.best_valid_loss:.6f}")
        logger.info("=" * 60)

        return self.history

    def save_checkpoint(self, filename: str) -> None:
        """保存模型检查点

        Args:
            filename: 文件名
        """
        self.config.save_dir.mkdir(parents=True, exist_ok=True)
        path = self.config.save_dir / filename

        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "history": self.history,
            "best_valid_loss": self.best_valid_loss,
            "best_epoch": self.best_epoch,
        }

        torch.save(checkpoint, path)

    def load_checkpoint(self, filename: str) -> None:
        """加载模型检查点

        Args:
            filename: 文件名
        """
        path = self.config.save_dir / filename
        checkpoint = torch.load(path, map_location=self.device, weights_only=True)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.history = checkpoint["history"]
        self.best_valid_loss = checkpoint["best_valid_loss"]
        self.best_epoch = checkpoint["best_epoch"]

        logger.info(f"从 {path} 加载检查点")
