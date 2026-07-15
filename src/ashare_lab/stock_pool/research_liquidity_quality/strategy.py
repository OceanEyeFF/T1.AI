"""research_liquidity_quality 选股策略。

主板可研究/可交易卫生筛（非控盘/非 alpha）。
硬过滤后 5 维综合分排序，软目标 ≤80，硬上限 100。
默认 cache-first；不发起 live 拉数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ashare_lab.stock_pool.base import PoolCandidate, StockPoolStrategy

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

UNIVERSE_EXCLUDE_PREFIXES = ("688", "300", "301", "8", "4")
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")


@dataclass
class _Row:
    symbol: str
    ts_code: str
    total_score: float = 0.0
    sub_scores: dict[str, float] = field(default_factory=dict)
    reject_reason: str | None = None
    avg_amount_yi: float = 0.0
    avg_turnover: float = 0.0
    basic_coverage: float = 0.0
    mf_coverage: float = 0.0
    zero_volume_ratio: float = 0.0
    limit_hits: int = 0
    r_squared: float = 0.0
    amihud_illiq: float = 0.0


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, dict) else {}


def _load_partitioned_parquet(cache_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    if not cache_dir.exists():
        return frames
    for sym_dir in sorted(cache_dir.iterdir()):
        if not sym_dir.is_dir():
            continue
        parts: list[pd.DataFrame] = []
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
    out: dict[str, dict[str, pd.DataFrame]] = {}
    for key, dirname in (
        ("qfq", "tushare_qfq"),
        ("daily_basic", "tushare_daily_basic"),
        ("moneyflow", "tushare_moneyflow"),
    ):
        out[key] = _load_partitioned_parquet(data_root / dirname)
    return out


def _to_bare_and_ts(code: str) -> tuple[str, list[str]]:
    c = code.strip().upper()
    if "." in c:
        bare, mkt = c.split(".", 1)
        return bare, [f"{bare}.{mkt}"]
    return c, [f"{c}.SH", f"{c}.SZ"]


def _norm_range(values: list[float], low: float, high: float) -> list[float]:
    scores: list[float] = []
    for v in values:
        if low <= v <= high:
            scores.append(80.0)
        elif v < low:
            scores.append(max(10.0, 80.0 * (v / max(low, 1e-9))))
        else:
            over = (v - high) / max(high, 1e-9)
            scores.append(max(10.0, 80.0 - 40.0 * over))
    return scores


def _norm_positive(values: list[float]) -> list[float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return []
    lo, hi = np.nanpercentile(arr, 10), np.nanpercentile(arr, 90)
    if hi <= lo:
        return [50.0] * len(arr)
    return [float(np.clip(100.0 * (v - lo) / (hi - lo), 5.0, 100.0)) for v in arr]


def _norm_negative(values: list[float]) -> list[float]:
    return [100.0 - s for s in _norm_positive(values)]


class ResearchLiquidityQualityStrategy(StockPoolStrategy):
    """研究可交易卫生选股策略。"""

    def __init__(
        self,
        data_root: str | Path = "inputs/data/cache",
        config_path: str | Path | None = None,
        score_threshold: float | None = None,
        soft_target_size: int | None = None,
        hard_cap: int | None = None,
    ) -> None:
        self._data_root = Path(data_root)
        cfg = _load_toml(Path(config_path) if config_path else DEFAULT_CONFIG_PATH)
        st = cfg.get("strategy", {})
        weights = cfg.get("weights", {})
        sweet = cfg.get("turnover_sweet_spot", {})

        self.score_threshold = float(
            score_threshold if score_threshold is not None else st.get("score_threshold", 55.0)
        )
        self.lookback_days = int(st.get("lookback_days", 60))
        self.min_data_days = int(st.get("min_data_days", 120))
        self.soft_target_size = int(
            soft_target_size if soft_target_size is not None else st.get("soft_target_size", 80)
        )
        self.hard_cap = int(hard_cap if hard_cap is not None else st.get("hard_cap", 100))
        self.basic_coverage_min = float(st.get("basic_coverage_min", 0.80))
        self.min_avg_amount_yi = float(st.get("min_avg_amount_yi", 0.5))
        self.max_zero_volume_ratio = float(st.get("max_zero_volume_ratio", 0.15))
        self.max_limit_hits = int(st.get("max_limit_hits", 8))
        self.index_symbol = str(st.get("index_symbol", "510300.SH"))
        self.weights = {
            "liquidity_depth": float(weights.get("liquidity_depth", 0.30)),
            "turnover_health": float(weights.get("turnover_health", 0.25)),
            "data_completeness": float(weights.get("data_completeness", 0.20)),
            "trading_hygiene": float(weights.get("trading_hygiene", 0.15)),
            "market_synchronicity": float(weights.get("market_synchronicity", 0.10)),
        }
        self.turnover_sweet_low = float(sweet.get("low", 0.8))
        self.turnover_sweet_high = float(sweet.get("high", 6.0))

        if self.soft_target_size > self.hard_cap:
            raise ValueError("soft_target_size must be <= hard_cap")

    @property
    def name(self) -> str:
        return "research_liquidity_quality"

    @property
    def description(self) -> str:
        return "主板研究可交易卫生筛（流动性/完备性/卫生；非控盘断言）"

    def select(self, universe: list[str]) -> PoolCandidate:
        filtered: list[str] = []
        for s in universe:
            bare = s.split(".")[0]
            if bare.startswith(UNIVERSE_EXCLUDE_PREFIXES):
                continue
            filtered.append(s)
        if not filtered:
            return PoolCandidate(
                symbols=[],
                metadata={"error": "no symbols pass board hard-filter H1", "strategy": self.name},
            )

        caches = _load_caches(self._data_root)
        qfq = caches.get("qfq", {})
        basic = caches.get("daily_basic", {})
        mf = caches.get("moneyflow", {})

        index_returns: pd.Series | None = None
        idx_df = qfq.get(self.index_symbol)
        if idx_df is not None and len(idx_df) > 0:
            tmp = idx_df.copy()
            tmp["return"] = tmp["close"].pct_change()
            index_returns = tmp.set_index("date")["return"].dropna()

        rows: list[_Row] = []
        rejects: dict[str, str] = {}
        seen_bare: set[str] = set()

        for code in filtered:
            bare, ts_candidates = _to_bare_and_ts(code)
            if bare in seen_bare:
                continue
            # 指数锚点只用于 D5 同步性，不计入池规模
            if self.index_symbol in ts_candidates or code.upper() == self.index_symbol:
                continue
            ts_code = next((t for t in ts_candidates if t in qfq), None)
            if ts_code is None:
                rejects[bare] = "H3_missing_qfq_cache"
                continue
            seen_bare.add(bare)
            row = self._evaluate_one(
                bare=bare,
                ts_code=ts_code,
                df_qfq=qfq[ts_code],
                df_basic=basic.get(ts_code),
                df_mf=mf.get(ts_code),
                index_returns=index_returns,
            )
            if row.reject_reason:
                rejects[bare] = row.reject_reason
                continue
            rows.append(row)

        self._score_rows(rows)
        eligible = [r for r in rows if r.total_score >= self.score_threshold]
        eligible.sort(key=lambda r: r.total_score, reverse=True)
        selected = eligible[: self.soft_target_size]
        if len(selected) > self.hard_cap:
            selected = selected[: self.hard_cap]

        reject_reason_counts: dict[str, int] = {}
        for reason in rejects.values():
            reject_reason_counts[reason] = reject_reason_counts.get(reason, 0) + 1

        return PoolCandidate(
            symbols=[r.symbol for r in selected],
            metadata={
                "strategy": self.name,
                "score_threshold": self.score_threshold,
                "soft_target_size": self.soft_target_size,
                "hard_cap": self.hard_cap,
                "total_input": len(universe),
                "total_scored": len(rows),
                "total_selected": len(selected),
                "rejects_sample": dict(list(rejects.items())[:50]),
                "reject_count": len(rejects),
                "reject_reason_counts": reject_reason_counts,
                "index_symbol": self.index_symbol,
                "index_available": index_returns is not None and len(index_returns) > 0,
                "amount_unit": "tushare_thousand_cny",
                "weights": self.weights,
                "scores": {
                    r.symbol: {
                        "total": r.total_score,
                        "sub": r.sub_scores,
                        "ts_code": r.ts_code,
                        "avg_amount_yi": r.avg_amount_yi,
                        "avg_turnover": r.avg_turnover,
                        "basic_coverage": r.basic_coverage,
                        "limit_hits": r.limit_hits,
                    }
                    for r in selected
                },
            },
        )

    def _evaluate_one(
        self,
        *,
        bare: str,
        ts_code: str,
        df_qfq: pd.DataFrame,
        df_basic: pd.DataFrame | None,
        df_mf: pd.DataFrame | None,
        index_returns: pd.Series | None,
    ) -> _Row:
        row = _Row(symbol=bare, ts_code=ts_code)
        if df_qfq is None or len(df_qfq) < self.min_data_days:
            row.reject_reason = "H3_insufficient_qfq_days"
            return row

        df = df_qfq.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        if len(df) < self.min_data_days:
            row.reject_reason = "H3_insufficient_qfq_days"
            return row

        recent = df.tail(self.lookback_days)
        if len(recent) < self.lookback_days:
            row.reject_reason = "H3_insufficient_lookback"
            return row

        # H4 basic coverage
        if df_basic is None or len(df_basic) == 0:
            row.reject_reason = "H4_missing_daily_basic"
            return row
        basic = df_basic.copy()
        basic["date"] = pd.to_datetime(basic["date"])
        basic_recent = basic[basic["date"].isin(recent["date"])]
        coverage = len(basic_recent) / max(len(recent), 1)
        row.basic_coverage = round(coverage, 3)
        if coverage < self.basic_coverage_min:
            row.reject_reason = "H4_basic_coverage"
            return row
        if "circ_mv" not in basic_recent.columns and "turnover_rate" not in basic_recent.columns:
            row.reject_reason = "H4_basic_fields_missing"
            return row

        # amount / volume hygiene
        # TuShare amount 单位为千元；亿元 = amount / 1e5
        if "amount" not in recent.columns:
            row.reject_reason = "H5_missing_amount"
            return row
        amount_yi = recent["amount"].astype(float) / 1e5
        row.avg_amount_yi = float(amount_yi.mean())
        if row.avg_amount_yi < self.min_avg_amount_yi:
            row.reject_reason = "H5_amount_floor"
            return row

        vol = recent["volume"] if "volume" in recent.columns else pd.Series(dtype=float)
        if len(vol) > 0:
            row.zero_volume_ratio = float((vol.fillna(0) <= 0).mean())
        if row.zero_volume_ratio > self.max_zero_volume_ratio:
            row.reject_reason = "H6_zero_volume_ratio"
            return row

        ret = recent["close"].pct_change()
        # rough limit-up/down proxy for A-share ~9.5%
        row.limit_hits = int(((ret.abs() >= 0.095) & ret.notna()).sum())
        if row.limit_hits > self.max_limit_hits:
            row.reject_reason = "H7_limit_hits"
            return row

        if "turnover_rate" in basic_recent.columns:
            row.avg_turnover = float(basic_recent["turnover_rate"].mean())

        if df_mf is not None and len(df_mf) > 0:
            mf = df_mf.copy()
            mf["date"] = pd.to_datetime(mf["date"])
            mf_recent = mf[mf["date"].isin(recent["date"])]
            row.mf_coverage = round(len(mf_recent) / max(len(recent), 1), 3)

        illiq = ret.abs() / amount_yi.replace(0, np.nan)
        row.amihud_illiq = float(illiq.mean()) if len(illiq) else 1.0

        if index_returns is not None:
            aligned_ret = recent.set_index("date")["close"].pct_change().dropna()
            aligned_idx = index_returns.reindex(aligned_ret.index).dropna()
            aligned_ret = aligned_ret.loc[aligned_idx.index]
            if len(aligned_ret) >= 30:
                corr = np.corrcoef(aligned_ret.values, aligned_idx.values)[0, 1]
                if np.isfinite(corr):
                    row.r_squared = float(corr**2)

        return row

    def _score_rows(self, rows: list[_Row]) -> None:
        if not rows:
            return
        amounts = [r.avg_amount_yi for r in rows]
        illiqs = [r.amihud_illiq if np.isfinite(r.amihud_illiq) else 1.0 for r in rows]
        turnovers = [r.avg_turnover for r in rows]
        completeness = [
            100.0 * (0.6 * r.basic_coverage + 0.4 * r.mf_coverage) for r in rows
        ]
        hygiene = [
            max(
                5.0,
                100.0
                - 50.0 * r.zero_volume_ratio / max(self.max_zero_volume_ratio, 1e-9)
                - 40.0 * r.limit_hits / max(self.max_limit_hits, 1),
            )
            for r in rows
        ]
        sync = [50.0 if r.r_squared <= 0 else float(np.clip(100.0 * r.r_squared, 5.0, 100.0)) for r in rows]

        s_liq = [
            0.6 * a + 0.4 * b
            for a, b in zip(_norm_positive(amounts), _norm_negative(illiqs))
        ]
        s_turn = _norm_range(turnovers, self.turnover_sweet_low, self.turnover_sweet_high)

        w = self.weights
        for i, r in enumerate(rows):
            r.total_score = round(
                w["liquidity_depth"] * s_liq[i]
                + w["turnover_health"] * s_turn[i]
                + w["data_completeness"] * completeness[i]
                + w["trading_hygiene"] * hygiene[i]
                + w["market_synchronicity"] * sync[i],
                1,
            )
            r.sub_scores = {
                "liquidity_depth": round(s_liq[i], 1),
                "turnover_health": round(s_turn[i], 1),
                "data_completeness": round(completeness[i], 1),
                "trading_hygiene": round(hygiene[i], 1),
                "market_synchronicity": round(sync[i], 1),
            }
