"""U-G listing: apply_listing_filter + missing_bar_action (Phase 1 helpers)."""

from __future__ import annotations

from datetime import date

import pytest

from ashare_infra.guard.listing import apply_listing_filter, missing_bar_action
from ashare_infra.guard.scope import (
    DataScope,
    ListingPolicy,
    MissingBarPolicy,
    SymbolLifecycle,
)


def _scope(
    *,
    listing_policy: ListingPolicy,
    missing_bar_policy: MissingBarPolicy = MissingBarPolicy.REJECT,
) -> DataScope:
    return DataScope(
        symbols=frozenset({"600000"}),
        window_start=date(2024, 1, 1),
        window_end=date(2024, 12, 31),
        listing_policy=listing_policy,
        missing_bar_policy=missing_bar_policy,
        symbol_meta={
            "600000": SymbolLifecycle(
                list_date=date(2024, 2, 1),
                delist_date=None,
            )
        },
    )


def test_apply_listing_filter_tradable_always_true() -> None:
    scope = _scope(listing_policy=ListingPolicy.EXCLUDE_DAY)
    assert apply_listing_filter(scope, "600000", date(2024, 3, 1)) is True


def test_apply_listing_filter_exclude_day() -> None:
    scope = _scope(listing_policy=ListingPolicy.EXCLUDE_DAY)
    assert apply_listing_filter(scope, "600000", date(2024, 1, 15)) is False


def test_apply_listing_filter_fill_nan_keeps_row() -> None:
    scope = _scope(listing_policy=ListingPolicy.FILL_NAN)
    assert apply_listing_filter(scope, "600000", date(2024, 1, 15)) is True


def test_apply_listing_filter_raise() -> None:
    scope = _scope(listing_policy=ListingPolicy.RAISE)
    with pytest.raises(ValueError, match="not tradable"):
        apply_listing_filter(scope, "600000", date(2024, 1, 15))


def test_missing_bar_action_passthrough() -> None:
    scope = _scope(
        listing_policy=ListingPolicy.EXCLUDE_DAY,
        missing_bar_policy=MissingBarPolicy.SKIP,
    )
    assert missing_bar_action(scope) is MissingBarPolicy.SKIP
