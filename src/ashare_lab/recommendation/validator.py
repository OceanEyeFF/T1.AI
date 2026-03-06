"""推荐结果验证器（Phase 2）

本模块目标：
- 通过"数据源适配器 + 交易日历注入"实现与外部数据源解耦；
- 使用沪深300（HS300）指数日线的日期作为交易日历；
- 对停牌/缺价等情况用 NaN 掩码处理，并复用 evaluation.metrics 的 IC/RankIC 计算；
- 输出命中率、IC、RankIC、超额收益等核心指标。

支持两种收益计算口径：
- close_to_close: 从推荐日 close 到验证日 close（旧默认，兼容现有流程）
- next_open_to_open: 从推荐日次日 open 到验证日次日 open（与交易协议一致）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    import pandas as pd


_REQUIRED_DAILY_COLS: tuple[str, ...] = ("open", "high", "low", "close", "volume", "amount")

# 收益模式类型定义
ReturnMode = Literal["close_to_close", "next_open_to_open"]


class DailyBarsSource(Protocol):
    """日线行情数据源抽象层。

    约定：返回一个 dict，key 为输入的股票代码（通常为 6 位数字），value 为符合
    docs/data_contract.md 的日线 DataFrame（索引为 date，升序）。
    """

    def fetch_daily_bars(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, pd.DataFrame]:
        """批量获取日线数据（区间闭合）。"""


class TradingCalendarSource(Protocol):
    """交易日历源（基于 HS300 指数日线）。"""

    def fetch_hs300_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取 HS300 日线（日历以其日期为准）。"""


def _to_yyyymmdd(date_str: str) -> str:
    """兼容 YYYY-MM-DD / YYYYMMDD 两种输入，统一转为 YYYYMMDD。"""
    import pandas as pd

    s = str(date_str).strip()
    if not s:
        raise ValueError("日期不能为空")
    if "-" in s:
        ts = pd.to_datetime(s)
        return ts.strftime("%Y%m%d")
    if len(s) == 8 and s.isdigit():
        return s
    raise ValueError(f"不支持的日期格式: {date_str}")


def _ensure_daily_schema(df: pd.DataFrame) -> pd.DataFrame:
    """确保日线数据满足内部 schema（缺失列用 NaN 补齐）。"""
    import numpy as np
    import pandas as pd

    if df is None or df.empty:
        out = pd.DataFrame(columns=list(_REQUIRED_DAILY_COLS))
        out.index.name = "date"
        return out

    out = df.copy()
    if out.index.name != "date":
        out.index.name = "date"

    for col in _REQUIRED_DAILY_COLS:
        if col not in out.columns:
            out[col] = np.nan

    out = out[list(_REQUIRED_DAILY_COLS)].copy()
    for col in _REQUIRED_DAILY_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.sort_index()
    return out


def _symbol_to_ts_code(symbol: str) -> str:
    """将 6 位数字股票代码转换为 TuShare 的 ts_code（如 600519.SH）。"""
    s = str(symbol).strip().upper()
    if not s:
        raise ValueError("symbol 不能为空")
    if "." in s:
        return s
    if len(s) != 6 or not s.isdigit():
        raise ValueError(f"不支持的股票代码格式: {symbol}")

    if s.startswith("6"):
        suffix = "SH"
    elif s.startswith(("0", "3")):
        suffix = "SZ"
    elif s.startswith(("8", "4")):
        suffix = "BJ"
    else:
        raise ValueError(f"无法识别交易所后缀: {symbol}")
    return f"{s}.{suffix}"


