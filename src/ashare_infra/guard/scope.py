"""DataScope and listing / lifecycle types for infra guard."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from enum import Enum
from typing import Mapping
from uuid import uuid4


class ListingPolicy(str, Enum):
    """How to treat symbols outside list/delist bounds or with missing bars."""

    EXCLUDE_DAY = "exclude_day"
    """Drop the (symbol, day) from evaluation / matching for that day."""

    FILL_NAN = "fill_nan"
    """Keep the row but mark prices as NaN (research-only)."""

    RAISE = "raise"
    """Fail hard when a day falls outside listing or bar is missing."""


class MissingBarPolicy(str, Enum):
    """Sim / backtest behaviour when a bar is absent for a held or ordered symbol."""

    REJECT = "reject"
    """Reject the order (existing PaperBroker missing_bar behaviour)."""

    SKIP = "skip"
    """Silently skip matching for that symbol-day."""

    RAISE = "raise"


@dataclass(frozen=True)
class MetaSource:
    """Provenance for lifecycle metadata overrides (CodeX / SearchEngine review)."""

    kind: str
    """e.g. ``stock_basic``, ``scope_override``, ``infer_from_bars``."""

    evidence_ref: str = ""
    """Pointer to evidence (path, ticket, or search hit id)."""


@dataclass(frozen=True)
class SymbolLifecycle:
    """Per-symbol list / delist dates."""

    list_date: date | None = None
    delist_date: date | None = None
    source: MetaSource = field(
        default_factory=lambda: MetaSource(kind="unknown", evidence_ref="")
    )

    def is_listed_on(self, day: date) -> bool:
        if self.list_date is not None and day < self.list_date:
            return False
        if self.delist_date is not None and day >= self.delist_date:
            return False
        return True


@dataclass(frozen=True)
class DataScope:
    """Three-boundary scope: symbols × management window × listing policy."""

    symbols: frozenset[str]
    window_start: date
    window_end: date
    listing_policy: ListingPolicy = ListingPolicy.EXCLUDE_DAY
    missing_bar_policy: MissingBarPolicy = MissingBarPolicy.REJECT
    symbol_meta: Mapping[str, SymbolLifecycle] = field(default_factory=dict)
    scope_id: str = field(default_factory=lambda: uuid4().hex)
    frozen: bool = False
    parent_scope_id: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.window_end < self.window_start:
            raise ValueError(
                f"window_end {self.window_end} < window_start {self.window_start}"
            )
        object.__setattr__(self, "symbols", frozenset(self.symbols))
        # Freeze nested mapping view
        object.__setattr__(self, "symbol_meta", dict(self.symbol_meta))

    def contains_symbol(self, symbol: str) -> bool:
        return symbol in self.symbols

    def in_window(self, day: date) -> bool:
        return self.window_start <= day <= self.window_end

    def is_tradable(self, symbol: str, day: date) -> bool:
        if not self.contains_symbol(symbol):
            return False
        if not self.in_window(day):
            return False
        meta = self.symbol_meta.get(symbol)
        if meta is None:
            return True
        return meta.is_listed_on(day)

    def with_symbols(self, symbols: frozenset[str]) -> DataScope:
        return replace(self, symbols=frozenset(symbols))

    def with_window(self, window_start: date, window_end: date) -> DataScope:
        return replace(self, window_start=window_start, window_end=window_end)

    def with_meta(self, symbol_meta: Mapping[str, SymbolLifecycle]) -> DataScope:
        return replace(self, symbol_meta=dict(symbol_meta))

    def freeze(self) -> DataScope:
        return replace(self, frozen=True)

    def fork(
        self,
        *,
        symbols: frozenset[str] | None = None,
        window_start: date | None = None,
        window_end: date | None = None,
        listing_policy: ListingPolicy | None = None,
        missing_bar_policy: MissingBarPolicy | None = None,
        symbol_meta: Mapping[str, SymbolLifecycle] | None = None,
        notes: str = "",
    ) -> DataScope:
        """Create a new scope_id; used when removing symbols (immutable set)."""
        return DataScope(
            symbols=frozenset(symbols) if symbols is not None else self.symbols,
            window_start=window_start if window_start is not None else self.window_start,
            window_end=window_end if window_end is not None else self.window_end,
            listing_policy=listing_policy if listing_policy is not None else self.listing_policy,
            missing_bar_policy=(
                missing_bar_policy if missing_bar_policy is not None else self.missing_bar_policy
            ),
            symbol_meta=dict(symbol_meta) if symbol_meta is not None else dict(self.symbol_meta),
            scope_id=uuid4().hex,
            frozen=False,
            parent_scope_id=self.scope_id,
            notes=notes or self.notes,
        )


# Merge priority for lifecycle metadata (documented for FetchGate / lake):
# scope override > stock_basic > INFER_FROM_BARS (fallback + WARN)
META_MERGE_PRIORITY = ("scope_override", "stock_basic", "infer_from_bars")


def merge_symbol_lifecycle(
    *,
    scope_override: SymbolLifecycle | None = None,
    stock_basic: SymbolLifecycle | None = None,
    infer_from_bars: SymbolLifecycle | None = None,
) -> tuple[SymbolLifecycle | None, str | None]:
    """Merge lifecycle sources by priority. Returns (meta, warn_msg)."""
    if scope_override is not None:
        return scope_override, None
    if stock_basic is not None:
        return stock_basic, None
    if infer_from_bars is not None:
        return infer_from_bars, "lifecycle inferred from bars only (fallback)"
    return None, None
