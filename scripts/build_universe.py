#!/usr/bin/env python
"""构建股票池快照脚本

从 akshare 拉取全市场 A 股列表，按硬约束过滤（排除 ST/北交/科创/创业板），
并保存快照到 data/cache/universe/<date>.csv

用法：
    python scripts/build_universe.py --date 20241231
    python scripts/build_universe.py  # 使用当前日期
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 sys.path（必须在导入 ashare_lab 之前）
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import akshare as ak  # noqa: E402
import pandas as pd  # noqa: E402

from ashare_lab.universe import is_allowed_a_share_symbol  # noqa: E402


def fetch_stock_list() -> pd.DataFrame:
    """从 akshare 拉取 A 股列表

    Returns:
        DataFrame with columns: symbol, name, list_date, etc.
    """
    print("正在从 akshare 拉取 A 股列表...")
    try:
        # 获取沪深A股列表
        df = ak.stock_info_a_code_name()
        print(f"拉取成功，共 {len(df)} 只股票")
        return df
    except Exception as e:
        print(f"拉取失败: {e}")
        raise


def filter_stock_universe(df: pd.DataFrame) -> pd.DataFrame:
    """按硬约束过滤股票池

    过滤规则（与 docs/constraints.md 一致）：
    - 排除代码前缀 688*（科创板）
    - 排除代码前缀 300*/301*（创业板）
    - 排除代码前缀 8*/4*（北交所）
    - 排除名称包含 "ST" 的股票

    Args:
        df: 原始股票列表

    Returns:
        过滤后的股票列表
    """
    print("正在过滤股票池...")

    # 复制数据避免修改原始 DataFrame
    df = df.copy()

    # 确保列名一致（akshare 返回的列名可能是中文）
    # 常见列名：code/代码, name/名称
    if "code" in df.columns:
        df = df.rename(columns={"code": "symbol"})
    elif "代码" in df.columns:
        df = df.rename(columns={"代码": "symbol"})

    if "name" not in df.columns and "名称" in df.columns:
        df = df.rename(columns={"名称": "name"})

    # 过滤：排除不符合 A 股代码规则的股票
    mask_code = df["symbol"].apply(is_allowed_a_share_symbol)
    df_filtered = df[mask_code].copy()
    print(f"  - 代码过滤后剩余: {len(df_filtered)} 只（排除科创/创业/北交）")

    # 过滤：排除名称包含 "ST" 的股票
    mask_st = ~df_filtered["name"].str.contains("ST", na=False)
    df_filtered = df_filtered[mask_st].copy()
    print(f"  - ST 过滤后剩余: {len(df_filtered)} 只")

    return df_filtered


def save_universe_snapshot(df: pd.DataFrame, date_str: str) -> Path:
    """保存股票池快照

    Args:
        df: 股票池 DataFrame
        date_str: 日期字符串（YYYYMMDD）

    Returns:
        快照文件路径
    """
    # 创建输出目录
    output_dir = PROJECT_ROOT / "data" / "cache" / "universe"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存快照
    output_path = output_dir / f"{date_str}.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"快照已保存: {output_path}")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="构建股票池快照")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="日期（YYYYMMDD 格式），默认使用当前日期",
    )
    args = parser.parse_args()

    # 确定日期
    if args.date:
        date_str = args.date
        # 验证日期格式
        try:
            datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            print("错误：日期格式不正确，请使用 YYYYMMDD 格式（如 20241231）")
            sys.exit(1)
    else:
        date_str = datetime.now().strftime("%Y%m%d")

    print(f"构建股票池快照（日期: {date_str}）")
    print("=" * 60)

    # 拉取股票列表
    df_raw = fetch_stock_list()

    # 过滤股票池
    df_filtered = filter_stock_universe(df_raw)

    # 保存快照
    snapshot_path = save_universe_snapshot(df_filtered, date_str)

    print("=" * 60)
    print(f"✅ 完成！股票池快照已保存到: {snapshot_path}")
    print(f"   - 总股票数: {len(df_raw)}")
    print(f"   - 过滤后股票数: {len(df_filtered)}")
    print(f"   - 过滤比例: {len(df_filtered) / len(df_raw) * 100:.1f}%")


if __name__ == "__main__":
    main()
