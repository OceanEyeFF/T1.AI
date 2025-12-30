#!/usr/bin/env python
"""构建多股票数据集

从选股结果CSV中读取股票列表，构建完整数据集。

用法示例：
    python scripts/build_dataset_multi_stock.py \\
        --input data/cache/selected_stocks_20210701.csv \\
        --name dataset_65stocks_2021q3_2025q4 \\
        --start 20210701 \\
        --end 20251115
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


def main() -> None:
    parser = argparse.ArgumentParser(description="构建多股票数据集")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="选股结果CSV文件路径",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="数据集名称",
    )
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="开始日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="结束日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="训练集比例 (默认0.7)",
    )
    parser.add_argument(
        "--valid-ratio",
        type=float,
        default=0.85,
        help="验证集比例 (默认0.85，即训练+验证占85%%)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("构建多股票数据集")
    logger.info("=" * 60)

    # 1. 读取股票列表
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"选股结果文件不存在: {input_path}")
        return

    df = pd.read_csv(input_path, dtype={"code": str})
    df["code"] = df["code"].str.zfill(6)  # 补齐前导零
    symbols = df["code"].unique().tolist()

    logger.info(f"从 {input_path} 读取到 {len(symbols)} 只股票（去重后）")

    # 2. 计算切分日期
    start_date = pd.to_datetime(args.start, format="%Y%m%d")
    end_date = pd.to_datetime(args.end, format="%Y%m%d")
    date_range = pd.date_range(start_date, end_date, freq="D")
    total_days = len(date_range)

    train_end_idx = int(total_days * args.train_ratio)
    valid_end_idx = int(total_days * args.valid_ratio)

    train_end_date = date_range[train_end_idx].strftime("%Y%m%d")
    valid_end_date = date_range[valid_end_idx].strftime("%Y%m%d")

    logger.info(f"日期范围: {args.start} ~ {args.end} (共 {total_days} 天)")
    logger.info(f"训练集结束日期: {train_end_date}")
    logger.info(f"验证集结束日期: {valid_end_date}")

    # 3. 配置特征和标签
    features = [
        Return1D(),
        Return5D(),
        Return20D(),
        VolumeRatio(window=5),
        VolumeChange(),
        AmountChange(),
    ]

    config = DatasetConfig(
        name=args.name,
        symbols=symbols,
        start_date=args.start,
        end_date=args.end,
        features=features,
        label_type="excess_return",  # 超额收益标签
        benchmark_code="000300",  # 沪深300
        train_end_date=train_end_date,
        valid_end_date=valid_end_date,
        cache_dir=Path("data/cache"),
        output_dir=Path("data/datasets"),
        nan_threshold=0.2,
    )

    # 4. 构建数据集
    logger.info("开始构建数据集...")
    builder = DatasetBuilder(config)

    try:
        output_path = builder.build()
        logger.info("=" * 60)
        logger.info("✅ 数据集构建成功！")
        logger.info(f"输出目录: {output_path}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"数据集构建失败: {e}")
        raise


if __name__ == "__main__":
    main()
