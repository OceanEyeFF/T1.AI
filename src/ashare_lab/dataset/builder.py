"""数据集构建器

负责加载数据、计算特征、生成标签、切分数据集。
取数统一经 ``ashare_infra.lake.DataLake``（WT-INFRA-002）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
import yaml

from ashare_infra.lake import DataLake
from ashare_infra.lake.r4_contract import R4_ADJUST_DEFAULT, make_r4_datalake
from ashare_lab.features.base import BaseFeature
from ashare_lab.labels.excess_return import ExcessReturnLabel, ForwardReturnLabel
from ashare_lab.symbols import symbol_to_odp_equity_symbol, symbol_to_ts_code

logger = logging.getLogger(__name__)

SourceKind = Literal["akshare", "tushare", "odp"]


@dataclass
class DatasetConfig:
    """数据集配置"""

    name: str
    symbols: list[str]
    start_date: str  # YYYYMMDD
    end_date: str  # YYYYMMDD
    features: list[BaseFeature]
    label_type: str = "excess_return"  # 'excess_return' or 'forward_return'
    benchmark_code: str = "000300"  # 沪深300
    split_method: str = "fixed_window"  # 'fixed_window' or 'rolling_window'
    train_end_date: str | None = None  # YYYYMMDD
    valid_end_date: str | None = None  # YYYYMMDD
    source: SourceKind = "tushare"  # R4/A1 primary; override for akshare/odp
    cache_dir: Path = field(default_factory=lambda: Path("inputs/data/cache"))
    output_dir: Path = field(default_factory=lambda: Path("workspace/datasets"))
    nan_threshold: float = 0.2  # 缺失数据阈值（超过警告）


class DatasetBuilder:
    """数据集构建器

    负责构建用于模型训练的数据集：
    1. 加载股票和基准数据
    2. 计算特征和标签
    3. 数据质量检查
    4. Walk-forward 切分
    5. 保存到 Parquet 文件
    """

    def __init__(self, config: DatasetConfig):
        self.config = config
        self.stock_data: dict[str, pd.DataFrame] = {}
        self.benchmark_data: pd.DataFrame | None = None
        self.dataset: pd.DataFrame | None = None
        if config.source == "tushare":
            self._lake = make_r4_datalake(cache_dir=config.cache_dir)
        else:
            self._lake = DataLake(
                cache_dir=config.cache_dir,
                default_source=config.source,  # type: ignore[arg-type]
            )

    def build(self) -> Path:
        """构建完整数据集

        Returns:
            输出目录路径
        """
        logger.info(f"开始构建数据集: {self.config.name}")

        # 1. 加载数据
        self._load_stock_data()
        self._load_benchmark_data()

        # 2. 计算特征和标签
        self._compute_features_and_labels()

        # 3. 数据质量检查
        self._quality_check()

        # 4. 切分数据集
        train_df, valid_df, test_df = self._split_data()

        # 5. 保存数据集
        output_path = self._save_dataset(train_df, valid_df, test_df)

        logger.info(f"数据集构建完成: {output_path}")
        return output_path

    def _load_stock_data(self) -> None:
        """加载所有股票的行情数据"""
        logger.info(f"加载 {len(self.config.symbols)} 只股票数据...")
        source = self.config.source
        if source not in ("akshare", "tushare", "odp"):
            raise ValueError(f"不支持的数据源: {source}")

        for symbol in self.config.symbols:
            try:
                lake_symbol = self._resolve_lake_symbol(symbol, source)
                df = self._lake.load_daily_bars(
                    lake_symbol,
                    self.config.start_date,
                    self.config.end_date,
                    source=source,
                    adjust=R4_ADJUST_DEFAULT,
                )
                if df.empty:
                    logger.warning(f"股票 {symbol} 数据为空，跳过")
                    continue

                self.stock_data[symbol] = df
            except Exception as e:
                logger.error(f"加载股票 {symbol} 数据失败: {e}")

        logger.info(f"成功加载 {len(self.stock_data)} 只股票数据")

    def _resolve_lake_symbol(self, symbol: str, source: SourceKind) -> str:
        if source == "tushare":
            return symbol_to_ts_code(symbol)
        if source == "odp":
            return symbol_to_odp_equity_symbol(symbol)
        return symbol

    def _load_benchmark_data(self) -> None:
        """加载基准数据（沪深300）"""
        if self.config.label_type != "excess_return":
            logger.info("标签类型非超额收益，跳过基准数据加载")
            return

        logger.info(f"加载基准数据: {self.config.benchmark_code}")

        try:
            self.benchmark_data = self._lake.load_index_daily(
                self.config.benchmark_code,
                self.config.start_date,
                self.config.end_date,
            )
            logger.info(f"基准数据加载完成，共 {len(self.benchmark_data)} 条记录")
        except Exception as e:
            logger.error(f"加载基准数据失败: {e}")
            raise

    def _compute_features_and_labels(self) -> None:
        """计算所有股票的特征和标签"""
        logger.info("计算特征和标签...")

        # 检查是否有有效的股票数据
        if not self.stock_data:
            raise ValueError("数据集为空：没有加载到任何股票数据")

        all_rows = []

        for symbol, stock_df in self.stock_data.items():
            # 计算特征
            feature_dict = {}
            for feature in self.config.features:
                try:
                    feature_series = feature.compute(stock_df)
                    feature_dict[feature.name] = feature_series
                except Exception as e:
                    logger.error(f"计算特征 {feature.name} 失败 (股票 {symbol}): {e}")
                    # 填充 NaN
                    feature_dict[feature.name] = pd.Series(index=stock_df.index, dtype=float)

            # 计算标签
            if self.config.label_type == "excess_return":
                label_computer = ExcessReturnLabel()
                label_series = label_computer.compute(stock_df, self.benchmark_data)
            else:  # forward_return
                label_computer = ForwardReturnLabel()
                label_series = label_computer.compute(stock_df)

            # 组装单只股票的数据
            stock_features = pd.DataFrame(feature_dict, index=stock_df.index)
            stock_features["symbol"] = symbol
            stock_features["label"] = label_series

            # 添加原始价格列（用于后续分析）
            stock_features["close"] = stock_df["close"]

            # 重置索引，将 date 变成列
            if stock_features.index.name is None:
                stock_features.index.name = "date"
            stock_features = stock_features.reset_index()

            all_rows.append(stock_features)

        # 合并所有股票数据
        self.dataset = pd.concat(all_rows, ignore_index=True)

        # 按日期和股票代码排序
        self.dataset = self.dataset.sort_values(["date", "symbol"]).reset_index(drop=True)

        logger.info(f"特征和标签计算完成，共 {len(self.dataset)} 条记录")

    def _quality_check(self) -> None:
        """数据质量检查"""
        logger.info("执行数据质量检查...")

        if self.dataset is None or self.dataset.empty:
            raise ValueError("数据集为空，无法进行质量检查")

        # 统计 NaN 比例
        feature_cols = [f.name for f in self.config.features] + ["label"]
        nan_ratios = self.dataset[feature_cols].isna().mean()

        # 检查是否有列超过阈值
        high_nan_cols = nan_ratios[nan_ratios > self.config.nan_threshold]
        if not high_nan_cols.empty:
            logger.warning(f"以下列的 NaN 比例超过 {self.config.nan_threshold}:")
            for col, ratio in high_nan_cols.items():
                logger.warning(f"  {col}: {ratio:.2%}")

        # 统计每只股票的数据量
        symbol_counts = self.dataset.groupby("symbol").size()
        logger.info(f"每只股票平均数据量: {symbol_counts.mean():.0f} 条")

        # 统计总体 NaN 比例
        total_nan_ratio = self.dataset[feature_cols].isna().mean().mean()
        logger.info(f"整体 NaN 比例: {total_nan_ratio:.2%}")

    def _split_data(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """切分数据集（固定窗口）

        Returns:
            (train_df, valid_df, test_df)
        """
        logger.info("切分数据集...")

        if self.dataset is None:
            raise ValueError("数据集未计算，无法切分")

        # 转换日期格式
        train_end = pd.to_datetime(self.config.train_end_date, format="%Y%m%d")
        valid_end = pd.to_datetime(self.config.valid_end_date, format="%Y%m%d")

        # 按日期切分
        train_df = self.dataset[self.dataset["date"] <= train_end].copy()
        valid_df = self.dataset[
            (self.dataset["date"] > train_end) & (self.dataset["date"] <= valid_end)
        ].copy()
        test_df = self.dataset[self.dataset["date"] > valid_end].copy()

        logger.info(f"训练集: {len(train_df)} 条记录")
        logger.info(f"验证集: {len(valid_df)} 条记录")
        logger.info(f"测试集: {len(test_df)} 条记录")

        return train_df, valid_df, test_df

    def _save_dataset(
        self,
        train_df: pd.DataFrame,
        valid_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Path:
        """保存数据集到 Parquet 文件"""
        # 创建输出目录
        output_dir = self.config.output_dir / self.config.name
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存数据文件
        train_df.to_parquet(output_dir / "train.parquet", index=False)
        valid_df.to_parquet(output_dir / "valid.parquet", index=False)
        test_df.to_parquet(output_dir / "test.parquet", index=False)

        # 生成元数据
        metadata = self._generate_metadata(train_df, valid_df, test_df)

        # 保存元数据
        with open(output_dir / "metadata.yaml", "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)

        return output_dir

    def _generate_metadata(
        self,
        train_df: pd.DataFrame,
        valid_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> dict:
        """生成数据集元数据"""
        feature_cols = [f.name for f in self.config.features]

        metadata = {
            "name": self.config.name,
            "created_at": datetime.now().isoformat(),
            "description": f"特征: {', '.join(feature_cols)}; 标签: {self.config.label_type}",
            "date_range": {
                "start": self.config.start_date,
                "end": self.config.end_date,
            },
            "universe": {
                "total_symbols": len(self.config.symbols),
                "symbols": self.config.symbols,
            },
            "features": [
                {"name": f.name, "type": f.__class__.__name__} for f in self.config.features
            ],
            "label": {
                "name": self.config.label_type,
                "type": "regression",
                "description": "次日相对基准的超额收益"
                if self.config.label_type == "excess_return"
                else "次日绝对收益率",
            },
            "split": {
                "method": self.config.split_method,
                "train_end": self.config.train_end_date,
                "valid_end": self.config.valid_end_date,
            },
            "statistics": {
                "train_samples": len(train_df),
                "valid_samples": len(valid_df),
                "test_samples": len(test_df),
                "total_samples": len(train_df) + len(valid_df) + len(test_df),
                "nan_ratio": float(self.dataset[feature_cols + ["label"]].isna().mean().mean()),
            },
        }

        return metadata
