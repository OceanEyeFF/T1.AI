"""Listing / delisting / missing-bar policy application helpers."""

from __future__ import annotations

from datetime import date

from ashare_infra.guard.scope import DataScope, ListingPolicy, MissingBarPolicy


def apply_listing_filter(scope: DataScope, symbol: str, day: date) -> bool:
    """Return True if ``(symbol, day)`` should be included under listing_policy."""
    tradable = scope.is_tradable(symbol, day)
    if tradable:
        return True
    if scope.listing_policy == ListingPolicy.EXCLUDE_DAY:
        return False
    if scope.listing_policy == ListingPolicy.FILL_NAN:
        return True  # caller must fill NaN
    if scope.listing_policy == ListingPolicy.RAISE:
        raise ValueError(f"{symbol} not tradable on {day} under RAISE policy")
    return False


def missing_bar_action(scope: DataScope) -> MissingBarPolicy:
    return scope.missing_bar_policy
