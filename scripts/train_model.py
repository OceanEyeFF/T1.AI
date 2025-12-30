#!/usr/bin/env python
"""训练Transformer模型

用法示例：
    python scripts/train_model.py \\
        --dataset data/datasets/dataset_65stocks_2021q3_2025q4 \\
        --epochs 100 \\
        --batch-size 512 \\
        --lr 1e-4
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import torch

from ashare_lab.models.transformer import create_model
from ashare_lab.training.trainer import Trainer, TrainerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="训练Transformer模型")
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="数据集目录路径",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="最大训练轮数（默认100）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=512,
        help="批次大小（默认512）",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="学习率（默认1e-4）",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=10,
        help="Early stopping patience（默认10）",
    )
    parser.add_argument(
        "--n-layers",
        type=int,
        default=12,
        help="Transformer编码器层数（默认12）",
    )
    parser.add_argument(
        "--d-model",
        type=int,
        default=256,
        help="隐藏层维度（默认256）",
    )
    parser.add_argument(
        "--n-heads",
        type=int,
        default=8,
        help="注意力头数（默认8）",
    )
    parser.add_argument(
        "--d-ff",
        type=int,
        default=1024,
        help="前馈网络维度（默认1024）",
    )
    parser.add_argument(
        "--dropout",
        type=float,
        default=0.3,
        help="Dropout比例（默认0.3）",
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="runs/checkpoints",
        help="模型保存目录（默认runs/checkpoints）",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Transformer模型训练")
    logger.info("=" * 60)

    # 1. 加载数据集
    dataset_dir = Path(args.dataset)
    if not dataset_dir.exists():
        logger.error(f"数据集目录不存在: {dataset_dir}")
        return

    logger.info(f"加载数据集: {dataset_dir}")

    train_df = pd.read_parquet(dataset_dir / "train.parquet")
    valid_df = pd.read_parquet(dataset_dir / "valid.parquet")

    logger.info(f"训练集: {len(train_df)} 条记录")
    logger.info(f"验证集: {len(valid_df)} 条记录")

    # 2. 特征列
    feature_cols = [
        "return_1d",
        "return_5d",
        "return_20d",
        "volume_ratio_5d",
        "volume_change",
        "amount_change",
    ]

    logger.info(f"特征维度: {len(feature_cols)}")

    # 3. 创建模型
    logger.info("创建Transformer模型...")
    logger.info(f"  - 编码器层数: {args.n_layers}")
    logger.info(f"  - 隐藏层维度: {args.d_model}")
    logger.info(f"  - 注意力头数: {args.n_heads}")
    logger.info(f"  - 前馈网络维度: {args.d_ff}")
    logger.info(f"  - Dropout: {args.dropout}")

    model = create_model(
        input_dim=len(feature_cols),
        d_model=args.d_model,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        d_ff=args.d_ff,
        dropout=args.dropout,
    )

    # 统计参数量
    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"模型参数量: {n_params:,}")

    # 4. 训练器配置
    config = TrainerConfig(
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_epochs=args.epochs,
        patience=args.patience,
        save_dir=Path(args.save_dir),
    )

    logger.info("训练器配置:")
    logger.info(f"  - 批次大小: {config.batch_size}")
    logger.info(f"  - 学习率: {config.learning_rate}")
    logger.info(f"  - 最大轮数: {config.max_epochs}")
    logger.info(f"  - Early stopping patience: {config.patience}")
    logger.info(f"  - 设备: {config.device}")

    # 5. 创建训练器并训练
    trainer = Trainer(
        model=model,
        config=config,
        train_data=train_df,
        valid_data=valid_df,
        feature_cols=feature_cols,
    )

    history = trainer.train()

    # 6. 保存训练历史
    history_df = pd.DataFrame(history)
    history_path = config.save_dir / "training_history.csv"
    history_df.to_csv(history_path, index=False)
    logger.info(f"训练历史已保存到: {history_path}")

    logger.info("=" * 60)
    logger.info("✅ 训练完成！")
    logger.info(f"最佳模型已保存到: {config.save_dir / 'best_model.pt'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
