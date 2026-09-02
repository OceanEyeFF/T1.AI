"""多跨度收益标签

提供多日未来收益率标签与 1 日 H/L/C 标签的统一计算与落盘工具。

支持两种标签口径：
- close_to_close: 从 t 日收盘价到 t+h 日收盘价（旧默认，兼容现有流程）
- next_open_to_open: 从 t+1 日开盘价到 t+h+1 日开盘价（与交易协议一致）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Literal

import pandas as pd

from ashare_lab.trend_schema import PRIMARY_TREND_HORIZONS, label_col_for_horizon

# 标签模式类型定义
LabelMode = Literal["close_to_close", "next_open_to_open"]


def _window_has_issue(mask: pd.Series, window: int) -> pd.Series:
    """检查 t+1 ~ t+window 内是否存在停牌/缺价。

    具体规则：
        - 停牌：volume == 0
        - 缺价：close 为 NaN
        - 行间停牌：相邻行情日断档 > MAX_NATURAL_GAP_DAYS（长假最长 ~11 自然日，
          >15 即真实停牌；TuShare 停牌日不产生行，_window_has_issue 无法感知，
          需通过 index 断档检测——4.3 审计发现）
    """
    # 先计算滚动最大值，再向前平移 window，使得 index t 对应窗口 (t+1, t+window)
    return (
        mask.rolling(window=window, min_periods=window)
        .max()
        .shift(-window)
        .astype(bool)
    )


MAX_NATURAL_GAP_DAYS = 15  # 与合同测试 2.2 的断档阈值一致（长假 ~11 天，>15=停牌）


def _suspension_gap_mask(index: pd.DatetimeIndex, window: int) -> pd.Series:
    """行间停牌掩码：窗口 (i+1, i+window) 内任一行间断档 > MAX_NATURAL_GAP_DAYS 即标记。

    返回与 index 对齐的 bool Series（t 为 True = 该行标签窗口跨真实停牌）。
    """
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2:
        return pd.Series(False, index=idx)
    gap_days = idx.to_series().diff().dt.days
    suspension = (gap_days > MAX_NATURAL_GAP_DAYS).fillna(False)
    # suspension 为 True 的位置是“断档后的第一个交易日”；
    # 向前 window 行内存在断档 → 窗口跨停牌：滚动求和后平移
    susp_int = suspension.astype(int)
    count = susp_int.rolling(window=window, min_periods=window).sum().shift(-window).fillna(0)
    # count > 0 表示从 t 到 t+window 的行间存在真实停牌断档
    return count > 0


@dataclass(frozen=True)
class MultiHorizonLabel:
    """多跨度前向收益率标签

    Args:
        horizons: 未来收益率的天数（如 3/5/10 日）
        label_mode: 标签计算基准价格模式
            - "close_to_close": label[t] = close[t+h] / close[t] - 1（旧默认）
            - "next_open_to_open": label[t] = open[t+h+1] / open[t+1] - 1（推荐）
    """

    horizons: Iterable[int] = field(default_factory=lambda: PRIMARY_TREND_HORIZONS)
    label_mode: LabelMode = "close_to_close"  # 默认保持旧行为，向后兼容

    @property
    def names(self) -> List[str]:
        return [label_col_for_horizon(h) for h in self.horizons]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算多跨度标签

        Args:
            data: 包含 close、volume 列的行情数据（next_open_to_open 模式还需要 open 列），按日期升序

        Returns:
            DataFrame，多列分别为 label_{N}d

        说明:
            - close_to_close 模式：label[t] = (close[t+h] / close[t]) - 1
            - next_open_to_open 模式：label[t] = (open[t+h+1] / open[t+1]) - 1
              对应实际交易：t 日收盘后生成信号 → t+1 日 open 买入 → t+h+1 日 open 卖出
        """
        # 检查必需列
        if "volume" not in data:
            raise KeyError("input data must contain 'volume'")

        # 根据模式选择基准价格列
        if self.label_mode == "close_to_close":
            if "close" not in data:
                raise KeyError("close_to_close mode requires 'close' column")
            price_col = "close"
            shift_offset = 0  # label[t] 对应 close[t] -> close[t+h]
        elif self.label_mode == "next_open_to_open":
            if "open" not in data:
                raise KeyError("next_open_to_open mode requires 'open' column")
            price_col = "open"
            shift_offset = 1  # label[t] 对应 open[t+1] -> open[t+h+1]
        else:
            raise ValueError(f"不支持的 label_mode: {self.label_mode}，仅支持 'close_to_close' 或 'next_open_to_open'")

        price = data[price_col]
        volume = data["volume"]

        # 标记停牌或缺价（使用对应的价格列）
        issue_mask = price.isna() | volume.isna() | (volume == 0)

        label_df = pd.DataFrame(index=data.index)

        for h in self.horizons:
            # 计算未来收益率
            # close_to_close: close[t+h] / close[t] - 1
            # next_open_to_open: open[t+h+1] / open[t+1] - 1
            future_price = price.shift(-h - shift_offset)
            current_price = price.shift(-shift_offset)
            forward_ret = future_price / current_price - 1.0

            # 停牌掩码：如果未来窗口内任何一天缺价/停牌，label 置为 NaN
            invalid = _window_has_issue(issue_mask, h + shift_offset)
            invalid = invalid | _suspension_gap_mask(data.index, h + shift_offset)
            label_df[label_col_for_horizon(h)] = forward_ret.mask(invalid)

        return label_df

    def compute_and_save(self, data: pd.DataFrame, path: str | Path) -> Path:
        """计算并保存为 Parquet。"""
        result = self.compute(data)
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(out_path)
        return out_path


