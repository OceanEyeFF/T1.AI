#!/usr/bin/env python
"""在测试集上评估训练好的Transformer模型

用法示例：
    python scripts/evaluate_model.py \
        --checkpoint runs/transformer_12layers/best_model.pt \
        --dataset data/datasets/dataset_65stocks_2021q3_2025q4
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ashare_lab.evaluation.metrics import evaluate_model
from ashare_lab.models.transformer import create_model
from ashare_lab.training.trainer import StockDataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="评估Transformer模型")
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="模型检查点路径",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="数据集目录路径",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="计算设备（默认自动选择）",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Transformer模型测试集评估")
    logger.info("=" * 60)

    # 1. 加载测试数据集
    dataset_dir = Path(args.dataset)
    test_path = dataset_dir / "test.parquet"

    if not test_path.exists():
        logger.error(f"测试集文件不存在: {test_path}")
        return

    logger.info(f"加载测试集: {test_path}")
    test_df = pd.read_parquet(test_path)
    logger.info(f"测试集样本数: {len(test_df)}")

    # 2. 特征列（与训练时一致）
    feature_cols = [
        "return_1d",
        "return_5d",
        "return_20d",
        "volume_ratio_5d",
        "volume_change",
        "amount_change",
    ]

    # 3. 创建测试数据集
    test_dataset = StockDataset(test_df, feature_cols, label_col="label")
    logger.info(f"有效测试样本数（去除NaN后）: {len(test_dataset)}")

    # 4. 加载模型检查点
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        logger.error(f"模型检查点不存在: {checkpoint_path}")
        return

    logger.info(f"加载模型检查点: {checkpoint_path}")

    device = torch.device(args.device)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)

    # 5. 创建模型并加载权重
    # 从检查点推断模型配置（假设使用默认参数）
    model = create_model(
        input_dim=len(feature_cols),
        d_model=256,
        n_layers=12,
        n_heads=8,
        d_ff=1024,
        dropout=0.3,
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"模型参数量: {n_params:,}")
    logger.info(f"设备: {device}")

    # 6. 生成预测
    logger.info("=" * 60)
    logger.info("生成测试集预测...")
    logger.info("=" * 60)

    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for i in range(len(test_dataset)):
            features, label = test_dataset[i]
            features = features.unsqueeze(0).to(device)  # [1, 1, n_features]

            prediction = model(features)
            all_predictions.append(prediction.cpu().item())
            all_labels.append(label.item())

    all_predictions = np.array(all_predictions)
    all_labels = np.array(all_labels)

    # 7. 计算评估指标
    logger.info("=" * 60)
    logger.info("计算评估指标...")
    logger.info("=" * 60)

    metrics = evaluate_model(all_predictions, all_labels)

    logger.info("测试集性能指标:")
    logger.info(f"  - MSE:     {metrics['mse']:.6f}")
    logger.info(f"  - MAE:     {metrics['mae']:.6f}")
    logger.info(f"  - IC:      {metrics['ic']:.4f}")
    logger.info(f"  - RankIC:  {metrics['rank_ic']:.4f}")

    # 8. 统计分析
    logger.info("=" * 60)
    logger.info("预测统计分析:")
    logger.info("=" * 60)

    logger.info("预测值分布:")
    logger.info(f"  - 均值:    {np.mean(all_predictions):.6f}")
    logger.info(f"  - 标准差:  {np.std(all_predictions):.6f}")
    logger.info(f"  - 最小值:  {np.min(all_predictions):.6f}")
    logger.info(f"  - 最大值:  {np.max(all_predictions):.6f}")

    logger.info("真实标签分布:")
    logger.info(f"  - 均值:    {np.mean(all_labels):.6f}")
    logger.info(f"  - 标准差:  {np.std(all_labels):.6f}")
    logger.info(f"  - 最小值:  {np.min(all_labels):.6f}")
    logger.info(f"  - 最大值:  {np.max(all_labels):.6f}")

    # 9. 保存预测结果
    results_df = pd.DataFrame(
        {
            "prediction": all_predictions,
            "label": all_labels,
            "error": all_predictions - all_labels,
            "abs_error": np.abs(all_predictions - all_labels),
        }
    )

    output_dir = checkpoint_path.parent
    results_path = output_dir / "test_predictions.csv"
    results_df.to_csv(results_path, index=False)
    logger.info(f"预测结果已保存到: {results_path}")

    # 10. 保存评估指标
    metrics_df = pd.DataFrame([metrics])
    metrics_path = output_dir / "test_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    logger.info(f"评估指标已保存到: {metrics_path}")

    # 11. 性能判断
    logger.info("=" * 60)
    logger.info("性能评估:")
    logger.info("=" * 60)

    if abs(metrics["ic"]) < 0.02:
        logger.warning("⚠️  IC绝对值 < 0.02: 预测能力极弱")
    elif abs(metrics["ic"]) < 0.05:
        logger.info("⚠️  IC绝对值 < 0.05: 预测能力较弱")
    elif abs(metrics["ic"]) < 0.10:
        logger.info("✅ IC绝对值 < 0.10: 预测能力中等")
    else:
        logger.info("✅ IC绝对值 ≥ 0.10: 预测能力较强")

    if abs(metrics["rank_ic"]) < 0.02:
        logger.warning("⚠️  RankIC绝对值 < 0.02: 排序能力极弱")
    elif abs(metrics["rank_ic"]) < 0.05:
        logger.info("⚠️  RankIC绝对值 < 0.05: 排序能力较弱")
    elif abs(metrics["rank_ic"]) < 0.10:
        logger.info("✅ RankIC绝对值 < 0.10: 排序能力中等")
    else:
        logger.info("✅ RankIC绝对值 ≥ 0.10: 排序能力较强")

    logger.info("=" * 60)
    logger.info("✅ 评估完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