class AkshareSourceAdapter:
    """AkShare 数据源适配器。"""

    def __init__(
        self,
        cache_dir: Path | None = None,
        adjust: str = "qfq",
        refresh: bool = False,
    ) -> None:
        self.cache_dir = cache_dir or Path("data/cache")
        self.adjust = adjust
        self.refresh = refresh

    def fetch_daily_bars(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, pd.DataFrame]:
        from ashare_lab.data.akshare_source import AkshareDailyBarsRequest
        from ashare_lab.data.akshare_source import (
            load_or_fetch_daily_bars as load_or_fetch_akshare_daily_bars,
        )

        start = _to_yyyymmdd(start_date)
        end = _to_yyyymmdd(end_date)

        out: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            sym = str(symbol)
            req = AkshareDailyBarsRequest(symbol=sym, start_date=start, end_date=end, adjust=self.adjust)
            df = load_or_fetch_akshare_daily_bars(req, self.cache_dir, refresh=self.refresh)
            out[sym] = _ensure_daily_schema(df)
        return out


class TushareSourceAdapter:
    """TuShare 数据源适配器（自动处理 symbol → ts_code）。"""

    def __init__(
        self,
        cache_dir: Path | None = None,
        adjust: str = "qfq",
        refresh: bool = False,
        token: str | None = None,
    ) -> None:
        self.cache_dir = cache_dir or Path("data/cache")
        self.adjust = adjust
        self.refresh = refresh
        self.token = token

    def fetch_daily_bars(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, pd.DataFrame]:
        from ashare_lab.data.tushare_source import TushareDailyBarsRequest
        from ashare_lab.data.tushare_source import (
            load_or_fetch_daily_bars as load_or_fetch_tushare_daily_bars,
        )

        start = _to_yyyymmdd(start_date)
        end = _to_yyyymmdd(end_date)

        out: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            sym = str(symbol)
            ts_code = _symbol_to_ts_code(sym)
            req = TushareDailyBarsRequest(
                symbol=ts_code,
                start_date=start,
                end_date=end,
                adjust=self.adjust,
                token=self.token,
            )
            df = load_or_fetch_tushare_daily_bars(req, self.cache_dir, refresh=self.refresh)
            out[sym] = _ensure_daily_schema(df)
        return out


class HS300IndexCalendarSource:
    """基于 HS300（000300）指数日线的交易日历源。"""

    def __init__(self, cache_dir: Path | None = None, refresh: bool = False) -> None:
        self.cache_dir = cache_dir or Path("data/cache")
        self.refresh = refresh

    def fetch_hs300_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        import numpy as np
        import pandas as pd

        from ashare_lab.data.index_source import AkshareIndexDailyRequest
        from ashare_lab.data.index_source import load_or_fetch_index_daily

        req = AkshareIndexDailyRequest(
            symbol="000300",
            start_date=_to_yyyymmdd(start_date),
            end_date=_to_yyyymmdd(end_date),
        )
        df = load_or_fetch_index_daily(req, self.cache_dir, refresh=self.refresh)
        if df is None or df.empty:
            out = pd.DataFrame(columns=list(_REQUIRED_DAILY_COLS))
            out.index.name = "date"
            return out
        # 指数日线与股票日线保持一致字段集合，便于统一计算收益
        return _ensure_daily_schema(df)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """推荐验证结果（单一 horizon）。

    Args:
        hit_rate: 方向命中率
        ic: 信息系数（Pearson）
        rank_ic: 秩信息系数（Spearman）
        excess_return: 超额收益（相对基准）
        valid_count: 有效样本数
        validation_date: 验证日期（YYYY-MM-DD）
        return_mode: 实际收益计算模式
        label_mode: 对应的标签模式（从元数据读取，可选）
    """

    hit_rate: float
    ic: float
    rank_ic: float
    excess_return: float
    valid_count: int
    validation_date: str  # YYYY-MM-DD
    return_mode: ReturnMode = "close_to_close"  # 新增：协议记录
    label_mode: str | None = None  # 新增：从元数据读取（可选）


