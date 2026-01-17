"""多跨度收益标签

提供 3/5/10 日未来收益率标签的统一计算与落盘工具。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

import pandas as pd


def _window_has_issue(mask: pd.Series, window: int) -> pd.Series:
    """检查 t+1 ~ t+window 内是否存在停牌/缺价。

    具体规则：
        - 停牌：volume == 0
        - 缺价：close 为 NaN
    """
    # 先计算滚动最大值，再向前平移 window，使得 index t 对应窗口 (t+1, t+window)
    return (
        mask.rolling(window=window, min_periods=window)
        .max()
        .shift(-window)
        .astype(bool)
    )


@dataclass(frozen=True)
class MultiHorizonLabel:
    """多跨度前向收益率标签"""

    horizons: Iterable[int] = field(default_factory=lambda: (3, 5, 10))

    @property
    def names(self) -> List[str]:
        return [f"label_{h}d" for h in self.horizons]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算多跨度标签

        Args:
            data: 包含 close、volume 列的行情数据，按日期升序

        Returns:
            DataFrame，多列分别为 label_{N}d
        """
        if "close" not in data:
            raise KeyError("input data must contain 'close'")
        if "volume" not in data:
            raise KeyError("input data must contain 'volume'")

        close = data["close"]
        volume = data["volume"]

        # 标记停牌或缺价
        issue_mask = close.isna() | volume.isna() | (volume == 0)

        label_df = pd.DataFrame(index=data.index)

        for h in self.horizons:
            forward_ret = close.shift(-h) / close - 1.0
            invalid = _window_has_issue(issue_mask, h)
            label_df[f"label_{h}d"] = forward_ret.mask(invalid)

        return label_df

    def compute_and_save(self, data: pd.DataFrame, path: str | Path) -> Path:
        """计算并保存为 Parquet

        Args:
            data: 行情数据
            path: 目标文件路径

        Returns:
            实际写入的 Path
        """
        result = self.compute(data)
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(out_path)
        return out_path
