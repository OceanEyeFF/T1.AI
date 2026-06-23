"""低控盘概率评分 CLI。

薄壳入口，核心逻辑在 src/ashare_lab/stock_pool/low_manipulation/strategy.py。

用法：
  python scripts/score_low_manipulation.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

UNIVERSE_EXCLUDE_PREFIXES = ("688", "300", "301", "8", "4")
INDEX_SYMBOL = "510300.SH"  # 沪深300 ETF 作为市场基准
LOOKBACK_DAYS = 60  # 滚动窗口
MIN_DATA_DAYS = 120  # 最少需要的历史数据天数

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def _load_partitioned_parquet(cache_dir: Path) -> dict[str, pd.DataFrame]:
    """加载分区 parquet 缓存。"""
    frames: dict[str, pd.DataFrame] = {}
    if not cache_dir.exists():
        return frames
    for sym_dir in sorted(cache_dir.iterdir()):
        parts = []
        for year_dir in sorted(sym_dir.iterdir()):
            if year_dir.is_dir():
                for f in year_dir.glob("*.parquet"):
                    parts.append(pd.read_parquet(f))
        if parts:
            df = pd.concat(parts).sort_values("date")
            df["date"] = pd.to_datetime(df["date"])
            frames[sym_dir.name] = df
    return frames


def load_all_data(repo_root: Path) -> dict[str, dict[str, pd.DataFrame]]:
    """加载所有缓存数据。"""
    data: dict[str, dict[str, pd.DataFrame]] = {}

    for source, dir_name in [
        ("daily_basic", "tushare_daily_basic"),
        ("qfq", "tushare_qfq"),
        ("moneyflow", "tushare_moneyflow"),
    ]:
        cache_dir = repo_root / "data" / "cache" / dir_name
        data[source] = _load_partitioned_parquet(cache_dir)

    return data


# ---------------------------------------------------------------------------
# 指标计算
# ---------------------------------------------------------------------------


@dataclass
class IndicatorResult:
    """单个股票的指标计算结果。"""

    symbol: str
    ts_code: str
    latest_date: str

    # === 规模与流动性 (Agent 2/3) ===
    circ_mv_yi: float = 0.0  # 流通市值（亿）
    total_mv_yi: float = 0.0
    free_float_ratio: float = 0.0  # circ_mv / total_mv
    avg_amount_yi: float = 0.0  # 20日均成交额（亿）
    amihud_illiq: float = 0.0  # Amihud 非流动性（越小越好）

    # === 换手率行为 (Agent 2/3/4) ===
    avg_turnover: float = 0.0  # 20日均换手率
    turnover_cv: float = 0.0  # 换手率变异系数（std/mean，越小越稳定）
    turnover_20d_min: float = 0.0
    turnover_20d_max: float = 0.0

    # === 市场同步性 (Agent 2/3) ===
    beta: float = 0.0  # 对沪深300的β
    r_squared: float = 0.0  # 价格同步性 R²
    idiosyncratic_vol: float = 0.0  # 异质波动率

    # === 极端行为 (Agent 2/3/4) ===
    limit_hit_count_60d: int = 0  # 60日涨跌停触及次数
    max_return_20d: float = 0.0  # 20日最大单日收益 (MAX)
    return_autocorr_lag1: float = 0.0  # 收益率自相关 AR(1) 绝对值

    # === 量价形态 (Agent 3) ===
    vol_price_corr: float = 0.0  # 量价相关性
    overnight_vol_ratio: float = 0.0  # 隔夜波动 / 日内波动

    # === 资金流向 (Agent 3) ===
    moneyflow_dispersion: float = 0.0  # 大单净流向离散度
    net_mf_vol_trend: float = 0.0  # 主力净流向趋势（近期均值）

    # === 综合评分 ===
    total_score: float = 0.0
    sub_scores: dict[str, float] = field(default_factory=dict)


def compute_indicators(
    df_basic: pd.DataFrame | None,
    df_qfq: pd.DataFrame | None,
    df_mf: pd.DataFrame | None,
    index_returns: pd.Series | None,
    ts_code: str,
    symbol: str,
) -> IndicatorResult | None:
    """计算单个股票的全部指标。"""
    if df_qfq is None or len(df_qfq) < MIN_DATA_DAYS:
        return None

    # 准备日收益率
    df = df_qfq.copy()
    df["return"] = df["close"].pct_change()
    df = df.dropna(subset=["return"])

    if len(df) < LOOKBACK_DAYS:
        return None

    recent = df.tail(LOOKBACK_DAYS)
    result = IndicatorResult(
        symbol=symbol,
        ts_code=ts_code,
        latest_date=str(df["date"].iloc[-1])[:10],
    )

    # ---- 规模与流动性 ----
    if df_basic is not None and len(df_basic) > 0:
        basic_recent = df_basic[df_basic["date"].isin(recent["date"])]
        if len(basic_recent) > 0:
            result.circ_mv_yi = round(basic_recent["circ_mv"].iloc[-1] / 1e4, 1)
            result.total_mv_yi = round(basic_recent["total_mv"].iloc[-1] / 1e4, 1)
            result.free_float_ratio = round(
                basic_recent["circ_mv"].iloc[-1] / max(basic_recent["total_mv"].iloc[-1], 1), 3
            )
            result.avg_turnover = round(basic_recent["turnover_rate"].mean(), 2)
            result.turnover_cv = round(
                basic_recent["turnover_rate"].std()
                / max(basic_recent["turnover_rate"].mean(), 0.001),
                3,
            )
            result.turnover_20d_min = round(basic_recent["turnover_rate"].min(), 2)
            result.turnover_20d_max = round(basic_recent["turnover_rate"].max(), 2)

    # 成交额
    if "amount" in recent.columns:
        # amount 单位是元，转亿
        result.avg_amount_yi = round(recent["amount"].mean() / 1e8, 1)

    # Amihud ILLIQ
    illiq_daily = recent["return"].abs() / (recent["amount"] / 1e8).replace(0, np.nan)
    result.amihud_illiq = round(illiq_daily.mean(), 6)

    # ---- 市场同步性 ----
    if index_returns is not None:
        aligned_ret = recent.set_index("date")["return"]
        aligned_idx = index_returns.reindex(aligned_ret.index).dropna()
        aligned_ret = aligned_ret.loc[aligned_idx.index]

        if len(aligned_ret) >= 30:
            cov_matrix = np.cov(aligned_ret.values, aligned_idx.values)
            result.beta = round(cov_matrix[0, 1] / max(cov_matrix[1, 1], 1e-10), 3)
            corr = np.corrcoef(aligned_ret.values, aligned_idx.values)[0, 1]
            result.r_squared = round(corr**2, 3)
            residuals = aligned_ret.values - result.beta * aligned_idx.values
            result.idiosyncratic_vol = round(np.std(residuals, ddof=1), 4)

    # ---- 极端行为 ----
    pre_close = df["close"].shift(1)
    limit_up = pre_close * 1.10
    limit_down = pre_close * 0.90
    hit_limit = (df["high"] >= limit_up) | (df["low"] <= limit_down)
    result.limit_hit_count_60d = int(hit_limit.tail(60).sum())

    result.max_return_20d = round(recent["return"].max(), 4)

    autocorr = recent["return"].autocorr(lag=1)
    result.return_autocorr_lag1 = round(abs(autocorr) if not pd.isna(autocorr) else 0.0, 4)

    # ---- 量价形态 ----
    vol_change = recent["volume"].diff()
    price_change = recent["close"].diff()
    valid = (vol_change.notna()) & (price_change.notna())
    if valid.sum() >= 10:
        result.vol_price_corr = round(vol_change[valid].corr(price_change[valid]), 3)

    # 隔夜/日内波动比
    overnight_ret = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
    intraday_ret = (df["close"] - df["open"]) / df["open"]
    ov_clean = overnight_ret.dropna()
    iv_clean = intraday_ret.dropna()
    if len(ov_clean) >= 30 and len(iv_clean) >= 30:
        result.overnight_vol_ratio = round(ov_clean.std() / max(iv_clean.std(), 1e-10), 3)

    # ---- 资金流向 ----
    if df_mf is not None and len(df_mf) > 0:
        mf_recent = df_mf[df_mf["date"].isin(recent["date"])]
        if len(mf_recent) > 0 and "net_mf_vol" in mf_recent.columns:
            result.net_mf_vol_trend = round(mf_recent["net_mf_vol"].mean(), 0)
            if "buy_lg_amount" in mf_recent.columns and "sell_lg_amount" in mf_recent.columns:
                lg_net = mf_recent["buy_lg_amount"] - mf_recent["sell_lg_amount"]
                result.moneyflow_dispersion = round(
                    lg_net.std() / max(mf_recent["buy_lg_amount"].mean(), 1.0), 3
                )

    return result


# ---------------------------------------------------------------------------
# 评分系统
# ---------------------------------------------------------------------------


def normalize_positive(values: list[float]) -> list[float]:
    """正向指标归一化到 [0, 100]（越大越好）。"""
    arr = np.array(values)
    vmin, vmax = np.nanmin(arr), np.nanmax(arr)
    if vmax - vmin < 1e-10:
        return [50.0] * len(values)
    return ((arr - vmin) / (vmax - vmin) * 100).tolist()


def normalize_negative(values: list[float]) -> list[float]:
    """负向指标归一化到 [0, 100]（越小越好，反转）。"""
    pos = normalize_positive(values)
    return [100.0 - p for p in pos]


def normalize_optimal_range(values: list[float], low: float, high: float) -> list[float]:
    """区间最优指标——在 [low, high] 内最好，偏离扣分。"""
    arr = np.array(values)
    scores = []
    for v in arr:
        if low <= v <= high:
            scores.append(100.0)
        elif v < low:
            scores.append(max(0.0, 100.0 - (low - v) / max(low, 0.01) * 100))
        else:
            scores.append(max(0.0, 100.0 - (v - high) / max(high, 0.01) * 100))
    return scores


def score_all(results: list[IndicatorResult]) -> list[IndicatorResult]:
    """计算所有股票的综合评分。"""
    if not results:
        return results

    # 提取各指标值
    circ_mv = [r.circ_mv_yi for r in results]
    free_float = [r.free_float_ratio for r in results]
    avg_amount = [r.avg_amount_yi for r in results]
    illiq = [r.amihud_illiq for r in results]
    turnover = [r.avg_turnover for r in results]
    turnover_cv = [r.turnover_cv for r in results]
    r2 = [r.r_squared for r in results]
    ivol = [r.idiosyncratic_vol for r in results]
    limit_hit = [r.limit_hit_count_60d for r in results]
    max_ret = [r.max_return_20d for r in results]
    ar1 = [r.return_autocorr_lag1 for r in results]
    vp_corr = [r.vol_price_corr for r in results]
    overnight = [r.overnight_vol_ratio for r in results]
    mf_disp = [r.moneyflow_dispersion for r in results]

    # 计算各维度子分

    # 维度1：规模壁垒（35% 权重 — Agent 2/3 共识的 #1 指标）
    s_circ_mv = normalize_positive(circ_mv)
    s_amount = normalize_positive(avg_amount)
    s_illiq = normalize_negative(illiq)
    s_free = normalize_positive(free_float)
    sub_scale = [
        0.40 * c + 0.25 * a + 0.20 * i + 0.15 * f
        for c, a, i, f in zip(s_circ_mv, s_amount, s_illiq, s_free)
    ]

    # 维度2：换手率健康度（20% 权重）
    s_turnover = normalize_optimal_range(turnover, 0.8, 6.0)
    s_turnover_cv = normalize_negative(turnover_cv)
    sub_turnover = [0.60 * t + 0.40 * cv for t, cv in zip(s_turnover, s_turnover_cv)]

    # 维度3：市场同步性（20% 权重 — Agent 2/3/4 共识：不能独立于大盘）
    s_r2 = normalize_positive(r2)
    s_ivol = normalize_negative(ivol)
    sub_sync = [0.50 * r + 0.50 * i for r, i in zip(s_r2, s_ivol)]

    # 维度4：极端行为（15% 权重）
    s_limit = normalize_negative([float(v) for v in limit_hit])
    s_max = normalize_negative(max_ret)
    s_ar1 = normalize_negative(ar1)
    sub_extreme = [0.40 * lim + 0.30 * mx + 0.30 * ar for lim, mx, ar in zip(s_limit, s_max, s_ar1)]

    # 维度5：量价自然度（5% 权重）
    s_vp = [80.0 if abs(c) < 0.3 else 50.0 if abs(c) < 0.5 else 20.0 for c in vp_corr]
    s_ov = normalize_optimal_range(overnight, 0.3, 1.5)
    sub_behavior = [0.50 * v + 0.50 * o for v, o in zip(s_vp, s_ov)]

    # 维度6：资金流向稳定性（5% 权重）
    s_mf = normalize_negative(mf_disp)
    sub_moneyflow = s_mf

    # 综合总分
    for i, r in enumerate(results):
        r.total_score = round(
            0.35 * sub_scale[i]
            + 0.20 * sub_turnover[i]
            + 0.20 * sub_sync[i]
            + 0.15 * sub_extreme[i]
            + 0.05 * sub_behavior[i]
            + 0.05 * sub_moneyflow[i],
            1,
        )
        r.sub_scores = {
            "规模壁垒(35%)": round(sub_scale[i], 1),
            "换手率健康(20%)": round(sub_turnover[i], 1),
            "市场同步(20%)": round(sub_sync[i], 1),
            "极端行为(15%)": round(sub_extreme[i], 1),
            "量价自然(5%)": round(sub_behavior[i], 1),
            "资金流向(5%)": round(sub_moneyflow[i], 1),
        }

    # 按总分降序
    results.sort(key=lambda r: r.total_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------


def print_table(results: list[IndicatorResult]) -> None:
    """打印评分表格。"""
    header = (
        f"{'排名':<4} {'代码':<8} {'名称':<10} {'总分':<6} "
        f"{'规模':<6} {'换手':<6} {'同步':<6} {'极端':<6} {'量价':<6} {'资金':<6} "
        f"{'流通市值':<10} {'换手率':<8} {'β':<6} {'R²':<6} {'涨跌停':<6}"
    )
    print("\n" + "=" * len(header))
    print("  综合低控盘概率评分（越高越难被操纵）")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    SYMBOL_NAMES = {
        "000001": "平安银行",
        "000333": "美的集团",
        "000858": "五粮液",
        "002594": "比亚迪",
        "600036": "招商银行",
        "600519": "贵州茅台",
        "601318": "中国平安",
        "300750": "宁德时代",
    }

    for rank, r in enumerate(results, 1):
        name = SYMBOL_NAMES.get(r.symbol, "")
        ss = r.sub_scores
        print(
            f"{rank:<4} {r.symbol:<8} {name:<10} {r.total_score:<6.1f} "
            f"{ss['规模壁垒(35%)']:<6.1f} {ss['换手率健康(20%)']:<6.1f} "
            f"{ss['市场同步(20%)']:<6.1f} {ss['极端行为(15%)']:<6.1f} "
            f"{ss['量价自然(5%)']:<6.1f} {ss['资金流向(5%)']:<6.1f} "
            f"{r.circ_mv_yi:<10.0f} {r.avg_turnover:<8.2f} "
            f"{r.beta:<6.2f} {r.r_squared:<6.3f} {r.limit_hit_count_60d:<6}"
        )

    print("-" * len(header))
    print()


def print_detail(results: list[IndicatorResult]) -> None:
    """打印每只股票的详细指标。"""
    for r in results:
        print(f"\n{'─' * 60}")
        print(f"  {r.symbol} ({r.ts_code}) — 总分: {r.total_score}")
        print(f"{'─' * 60}")
        print(
            f"  流通市值: {r.circ_mv_yi:.0f}亿  总市值: {r.total_mv_yi:.0f}亿  自由流通比: {r.free_float_ratio:.1%}"
        )
        print(f"  日均成交额: {r.avg_amount_yi:.1f}亿  Amihud ILLIQ: {r.amihud_illiq:.6f}")
        print(
            f"  换手率: avg={r.avg_turnover:.2f}%  CV={r.turnover_cv:.2f}  range=[{r.turnover_20d_min:.2f}, {r.turnover_20d_max:.2f}]"
        )
        print(f"  β={r.beta:.2f}  R²={r.r_squared:.3f}  异质波动={r.idiosyncratic_vol:.4f}")
        print(
            f"  60日涨跌停={r.limit_hit_count_60d}  MAX(20d)={r.max_return_20d:.4f}  AR(1)={r.return_autocorr_lag1:.4f}"
        )
        print(f"  量价相关={r.vol_price_corr:.3f}  隔夜/日内波动比={r.overnight_vol_ratio:.3f}")
        print(f"  大单流向离散={r.moneyflow_dispersion:.3f}  主力净量趋势={r.net_mf_vol_trend:.0f}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> int:
    from ashare_lab.stock_pool.low_manipulation.strategy import (
        _load_caches,
        _compute_indicators,
        _score_all,
        IndicatorResult as IR,
    )

    repo_root = Path(__file__).resolve().parents[1]

    print("加载缓存数据 ...")
    data = _load_caches(repo_root / "data" / "cache")

    index_df = data.get("qfq", {}).get(INDEX_SYMBOL)
    index_returns: pd.Series | None = None
    if index_df is not None:
        idx = index_df.copy()
        idx["return"] = idx["close"].pct_change()
        index_returns = idx.set_index("date")["return"].dropna()
        print(f"  基准: {INDEX_SYMBOL} ({len(index_returns)} 日)")
    else:
        print("  ⚠️ 无指数数据，使用等权均值作为代理")
        all_rets = []
        for df in data.get("qfq", {}).values():
            d = df.copy()
            d["return"] = d["close"].pct_change()
            d = d.set_index("date")["return"].dropna()
            all_rets.append(d)
        if all_rets:
            index_returns = pd.concat(all_rets, axis=1).mean(axis=1)

    qfq_data = data.get("qfq", {})
    basic_data = data.get("daily_basic", {})
    mf_data = data.get("moneyflow", {})

    results: list[IR] = []
    excluded: list[str] = []

    for ts_code in sorted(qfq_data.keys()):
        symbol = ts_code.split(".")[0]
        if symbol.startswith(UNIVERSE_EXCLUDE_PREFIXES):
            excluded.append(symbol)
            continue
        r = _compute_indicators(
            df_basic=basic_data.get(ts_code),
            df_qfq=qfq_data.get(ts_code),
            df_mf=mf_data.get(ts_code),
            index_returns=index_returns,
            ts_code=ts_code,
            symbol=symbol,
        )
        if r:
            results.append(r)

    if excluded:
        print(f"  已排除: {', '.join(excluded)}（创业板/科创板/北交所）")
    print(f"\n  计算范围: {len(results)} 只股票\n")

    results = _score_all(results)
    print_table(results)
    print_detail(results)

    scores = [r.total_score for r in results]
    print(f"\n{'─' * 40}")
    print(
        f"  评分分布: 最高={max(scores):.1f}  最低={min(scores):.1f}  均值={np.mean(scores):.1f}  中位数={np.median(scores):.1f}"
    )
    print(f"{'─' * 40}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