def _extract_symbol_and_score(item: Any) -> tuple[str, float]:
    """从 Recommendation 或 dict 中提取 symbol 与 score。"""
    if hasattr(item, "symbol"):
        symbol = str(getattr(item, "symbol"))
        if hasattr(item, "predicted_return"):
            score = float(getattr(item, "predicted_return"))
        elif hasattr(item, "score"):
            score = float(getattr(item, "score"))
        else:
            raise ValueError("推荐对象缺少 predicted_return/score 字段")
        return symbol, score

    if isinstance(item, Mapping):
        if "symbol" not in item:
            raise ValueError("推荐 dict 缺少 symbol 字段")
        symbol = str(item["symbol"])
        if "predicted_return" in item:
            score = float(item["predicted_return"])
        elif "score" in item:
            score = float(item["score"])
        else:
            raise ValueError("推荐 dict 缺少 predicted_return/score 字段")
        return symbol, score

    raise ValueError(f"不支持的推荐对象类型: {type(item)!r}")


def _parse_recommendations_payload(
    recommendations: Any,
    validation_horizon: int,
    recommendation_date: str | None,
) -> tuple[list[Any], str]:
    """兼容多种输入格式，解析出（推荐列表, 推荐日期）。"""
    date = recommendation_date
    items: Any = recommendations

    if isinstance(recommendations, Mapping):
        if date is None:
            for key in ("recommendation_date", "rec_date", "date"):
                if key in recommendations and recommendations[key]:
                    date = str(recommendations[key])
                    break
        # 优先支持形如 {"date": "...", "recommendations": [...]} 的结构
        if "recommendations" in recommendations:
            items = recommendations["recommendations"]
        else:
            # 兼容 engine.save_as_json 的结构（"3d"/"5d"/"10d"）
            key = f"{int(validation_horizon)}d"
            if key in recommendations:
                items = recommendations[key]
            elif "items" in recommendations:
                items = recommendations["items"]
            elif "recs" in recommendations:
                items = recommendations["recs"]

    if date is None:
        raise ValueError("缺少 recommendation_date（可通过参数传入或在 payload 中提供 date 字段）")

    if items is None:
        return [], date

    if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
        return list(items), date

    # 单条推荐的 dict 也允许
    return [items], date


def _get_close_on(df: pd.DataFrame, date: pd.Timestamp) -> float | None:
    """从日线中取某日收盘价（缺失返回 None）。"""
    import pandas as pd

    if df is None or df.empty:
        return None
    if "close" not in df.columns:
        return None
    try:
        value = df.loc[date, "close"]
    except KeyError:
        return None
    if pd.isna(value):
        return None
    return float(value)


def _get_open_on(df: pd.DataFrame, date: pd.Timestamp) -> float | None:
    """从日线中取某日开盘价（缺失返回 None）。"""
    import pandas as pd

    if df is None or df.empty:
        return None
    if "open" not in df.columns:
        return None
    try:
        value = df.loc[date, "open"]
    except KeyError:
        return None
    if pd.isna(value):
        return None
    return float(value)


