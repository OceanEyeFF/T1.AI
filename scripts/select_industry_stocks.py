#!/usr/bin/env python
"""按行业分类选股脚本

根据指定的行业分类，从股票池中筛选优质股票。

用法示例：
    python scripts/select_industry_stocks.py --date 20210701 --output selected_stocks.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

try:
    import akshare as ak
except ImportError:
    print("请先安装 akshare: pip install akshare")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 行业分类与关键词映射（根据主人需求定制）
INDUSTRY_MAPPING = {
    "航天": {
        "concepts": ["大飞机", "通用航空", "商业航天", "军民融合", "卫星互联网"],
        "keywords": ["航天", "航空", "卫星", "火箭", "飞机"],
    },
    "轴承": {
        "concepts": ["工业母机", "机器人执行器", "减速器"],
        "keywords": ["轴承", "滚珠"],
    },
    "发动机": {
        "concepts": ["汽车热管理", "工业母机"],
        "keywords": ["发动机", "动力"],
    },
    "微电子": {
        "concepts": ["第四代半导体", "碳化硅", "MicroLED"],
        "keywords": ["微电子", "集成电路", "芯片"],
    },
    "芯片": {
        "concepts": ["第四代半导体", "碳化硅", "芯片概念"],
        "keywords": ["芯片", "半导体", "集成电路"],
    },
    "半导体": {
        "concepts": ["第四代半导体", "碳化硅", "TOPCon电池"],
        "keywords": ["半导体", "晶圆", "光刻"],
    },
    "医疗器具": {
        "concepts": ["医疗器械"],
        "keywords": ["医疗器械", "医疗设备", "器械"],
    },
    "医药": {
        "concepts": ["生物医药", "创新药"],
        "keywords": ["医药", "制药", "生物"],
    },
    "AI": {
        "concepts": ["智谱AI", "人形机器人", "人脑工程"],
        "keywords": ["人工智能", "AI", "算法", "深度学习"],
    },
    "数据": {
        "concepts": ["时空大数据", "数字哨兵", "大数据"],
        "keywords": ["数据", "云计算", "存储"],
    },
    "电力": {
        "concepts": ["电力", "特高压"],
        "keywords": ["电力", "供电", "电网"],
    },
    "新能源": {
        "concepts": ["换电概念", "HIT电池", "TOPCon电池", "BC电池"],
        "keywords": ["新能源", "光伏", "风电"],
    },
    "电池": {
        "concepts": ["麒麟电池", "HIT电池", "TOPCon电池", "BC电池"],
        "keywords": ["电池", "锂电"],
    },
    "锂": {
        "concepts": ["锂电池", "盐湖提锂"],
        "keywords": ["锂", "碳酸锂", "氢氧化锂"],
    },
    "铜": {
        "concepts": ["铜", "金属铜"],
        "keywords": ["铜", "铜业"],
    },
    "稀土": {
        "concepts": ["稀土永磁"],
        "keywords": ["稀土", "永磁"],
    },
    "化肥": {
        "concepts": ["化肥"],
        "keywords": ["化肥", "肥料", "磷肥", "钾肥"],
    },
    "农机": {
        "concepts": ["农机", "智慧农业"],
        "keywords": ["农机", "农业机械", "拖拉机"],
    },
    "银行": {
        "concepts": [],
        "keywords": ["银行"],
    },
    "证券": {
        "concepts": [],
        "keywords": ["证券", "券商"],
    },
}


def get_concept_stocks(concept_name: str) -> set[str]:
    """获取指定概念的成分股代码"""
    try:
        df = ak.stock_board_concept_cons_em(concept_name)
        # 确保代码格式统一为6位字符串（补齐前导零）
        codes = df["代码"].astype(str).str.zfill(6).tolist()
        return set(codes)
    except Exception as e:
        logger.warning(f"获取概念 {concept_name} 成分股失败: {e}")
        return set()


def get_all_stocks_info() -> pd.DataFrame:
    """获取所有股票的基本信息（包括市值、换手率等）"""
    try:
        df = ak.stock_zh_a_spot_em()
        # 重命名列以便于使用
        df = df.rename(
            columns={
                "代码": "code",
                "名称": "name",
                "最新价": "price",
                "总市值": "total_market_value",
                "流通市值": "circulating_market_value",
                "换手率": "turnover_rate",
                "市盈率-动态": "pe_ratio",
                "市净率": "pb_ratio",
            }
        )
        # 确保 code 列为6位字符串格式
        df["code"] = df["code"].astype(str).str.zfill(6)
        return df
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        return pd.DataFrame()


def filter_stocks_by_industry(
    universe_df: pd.DataFrame,
    all_stocks_df: pd.DataFrame,
    industry_name: str,
    industry_config: dict,
    top_n: int = 5,
) -> list[str]:
    """根据行业配置筛选优质股票

    Args:
        universe_df: 股票池DataFrame（符合基本过滤条件的股票）
        all_stocks_df: 所有股票的详细信息
        industry_name: 行业名称
        industry_config: 行业配置（concepts和keywords）
        top_n: 每个行业选择的股票数量

    Returns:
        选中的股票代码列表
    """
    logger.info(f"开始筛选行业: {industry_name}")

    candidate_codes = set()

    # 1. 通过概念板块匹配
    for concept in industry_config["concepts"]:
        concept_stocks = get_concept_stocks(concept)
        candidate_codes.update(concept_stocks)
        logger.info(f"  - 概念 {concept}: {len(concept_stocks)} 只股票")

    # 2. 通过名称关键词匹配
    for keyword in industry_config["keywords"]:
        matched = universe_df[universe_df["name"].str.contains(keyword, na=False)]
        keyword_codes = set(matched["symbol"].tolist())
        candidate_codes.update(keyword_codes)
        logger.info(f"  - 关键词 '{keyword}': {len(keyword_codes)} 只股票")

    # 3. 与股票池交集（确保符合基本过滤条件）
    valid_codes = set(universe_df["symbol"].tolist())
    candidate_codes = candidate_codes & valid_codes

    if not candidate_codes:
        logger.warning(f"  ⚠️ 行业 {industry_name} 未找到候选股票")
        return []

    logger.info(f"  - 候选股票总数: {len(candidate_codes)}")

    # 4. 获取候选股票的详细信息
    candidates_df = all_stocks_df[all_stocks_df["code"].isin(candidate_codes)].copy()

    if candidates_df.empty:
        logger.warning(f"  ⚠️ 行业 {industry_name} 候选股票信息为空")
        return []

    # 5. 基本面筛选与排序
    # 剔除市值过小的股票（小于50亿）
    candidates_df = candidates_df[candidates_df["circulating_market_value"] > 5e9].copy()

    if candidates_df.empty:
        logger.warning(f"  ⚠️ 行业 {industry_name} 市值筛选后无候选股票")
        return []

    # 按流通市值排序（优先选择大市值股票，流动性好）
    candidates_df = candidates_df.sort_values("circulating_market_value", ascending=False)

    # 选择前N只
    selected_codes = candidates_df.head(top_n)["code"].tolist()

    logger.info(f"  ✅ 行业 {industry_name} 选中 {len(selected_codes)} 只股票:")
    for _, row in candidates_df.head(top_n).iterrows():
        logger.info(
            f"    - {row['code']} {row['name']}: 市值 {row['circulating_market_value'] / 1e8:.2f}亿"
        )

    return selected_codes


def main() -> None:
    parser = argparse.ArgumentParser(description="按行业分类选股")
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="股票池快照日期（YYYYMMDD）",
    )
    parser.add_argument(
        "--stocks-per-industry",
        type=int,
        default=5,
        help="每个行业选择的股票数量（默认5）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="selected_stocks.csv",
        help="输出文件名（默认 selected_stocks.csv）",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("按行业分类选股")
    logger.info("=" * 60)

    # 1. 加载股票池快照
    universe_path = Path(f"data/cache/universe/{args.date}.csv")
    if not universe_path.exists():
        logger.error(f"股票池快照不存在: {universe_path}")
        logger.info(f"请先运行: python scripts/build_universe.py --date {args.date}")
        return

    universe_df = pd.read_csv(universe_path)
    # 确保 symbol 列为6位字符串格式
    universe_df["symbol"] = universe_df["symbol"].astype(str).str.zfill(6)
    logger.info(f"加载股票池快照: {len(universe_df)} 只股票")

    # 2. 获取所有股票的详细信息
    logger.info("正在获取股票详细信息...")
    all_stocks_df = get_all_stocks_info()

    if all_stocks_df.empty:
        logger.error("无法获取股票信息，退出")
        return

    logger.info(f"获取到 {len(all_stocks_df)} 只股票的信息")

    # 3. 按行业筛选股票
    selected_stocks = []

    for industry_name, industry_config in INDUSTRY_MAPPING.items():
        codes = filter_stocks_by_industry(
            universe_df,
            all_stocks_df,
            industry_name,
            industry_config,
            top_n=args.stocks_per_industry,
        )

        for code in codes:
            stock_info = all_stocks_df[all_stocks_df["code"] == code]
            if not stock_info.empty:
                selected_stocks.append(
                    {
                        "industry": industry_name,
                        "code": code,
                        "name": stock_info.iloc[0]["name"],
                        "market_value": stock_info.iloc[0]["circulating_market_value"],
                    }
                )

    # 4. 保存结果
    result_df = pd.DataFrame(selected_stocks)

    output_path = Path(args.output)
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    logger.info("=" * 60)
    logger.info("✅ 选股完成！")
    logger.info(f"输出文件: {output_path}")
    logger.info(f"总股票数: {len(result_df)}")
    logger.info(f"行业数: {result_df['industry'].nunique()}")
    logger.info("=" * 60)

    # 打印统计
    logger.info("\\n行业分布:")
    for industry in INDUSTRY_MAPPING.keys():
        count = len(result_df[result_df["industry"] == industry])
        logger.info(f"  {industry}: {count} 只")


if __name__ == "__main__":
    main()
