"""低控盘概率选股策略。

6 维度综合评分（规模/换手/同步/极端/量价/资金），
从 universe 中筛选被操纵概率较低的股票。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_lab.stock_pool.base import PoolCandidate, StockPoolStrategy

# ---------------------------------------------------------------------------
# 可配置参数
# ---------------------------------------------------------------------------

DEFAULT_SCORE_THRESHOLD = 60.0
DEFAULT_LOOKBACK_DAYS = 60
DEFAULT_MIN_DATA_DAYS = 120
UNIVERSE_EXCLUDE_PREFIXES = ("688", "300", "301", "8", "4")
INDEX_SYMBOL = "510300.SH"

# 6 维度权重（四个 Agent 交叉共识）
DIMENSION_WEIGHTS: dict[str, float] = {
    "规模壁垒": 0.35,
    "换手率健康": 0.20,
    "市场同步": 0.20,
    "极端行为": 0.15,
    "量价自然": 0.05,
    "资金流向": 0.05,
}

# 评分阈值：换手率甜蜜区间
TURNOVER_SWEET_LOW = 0.8
TURNOVER_SWEET_HIGH = 6.0

# 量价相关性阈值
VP_CORR_GOOD = 0.3
VP_CORR_OK = 0.5

# 隔夜/日内波动比甜蜜区间
OVERNIGHT_SWEET_LOW = 0.3
OVERNIGHT_SWEET_HIGH = 1.5


# ---------------------------------------------------------------------------
# 指标结果
# ---------------------------------------------------------------------------


@dataclass
class IndicatorResult:
    """单个股票的指标计算结果。"""

    symbol: str
    ts_code: str
    latest_date: str

    circ_mv_yi: float = 0.0
    total_mv_yi: float = 0.0
    free_float_ratio: float = 0.0
    avg_amount_yi: float = 0.0
    amihud_illiq: float = 0.0

    avg_turnover: float = 0.0
    turnover_cv: float = 0.0
    turnover_20d_min: float = 0.0
    turnover_20d_max: float = 0.0

    beta: float = 0.0
    r_squared: float = 0.0
    idiosyncratic_vol: float = 0.0

    limit_hit_count_60d: int = 0
    max_return_20d: float = 0.0
    return_autocorr_lag1: float = 0.0

    vol_price_corr: float = 0.0
    overnight_vol_ratio: float = 0.0

    moneyflow_dispersion: float = 0.0
    net_mf_vol_trend: float = 0.0

    total_score: float = 0.0
    sub_scores: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def _load_partitioned_parquet(cache_dir: Path) -> dict[str, pd.DataFrame]:
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


def _load_caches(data_root: Path) -> dict[str, dict[str, pd.DataFrame]]:
    data: dict[str, dict[str, pd.DataFrame]] = {}
    for source, dir_name in [
        ("daily_basic", "tushare_daily_basic"),
        ("qfq", "tushare_qfq"),
        ("moneyflow", "tushare_moneyflow"),
    ]:
        cache_dir = data_root / dir_name
        data[source] = _load_partitioned_parquet(cache_dir)
    return data


# ---------------------------------------------------------------------------
# 指标计算
# ---------------------------------------------------------------------------


def _compute_indicators(
    df_basic: pd.DataFrame | None,
    df_qfq: pd.DataFrame | None,
    df_mf: pd.DataFrame | None,
    index_returns: pd.Series | None,
    ts_code: str,
    symbol: str,
) -> IndicatorResult | None:
    if df_qfq is None or len(df_qfq) < DEFAULT_MIN_DATA_DAYS:
        return None

    df = df_qfq.copy()
    df["return"] = df["close"].pct_change()
    df = df.dropna(subset=["return"])
    if len(df) < DEFAULT_LOOKBACK_DAYS:
        return None

    recent = df.tail(DEFAULT_LOOKBACK_DAYS)
    result = IndicatorResult(
        symbol=symbol, ts_code=ts_code, latest_date=str(df["date"].iloc[-1])[:10]
    )

    # 规模与流动性
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

    if "amount" in recent.columns:
        result.avg_amount_yi = round(recent["amount"].mean() / 1e8, 1)

    illiq_daily = recent["return"].abs() / (recent["amount"] / 1e8).replace(0, np.nan)
    result.amihud_illiq = round(illiq_daily.mean(), 6)

    # 市场同步性
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

    # 极端行为
    pre_close = df["close"].shift(1)
    hit_limit = (df["high"] >= pre_close * 1.10) | (df["low"] <= pre_close * 0.90)
    result.limit_hit_count_60d = int(hit_limit.tail(60).sum())
    result.max_return_20d = round(recent["return"].max(), 4)
    autocorr = recent["return"].autocorr(lag=1)
    result.return_autocorr_lag1 = round(abs(autocorr) if not pd.isna(autocorr) else 0.0, 4)

    # 量价形态
    vol_change = recent["volume"].diff()
    price_change = recent["close"].diff()
    valid = (vol_change.notna()) & (price_change.notna())
    if valid.sum() >= 10:
        result.vol_price_corr = round(vol_change[valid].corr(price_change[valid]), 3)

    overnight_ret = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
    intraday_ret = (df["close"] - df["open"]) / df["open"]
    ov_clean = overnight_ret.dropna()
    iv_clean = intraday_ret.dropna()
    if len(ov_clean) >= 30 and len(iv_clean) >= 30:
        result.overnight_vol_ratio = round(ov_clean.std() / max(iv_clean.std(), 1e-10), 3)

    # 资金流向
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
# 评分归一化
# ---------------------------------------------------------------------------


def _norm_positive(values: list[float]) -> list[float]:
    arr = np.array(values)
    vmin, vmax = np.nanmin(arr), np.nanmax(arr)
    if vmax - vmin < 1e-10:
        return [50.0] * len(values)
    return ((arr - vmin) / (vmax - vmin) * 100).tolist()


def _norm_negative(values: list[float]) -> list[float]:
    return [100.0 - p for p in _norm_positive(values)]


def _norm_range(values: list[float], low: float, high: float) -> list[float]:
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


# ---------------------------------------------------------------------------
# 综合评分
# ---------------------------------------------------------------------------


def _score_all(results: list[IndicatorResult]) -> list[IndicatorResult]:
    if not results:
        return results

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

    s_circ = _norm_positive(circ_mv)
    s_amt = _norm_positive(avg_amount)
    s_illiq = _norm_negative(illiq)
    s_free = _norm_positive(free_float)
    sub_scale = [
        0.40 * c + 0.25 * a + 0.20 * i + 0.15 * f
        for c, a, i, f in zip(s_circ, s_amt, s_illiq, s_free)
    ]

    s_to = _norm_range(turnover, TURNOVER_SWEET_LOW, TURNOVER_SWEET_HIGH)
    s_tocv = _norm_negative(turnover_cv)
    sub_turnover = [0.60 * t + 0.40 * cv for t, cv in zip(s_to, s_tocv)]

    s_r2 = _norm_positive(r2)
    s_ivol = _norm_negative(ivol)
    sub_sync = [0.50 * r + 0.50 * i for r, i in zip(s_r2, s_ivol)]

    s_limit = _norm_negative([float(v) for v in limit_hit])
    s_max = _norm_negative(max_ret)
    s_ar1 = _norm_negative(ar1)
    sub_extreme = [0.40 * lim + 0.30 * mx + 0.30 * ar for lim, mx, ar in zip(s_limit, s_max, s_ar1)]

    s_vp = [
        80.0 if abs(c) < VP_CORR_GOOD else 50.0 if abs(c) < VP_CORR_OK else 20.0 for c in vp_corr
    ]
    s_ov = _norm_range(overnight, OVERNIGHT_SWEET_LOW, OVERNIGHT_SWEET_HIGH)
    sub_behavior = [0.50 * v + 0.50 * o for v, o in zip(s_vp, s_ov)]

    s_mf = _norm_negative(mf_disp)
    sub_moneyflow = s_mf

    w = DIMENSION_WEIGHTS
    for i, r in enumerate(results):
        r.total_score = round(
            w["规模壁垒"] * sub_scale[i]
            + w["换手率健康"] * sub_turnover[i]
            + w["市场同步"] * sub_sync[i]
            + w["极端行为"] * sub_extreme[i]
            + w["量价自然"] * sub_behavior[i]
            + w["资金流向"] * sub_moneyflow[i],
            1,
        )
        r.sub_scores = {
            k: round(v[i], 1)
            for k, v in {
                f"规模壁垒({w['规模壁垒']:.0%})": sub_scale,
                f"换手率健康({w['换手率健康']:.0%})": sub_turnover,
                f"市场同步({w['市场同步']:.0%})": sub_sync,
                f"极端行为({w['极端行为']:.0%})": sub_extreme,
                f"量价自然({w['量价自然']:.0%})": sub_behavior,
                f"资金流向({w['资金流向']:.0%})": sub_moneyflow,
            }.items()
        }

    results.sort(key=lambda r: r.total_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# 策略类
# ---------------------------------------------------------------------------


class LowManipulationStrategy(StockPoolStrategy):
    """低控盘概率选股策略。

    从 universe 中按 6 维度综合评分筛选被操纵概率较低的股票。
    """

    def __init__(
        self,
        data_root: str | Path = "data/cache",
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> None:
        self._data_root = Path(data_root)
        self.score_threshold = score_threshold

    @property
    def name(self) -> str:
        return "low_manipulation"

    @property
    def description(self) -> str:
        return "6维度综合评分筛选低被操纵概率股票"

    def select(self, universe: list[str]) -> PoolCandidate:
        """从 universe 中按低控盘评分筛选。

        Args:
            universe: 候选股票代码列表 (bare symbols, e.g. ["600519", "000001"])

        Returns:
            PoolCandidate(symbols=入选代码, metadata=评分明细)
        """
        # 过滤 universe
        allowed = [s for s in universe if not s.startswith(UNIVERSE_EXCLUDE_PREFIXES)]
        if not allowed:
            return PoolCandidate(symbols=[], metadata={"error": "no symbols pass universe filter"})

        # 加载缓存
        caches = _load_caches(self._data_root)

        # 构建指数收益率
        index_returns: pd.Series | None = None
        idx_df = caches.get("qfq", {}).get(INDEX_SYMBOL)
        if idx_df is not None:
            idx = idx_df.copy()
            idx["return"] = idx["close"].pct_change()
            index_returns = idx.set_index("date")["return"].dropna()

        # 计算指标
        qfq_data = caches.get("qfq", {})
        basic_data = caches.get("daily_basic", {})
        mf_data = caches.get("moneyflow", {})

        results: list[IndicatorResult] = []
        for symbol in allowed:
            ts_codes = [f"{symbol}.SH", f"{symbol}.SZ"]
            for ts_code in ts_codes:
                if ts_code in qfq_data:
                    r = _compute_indicators(
                        df_basic=basic_data.get(ts_code),
                        df_qfq=qfq_data.get(ts_code),
                        df_mf=mf_data.get(ts_code),
                        index_returns=index_returns,
                        ts_code=ts_code,
                        symbol=symbol,
                    )
                    if r is not None:
                        results.append(r)
                    break

        # 评分
        results = _score_all(results)

        # 筛选
        selected = [r for r in results if r.total_score >= self.score_threshold]

        return PoolCandidate(
            symbols=[r.symbol for r in selected],
            metadata={
                "strategy": self.name,
                "score_threshold": self.score_threshold,
                "total_scored": len(results),
                "total_selected": len(selected),
                "scores": {
                    r.symbol: {
                        "total": r.total_score,
                        "sub": r.sub_scores,
                        "circ_mv_yi": r.circ_mv_yi,
                        "avg_turnover": r.avg_turnover,
                        "beta": r.beta,
                        "r_squared": r.r_squared,
                        "limit_hit_60d": r.limit_hit_count_60d,
                    }
                    for r in selected
                },
            },
        )
