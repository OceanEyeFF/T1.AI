"""DataLake: single entry point for loading/fetching market data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd

from ashare_infra.guard.scope import DataScope
from ashare_infra.guard.temporal import truncate_as_of

SourceKind = Literal["akshare", "tushare", "odp", "smoke"]

# (symbol, start_yyyymmdd, end_yyyymmdd, adjust) -> DataFrame
LakeLoader = Callable[[str, str, str, str], pd.DataFrame]


@dataclass
class DataLake:
    """Thin façade over ``ashare_infra.data.*_source.load_or_fetch_*``.

    Upper layers (strategy / advanced / pipeline) should only call DataLake,
    never ``load_or_fetch_*`` directly.

    For smoke / CI, pass ``loader=...`` (and usually ``default_source="smoke"``)
    so no network clients are touched — see ``ashare_infra.lake.smoke``.
    """

    cache_dir: Path
    default_source: SourceKind = "tushare"
    refresh: bool = False
    loader: LakeLoader | None = None

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)

    def load_daily_bars(
        self,
        symbol: str,
        start: date | str,
        end: date | str,
        *,
        source: SourceKind | None = None,
        adjust: str = "qfq",
        as_of: date | None = None,
    ) -> pd.DataFrame:
        """Load (or fetch+cache) daily OHLCV for one symbol."""
        src = source or self.default_source
        start_s = _yyyymmdd(start)
        end_s = _yyyymmdd(end)
        df = self._load_or_fetch(src, symbol, start_s, end_s, adjust=adjust)
        if as_of is not None and not df.empty:
            df = truncate_as_of(df, as_of, inclusive=True)
        return df

    def load_scope_bars(
        self,
        scope: DataScope,
        *,
        source: SourceKind | None = None,
        adjust: str = "qfq",
        as_of: date | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Load daily bars for every symbol in ``scope`` within the management window."""
        out: dict[str, pd.DataFrame] = {}
        for symbol in sorted(scope.symbols):
            df = self.load_daily_bars(
                symbol,
                scope.window_start,
                scope.window_end,
                source=source,
                adjust=adjust,
                as_of=as_of,
            )
            if not df.empty:
                out[symbol] = df
        return out

    def _load_or_fetch(
        self,
        source: SourceKind,
        symbol: str,
        start: str,
        end: str,
        *,
        adjust: str,
    ) -> pd.DataFrame:
        if source == "smoke":
            if self.loader is None:
                raise RuntimeError(
                    "DataLake source='smoke' requires an injected loader "
                    "(see ashare_infra.lake.smoke.SmokeHarness)"
                )
            return self.loader(symbol, start, end, adjust)

        # tushare nests its own cache_ns (tushare_qfq/…) under cache_dir;
        # akshare/odp use a dedicated subfolder to avoid collisions.
        if source == "akshare":
            from ashare_infra.data.akshare_source import (
                AkshareDailyBarsRequest,
                load_or_fetch_daily_bars,
            )

            req = AkshareDailyBarsRequest(
                symbol=symbol, start_date=start, end_date=end, adjust=adjust
            )
            return load_or_fetch_daily_bars(
                req, cache_dir=self.cache_dir / "akshare", refresh=self.refresh
            )

        if source == "tushare":
            from ashare_infra.data.tushare_source import (
                TushareDailyBarsRequest,
                load_or_fetch_daily_bars,
            )

            req = TushareDailyBarsRequest(
                symbol=symbol, start_date=start, end_date=end, adjust=adjust
            )
            return load_or_fetch_daily_bars(
                req, cache_dir=self.cache_dir, refresh=self.refresh
            )

        if source == "odp":
            from ashare_infra.data.odp_source import (
                ODPDailyBarsRequest,
                load_or_fetch_daily_bars,
            )

            req = ODPDailyBarsRequest(symbol=symbol, start_date=start, end_date=end)
            return load_or_fetch_daily_bars(
                req, cache_dir=self.cache_dir / "odp", refresh=self.refresh
            )

        raise ValueError(f"unsupported source: {source}")


def _yyyymmdd(value: date | str) -> str:
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    s = str(value).replace("-", "")
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"expected YYYYMMDD or date, got {value!r}")
    return s