@dataclass(frozen=True)
class OneDayHLCLabel:
    """1 日高/低/收收益率标签（用于日内/隔夜交易控制）。

    输出列：
        - label_1d_high
        - label_1d_low
        - label_1d_close

    口径：
        - close_to_close:
            base[t] = close[t]
            target[t] = {high, low, close}[t+1] / base[t] - 1
        - next_open_to_open:
            base[t] = open[t+1]
            target[t] = {high, low, close}[t+1] / base[t] - 1
    """

    label_mode: LabelMode = "close_to_close"

    @property
    def names(self) -> List[str]:
        return ["label_1d_high", "label_1d_low", "label_1d_close"]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"high", "low", "close", "volume"}
        missing = [c for c in sorted(required_cols) if c not in data]
        if missing:
            raise KeyError(f"input data missing required columns for 1d HLC labels: {missing}")

        high_next = data["high"].shift(-1)
        low_next = data["low"].shift(-1)
        close_next = data["close"].shift(-1)
        volume_next = data["volume"].shift(-1)

        if self.label_mode == "close_to_close":
            base = data["close"]
            base_issue = base.isna()
        elif self.label_mode == "next_open_to_open":
            if "open" not in data:
                raise KeyError("next_open_to_open mode requires 'open' column for 1d HLC labels")
            base = data["open"].shift(-1)
            base_issue = base.isna()
        else:
            raise ValueError(f"不支持的 label_mode: {self.label_mode}，仅支持 'close_to_close' 或 'next_open_to_open'")

        next_issue = (
            high_next.isna()
            | low_next.isna()
            | close_next.isna()
            | volume_next.isna()
            | (volume_next == 0)
        )
        invalid = base_issue | next_issue | _suspension_gap_mask(data.index, 1)

        out = pd.DataFrame(index=data.index)
        out["label_1d_high"] = (high_next / base - 1.0).mask(invalid)
        out["label_1d_low"] = (low_next / base - 1.0).mask(invalid)
        out["label_1d_close"] = (close_next / base - 1.0).mask(invalid)
        return out

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