class RecommendationValidator:
    """推荐验证器（单一 horizon 版本）。"""

    def __init__(self, data_source: DailyBarsSource, calendar_source: TradingCalendarSource | None = None):
        if data_source is None:
            raise ValueError("data_source 不能为空")
        self.data_source = data_source
        self.calendar_source = calendar_source or HS300IndexCalendarSource()

    def validate(
        self,
        recommendations: Any,
        validation_horizon: int = 5,
        recommendation_date: str | None = None,
        return_mode: ReturnMode = "close_to_close",
        label_mode: str | None = None,
    ) -> ValidationResult:
        """验证推荐准确性。

        Args:
            recommendations: 推荐列表（Recommendation 或 dict），也支持包含 date 字段的 payload。
            validation_horizon: 验证持有期（交易日数量），默认 5。
            recommendation_date: 推荐日期（YYYY-MM-DD 或 YYYYMMDD），可选。
            return_mode: 实际收益计算模式
                - "close_to_close": 从推荐日 close 到验证日 close（旧默认）
                - "next_open_to_open": 从推荐日次日 open 到验证日次日 open（推荐）
            label_mode: 对应的标签模式（可选，用于元数据记录）

        Returns:
            ValidationResult
        """
        if validation_horizon <= 0:
            raise ValueError("validation_horizon 必须为正整数")

        import numpy as np
        import pandas as pd

        from ashare_lab.evaluation import metrics

        raw_items, rec_date_str = _parse_recommendations_payload(
            recommendations, validation_horizon=validation_horizon, recommendation_date=recommendation_date
        )

        rec_ts = pd.to_datetime(rec_date_str).normalize()
        validation_ts, hs300_df, trade_dates = self._resolve_validation_date(rec_ts, validation_horizon)

        start_trade_date: pd.Timestamp | None = None
        end_trade_date: pd.Timestamp | None = None
        if return_mode == "next_open_to_open":
            rec_idx = int(trade_dates.get_loc(rec_ts))
            if rec_idx + 1 < len(trade_dates):
                start_trade_date = pd.Timestamp(trade_dates[rec_idx + 1]).normalize()

            val_idx = int(trade_dates.get_loc(validation_ts))
            if val_idx + 1 < len(trade_dates):
                end_trade_date = pd.Timestamp(trade_dates[val_idx + 1]).normalize()

        # 解析推荐（按 symbol 去重，保留第一条）
        symbol_to_score: dict[str, float] = {}
        for item in raw_items:
            symbol, score = _extract_symbol_and_score(item)
            if symbol not in symbol_to_score:
                symbol_to_score[symbol] = score

        symbols = list(symbol_to_score.keys())
        if not symbols:
            return ValidationResult(
                hit_rate=0.0,
                ic=0.0,
                rank_ic=0.0,
                excess_return=0.0,
                valid_count=0,
                validation_date=validation_ts.strftime("%Y-%m-%d"),
                return_mode=return_mode,
                label_mode=label_mode,
            )

        # 根据 return_mode 确定需要获取的日期范围
        if return_mode == "next_open_to_open" and end_trade_date is not None:
            fetch_end = end_trade_date.strftime("%Y-%m-%d")
        else:
            fetch_end = validation_ts.strftime("%Y-%m-%d")

        bars_by_symbol = self.data_source.fetch_daily_bars(
            symbols=symbols,
            start_date=rec_ts.strftime("%Y-%m-%d"),
            end_date=fetch_end,
        )

        realized_returns: list[float] = []
        scores: list[float] = []

        # 计算实际收益（根据 return_mode）
        for symbol in symbols:
            df = _ensure_daily_schema(bars_by_symbol.get(symbol, pd.DataFrame()))

            if return_mode == "close_to_close":
                # 旧模式：从推荐日 close 到验证日 close
                start_price = _get_close_on(df, rec_ts)
                end_price = _get_close_on(df, validation_ts)
            else:  # next_open_to_open
                # 新模式：严格使用统一交易日历上的“推荐日后1交易日”与“验证日后1交易日”
                start_price = _get_open_on(df, start_trade_date) if start_trade_date is not None else None
                end_price = _get_open_on(df, end_trade_date) if end_trade_date is not None else None

            # 计算收益率
            if start_price is None or end_price is None or start_price == 0:
                realized_returns.append(np.nan)
            else:
                realized_returns.append(end_price / start_price - 1.0)

            scores.append(float(symbol_to_score[symbol]))

        realized_np = np.asarray(realized_returns, dtype=float)
        scores_np = np.asarray(scores, dtype=float)

        valid_mask = np.isfinite(realized_np) & np.isfinite(scores_np)
        valid_count = int(valid_mask.sum())

        if valid_count == 0:
            hit_rate = 0.0
        else:
            pred_dir = np.sign(scores_np[valid_mask])
            real_dir = np.sign(realized_np[valid_mask])
            hit_rate = float(np.mean(pred_dir == real_dir))

        ic = float(metrics.information_coefficient(scores_np, realized_np))
        rank_ic = float(metrics.rank_information_coefficient(scores_np, realized_np))

        benchmark_return = self._benchmark_return_by_mode(hs300_df, rec_ts, validation_ts, return_mode)
        if valid_count == 0:
            excess_return = 0.0
        else:
            portfolio_return = float(np.nanmean(realized_np))
            excess_return = float(portfolio_return - benchmark_return)

        return ValidationResult(
            hit_rate=hit_rate,
            ic=ic,
            rank_ic=rank_ic,
            excess_return=excess_return,
            valid_count=valid_count,
            validation_date=validation_ts.strftime("%Y-%m-%d"),
            return_mode=return_mode,
            label_mode=label_mode,
        )

    def _resolve_validation_date(
        self, rec_ts: pd.Timestamp, validation_horizon: int
    ) -> tuple[pd.Timestamp, pd.DataFrame, pd.DatetimeIndex]:
        """基于 HS300 交易日历，获取推荐日后 N 个交易日对应的验证日期与交易日索引。"""
        import pandas as pd

        # 为了跨周末/节假日鲁棒，先给一个足够的缓冲区；不足时再扩大
        buffer_days = max(30, validation_horizon * 10)
        for _ in range(3):
            start = rec_ts - timedelta(days=5)
            end = rec_ts + timedelta(days=buffer_days)
            hs300_df = self.calendar_source.fetch_hs300_daily(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            hs300_df = _ensure_daily_schema(hs300_df)
            trade_dates = pd.DatetimeIndex(hs300_df.index).normalize().sort_values()
            if trade_dates.empty:
                raise ValueError("HS300 交易日历为空，无法进行验证")

            if rec_ts not in trade_dates:
                raise ValueError(f"推荐日期不在交易日历中: {rec_ts.strftime('%Y-%m-%d')}")

            start_idx = int(trade_dates.get_loc(rec_ts))
            end_idx = start_idx + int(validation_horizon)
            if end_idx < len(trade_dates):
                return pd.Timestamp(trade_dates[end_idx]).normalize(), hs300_df, trade_dates

            buffer_days *= 2

        raise ValueError("无法在交易日历中定位验证日期（可能是数据区间不足）")

    def _next_trade_day(self, trade_dates: pd.DatetimeIndex, current_day: pd.Timestamp) -> pd.Timestamp | None:
        """基于统一交易日历，定位某交易日的次交易日。"""
        import pandas as pd

        if current_day not in trade_dates:
            return None
        cur_idx = int(trade_dates.get_loc(current_day))
        if cur_idx + 1 >= len(trade_dates):
            return None
        return pd.Timestamp(trade_dates[cur_idx + 1]).normalize()

    def _benchmark_return_by_mode(
        self,
        hs300_df: pd.DataFrame,
        start: pd.Timestamp,
        end: pd.Timestamp,
        return_mode: ReturnMode = "close_to_close",
    ) -> float:
        """按收益模式计算 HS300 基准收益率（缺失返回 NaN）。"""
        import pandas as pd

        hs300_df = _ensure_daily_schema(hs300_df)
        if return_mode == "next_open_to_open":
            trade_dates = pd.DatetimeIndex(hs300_df.index).normalize().sort_values()
            start_next = self._next_trade_day(trade_dates, start)
            end_next = self._next_trade_day(trade_dates, end)
            start_price = _get_open_on(hs300_df, start_next) if start_next is not None else None
            end_price = _get_open_on(hs300_df, end_next) if end_next is not None else None
        else:
            start_price = _get_close_on(hs300_df, start)
            end_price = _get_close_on(hs300_df, end)

        if start_price is None or end_price is None or start_price == 0:
            return float("nan")
        return float(end_price / start_price - 1.0)
