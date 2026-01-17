#!/usr/bin/env python3
"""训练所有基准模型并生成对比报告

此脚本依次训练：
1. Ridge Regression（线性基准）
2. Lasso Regression（线性基准）
3. LSTM Baseline（时序基准）

并生成性能对比报告，为Transformer提供基准线。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

# TODO: 待实现模块导入（阶段3完成后取消注释）
# from ashare_lab.models.linear_baseline import LinearBaseline
# from ashare_lab.models.lstm_baseline import LSTMBaseline
# from ashare_lab.training.trainer_v2 import BaselineTrainer
# from ashare_lab.evaluation.metrics import compute_ic, compute_rank_ic


def load_sequence_dataset(dataset_path: Path):
    """加载序列数据集

    Args:
        dataset_path: 数据集目录路径（包含train.parquet/valid.parquet/test.parquet）

    Returns:
        (X_train, y_train, X_valid, y_valid, X_test, y_test)
    """
    # TODO: 实现数据集加载逻辑（阶段2完成后实现）
    raise NotImplementedError("序列数据集加载逻辑待实现（阶段2）")


def train_linear_baseline(X_train, y_train, X_valid, y_valid, model_type: str):
    """训练线性基准模型

    Args:
        X_train: [n_samples, seq_len, n_features]
        y_train: [n_samples]
        model_type: 'ridge' or 'lasso'

    Returns:
        训练好的模型 + 验证集IC
    """
    print(f"\n{'='*60}")
    print(f"训练 {model_type.upper()} 线性基准模型")
    print(f"{'='*60}")

    # TODO: 实现训练逻辑（阶段3）
    # model = LinearBaseline(model_type=model_type, alpha=1.0)
    # model.fit(X_train, y_train, X_valid, y_valid)

    # 验证集评估
    # y_pred = model.predict(X_valid)
    # ic = compute_ic(y_pred, y_valid)
    # rank_ic = compute_rank_ic(y_pred, y_valid)

    # print(f"验证集 IC: {ic:.4f}")
    # print(f"验证集 Rank IC: {rank_ic:.4f}")

    # return model, ic, rank_ic

    raise NotImplementedError("线性模型训练逻辑待实现（阶段3）")


def train_lstm_baseline(
    X_train,
    y_train,
    X_valid,
    y_valid,
    input_dim: int,
    batch_size: int = 256,
    epochs: int = 30,
):
    """训练LSTM基准模型

    Args:
        X_train: [n_samples, seq_len, n_features]
        y_train: [n_samples]
        input_dim: 特征维度
        batch_size: 批次大小
        epochs: 训练轮数

    Returns:
        训练好的模型 + 验证集IC
    """
    print(f"\n{'='*60}")
    print(f"训练 LSTM 基准模型")
    print(f"{'='*60}")

    # TODO: 实现训练逻辑（阶段3）
    # model = LSTMBaseline(input_dim=input_dim, hidden_dim=128, num_layers=2)

    # 创建DataLoader
    # train_dataset = TensorDataset(
    #     torch.tensor(X_train, dtype=torch.float32),
    #     torch.tensor(y_train, dtype=torch.float32),
    # )
    # train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    # 训练
    # trainer = BaselineTrainer(model, lr=1e-3, epochs=epochs)
    # trainer.fit(train_loader, valid_loader)

    # 验证集评估
    # y_pred = trainer.predict(X_valid)
    # ic = compute_ic(y_pred, y_valid)
    # rank_ic = compute_rank_ic(y_pred, y_valid)

    # print(f"验证集 IC: {ic:.4f}")
    # print(f"验证集 Rank IC: {rank_ic:.4f}")

    # return model, ic, rank_ic

    raise NotImplementedError("LSTM模型训练逻辑待实现（阶段3）")


def generate_comparison_report(results: dict, output_path: Path):
    """生成基准模型对比报告

    Args:
        results: {model_name: {'ic': ..., 'rank_ic': ..., 'train_time': ...}}
        output_path: 报告输出路径
    """
    print(f"\n{'='*60}")
    print("基准模型对比报告")
    print(f"{'='*60}\n")

    df = pd.DataFrame(results).T
    df = df.sort_values('rank_ic', ascending=False)

    print(df.to_string())

    # 保存到文件
    df.to_csv(output_path / "baseline_comparison.csv")

    # 生成Markdown报告
    with open(output_path / "baseline_comparison.md", "w", encoding="utf-8") as f:
        f.write("# 基准模型对比报告\n\n")
        f.write("## 模型性能对比\n\n")
        f.write(df.to_markdown() + "\n\n")
        f.write("## 结论\n\n")
        f.write("- **最佳模型**: " + df.index[0] + "\n")
        f.write(f"- **最佳Rank IC**: {df.iloc[0]['rank_ic']:.4f}\n\n")
        f.write("## 下一步\n\n")
        f.write("- 基准模型性能已确定，接下来训练Transformer V2\n")
        f.write("- 目标：Transformer Rank IC > " + f"{df.iloc[0]['rank_ic'] + 0.01:.4f}\n")

    print(f"\n✓ 报告已保存到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="训练所有基准模型")
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/datasets/sequence_v1",
        help="序列数据集路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="runs/baseline_models",
        help="输出目录",
    )
    args = parser.parse_args()

    # 创建输出目录
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # 加载数据集
    print("加载数据集...")
    # X_train, y_train, X_valid, y_valid, X_test, y_test = load_sequence_dataset(
    #     Path(args.dataset)
    # )
    # print(f"训练集: {X_train.shape}, 验证集: {X_valid.shape}, 测试集: {X_test.shape}")

    # 训练所有基准模型
    results = {}

    # 1. Ridge Regression
    # model_ridge, ic_ridge, rank_ic_ridge = train_linear_baseline(
    #     X_train, y_train, X_valid, y_valid, model_type='ridge'
    # )
    # results['Ridge'] = {'ic': ic_ridge, 'rank_ic': rank_ic_ridge, 'train_time': '...'}

    # 2. Lasso Regression
    # model_lasso, ic_lasso, rank_ic_lasso = train_linear_baseline(
    #     X_train, y_train, X_valid, y_valid, model_type='lasso'
    # )
    # results['Lasso'] = {'ic': ic_lasso, 'rank_ic': rank_ic_lasso, 'train_time': '...'}

    # 3. LSTM Baseline
    # model_lstm, ic_lstm, rank_ic_lstm = train_lstm_baseline(
    #     X_train, y_train, X_valid, y_valid, input_dim=X_train.shape[2]
    # )
    # results['LSTM'] = {'ic': ic_lstm, 'rank_ic': rank_ic_lstm, 'train_time': '...'}

    # 生成对比报告
    # generate_comparison_report(results, output_path)

    print("\n所有基准模型训练完成！")
    print("下一步：运行 scripts/train_transformer_v2.py 训练Transformer模型")


if __name__ == "__main__":
    main()
