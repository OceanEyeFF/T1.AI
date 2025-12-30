#!/usr/bin/env python
"""构建训练数据集

用法示例：
    # 使用默认配置（3 只股票，2023 年数据）
    python scripts/build_dataset.py

    # 指定股票和日期范围
    python scripts/build_dataset.py \\
        --symbols 600519,000333,601318 \\
        --start 20220101 \\
        --end 20231231 \\
        --name my_dataset

    # 使用股票池快照
    python scripts/build_dataset.py \\
        --universe data/cache/universe/20231231.csv \\
        --start 20220101 \\
        --end 20231231
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from ashare_lab.dataset.builder import DatasetBuilder, DatasetConfig
from ashare_lab.features.momentum import Return1D, Return5D, Return20D
from ashare_lab.features.volume import AmountChange, VolumeChange, VolumeRatio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_symbols_from_universe(universe_path: Path) -> list[str]:
    """从股票池快照加载股票列表"""
    df = pd.read_csv(universe_path)
    return df["code"].tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description="构建训练数据集")

    # 股票选择（二选一）
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--symbols",
        type=str,
        help="股票代码列表（逗号分隔），例如：600519,000333,601318",
    )
    group.add_argument(
        "--universe",
        type=Path,
        help="股票池快照文件路径，例如：data/cache/universe/20231231.csv",
    )

    # 日期范围
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="开始日期（YYYYMMDD）",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="结束日期（YYYYMMDD）",
    )

    # 数据集切分
    parser.add_argument(
        "--train-end",
        type=str,
        help="训练集结束日期（YYYYMMDD），默认为总时间的 70%%",
    )
    parser.add_argument(
        "--valid-end",
        type=str,
        help="验证集结束日期（YYYYMMDD），默认为总时间的 85%%",
    )

    # 输出配置
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="数据集名称，默认为 dataset_<timestamp>",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/datasets"),
        help="输出目录，默认为 data/datasets",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/cache"),
        help="缓存目录，默认为 data/cache",
    )

    # 特征配置
    parser.add_argument(
        "--label-type",
        type=str,
        choices=["excess_return", "forward_return"],
        default="excess_return",
        help="标签类型，默认为 excess_return（超额收益）",
    )

    args = parser.parse_args()

    # 加载股票列表
    if args.symbols:
        symbols = args.symbols.split(",")
    else:
        symbols = load_symbols_from_universe(args.universe)

    logger.info(f"加载股票列表: {len(symbols)} 只股票")

    # 自动计算切分日期（如果未指定）
    start_date = pd.to_datetime(args.start, format="%Y%m%d")
    end_date = pd.to_datetime(args.end, format="%Y%m%d")
    total_days = (end_date - start_date).days

    if args.train_end is None:
        train_end_date = start_date + pd.Timedelta(days=int(total_days * 0.7))
        args.train_end = train_end_date.strftime("%Y%m%d")

    if args.valid_end is None:
        valid_end_date = start_date + pd.Timedelta(days=int(total_days * 0.85))
        args.valid_end = valid_end_date.strftime("%Y%m%d")

    # 生成数据集名称（如果未指定）
    if args.name is None:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.name = f"dataset_{timestamp}"

    # 定义特征列表（默认使用所有实现的特征）
    features = [
        Return1D(),
        Return5D(),
        Return20D(),
        VolumeRatio(window=5),
        VolumeChange(),
        AmountChange(),
    ]

    logger.info(f"使用 {len(features)} 个特征")

    # 创建配置
    config = DatasetConfig(
        name=args.name,
        symbols=symbols,
        start_date=args.start,
        end_date=args.end,
        features=features,
        label_type=args.label_type,
        train_end_date=args.train_end,
        valid_end_date=args.valid_end,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
    )

    # 构建数据集
    builder = DatasetBuilder(config)
    output_path = builder.build()

    logger.info("=" * 60)
    logger.info("数据集构建完成！")
    logger.info(f"输出目录: {output_path}")
    logger.info(f"数据集名称: {args.name}")
    logger.info(f"股票数量: {len(symbols)}")
    logger.info(f"特征数量: {len(features)}")
    logger.info(f"标签类型: {args.label_type}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
