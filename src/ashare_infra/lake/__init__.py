"""DataLake: single entry point for loading/fetching market data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd

from ashare_infra.guard.scope import DataScope, SymbolLifecycle
from ashare_infra.guard.temporal import truncate_as_of
from ashare_infra.lake.meta import (
    _normalize_symbol,
    read_stock_basic,
    resolve_stock_basic_path,
    stock_basic_stem_path,
    stock_basic_to_lifecycle_map,
)

SourceKind = Literal["akshare", "tushare", "odp", "smoke"]

# (symbol, start_yyyymmdd, end_yyyymmdd, adjust) -> DataFrame
LakeLoader = Callable[[str, str, str, str], pd.DataFrame]


@dataclass
class DataLake:
    """Thin façade over ``ashare_infra.data.*_source.load_or_fetch_*``.

    Upper layers (lab consumers / scripts) should only call DataLake,
    never ``load_or_fetch_*`` directly.

    For smoke / CI, pass ``loader=...`` (and usually ``default_source="smoke"``)
    so no network clients are touched — see ``ashare_infra.lake.smoke``.

    Meta (``stock_basic``) is local-cache only in WT-INFRA-001.5 — see
    ``load_stock_basic`` / ``ashare_infra.lake.meta``.
    """

    cache_dir: Path
    default_source: SourceKind = "tushare"
    refresh: bool = False
    loader: LakeLoader | None = None
    tushare_token: str | None = None
    odp_provider: str = "yfinance"
    odp_interval: str = "1d"
    odp_base_url: str | None = None
    odp_prefer_rest: bool = False

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)

    def stock_basic_path(self) -> Path:
        """Canonical stem path ``{cache_dir}/meta/stock_basic`` (no suffix)."""
        return stock_basic_stem_path(self.cache_dir)

    def load_stock_basic(self, path: Path | str | None = None) -> pd.DataFrame:
        """Load local ``stock_basic`` meta (CSV or parquet). Never hits the network.

        Default path resolution: ``{cache_dir}/meta/stock_basic.{csv,parquet}``.
        """
        resolved = resolve_stock_basic_path(self.cache_dir, path)
        return read_stock_basic(resolved)

    def load_symbol_lifecycle_map(
        self,
        path: Path | str | None = None,
        *,
        source_kind: str = "stock_basic",
    ) -> dict[str, SymbolLifecycle]:
        """Build ``SymbolLifecycle`` map from local stock_basic meta."""
        resolved = resolve_stock_basic_path(self.cache_dir, path)
        df = read_stock_basic(resolved)
        return stock_basic_to_lifecycle_map(
            df, evidence_ref=str(resolved), source_kind=source_kind
        )

    def with_stock_basic_meta(
        self,
        scope: DataScope,
        *,
        path: Path | str | None = None,
        fill_missing_only: bool = True,
    ) -> DataScope:
        """Attach stock_basic lifecycle into ``scope.symbol_meta``.

        Scope symbols may be bare 6-digit codes or ts_code style (``600519.SH``);
        lookup normalizes both to the bare form used by the lifecycle map.

        When ``fill_missing_only`` (default), only symbols without existing meta
        are filled. ``fill_missing_only=False`` still never overwrites
        ``scope_override`` meta (META_MERGE_PRIORITY: override > stock_basic).
        """
        basic_map = self.load_symbol_lifecycle_map(path=path)
        new_meta = dict(scope.symbol_meta)
        for symbol in scope.symbols:
            existing = new_meta.get(symbol)
            if existing is not None:
                if fill_missing_only:
                    continue
                if existing.source.kind == "scope_override":
                    continue
            try:
                lookup_key = _normalize_symbol(symbol)
            except ValueError:
                continue
            lifecycle = basic_map.get(lookup_key)
            if lifecycle is not None:
                new_meta[symbol] = lifecycle
        return scope.with_meta(new_meta)

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
        """Load (or fetch+cache) daily OHLCV for one symbol.

        Symbol convention is per-source: tushare expects ts_code (``600519.SH``),
        akshare/odp expect bare codes. Volume units also differ: akshare/tushare
        report lots (手), odp/yfinance reports shares — set
        ``ReplayConfig.volume_in_lots=False`` when replaying odp frames.
        """
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

    def load_index_daily(
        self,
        symbol: str,
        start: date | str,
        end: date | str,
        *,
        as_of: date | None = None,
    ) -> pd.DataFrame:
        """Load (or fetch+cache) index daily bars via ``index_source`` (AkShare).

        Cache files live under ``{cache_dir}/index_{symbol}_daily_{start}_{end}.csv``
        (same layout as the adapter; no extra nesting).
        """
        from ashare_infra.data.index_source import (
            AkshareIndexDailyRequest,
            load_or_fetch_index_daily,
        )

        start_s = _yyyymmdd(start)
        end_s = _yyyymmdd(end)
        req = AkshareIndexDailyRequest(
            symbol=symbol, start_date=start_s, end_date=end_s
        )
        df = load_or_fetch_index_daily(
            req, cache_dir=self.cache_dir, refresh=self.refresh
        )
        if as_of is not None and not df.empty:
            df = truncate_as_of(df, as_of, inclusive=True)
        return df

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
        # akshare uses cache_dir/akshare/; odp_source self-namespaces under
        # cache_dir/odp/ (pass cache_dir unmodified — do not add another odp/).
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
                symbol=symbol,
                start_date=start,
                end_date=end,
                adjust=adjust,
                token=self.tushare_token,
            )
            return load_or_fetch_daily_bars(
                req, cache_dir=self.cache_dir, refresh=self.refresh
            )

        if source == "odp":
            from ashare_infra.data.odp_source import (
                ODPDailyBarsRequest,
                load_or_fetch_daily_bars,
            )

            req = ODPDailyBarsRequest(
                symbol=symbol,
                start_date=start,
                end_date=end,
                provider=self.odp_provider,
                interval=self.odp_interval,
                base_url=self.odp_base_url,
                prefer_rest=self.odp_prefer_rest,
            )
            # odp_source 自带 odp/ 命名空间；不要再嵌套一层，否则与直调该
            # adapter 的缓存分裂成两份
            return load_or_fetch_daily_bars(
                req, cache_dir=self.cache_dir, refresh=self.refresh
            )

        raise ValueError(f"unsupported source: {source}")


def _yyyymmdd(value: date | str) -> str:
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    s = str(value).replace("-", "")
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"expected YYYYMMDD or date, got {value!r}")
    return s
