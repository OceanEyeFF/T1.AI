"""Infra A unit: scope / listing edges against fixture meta."""

from __future__ import annotations

from datetime import date

from ashare_infra.guard.scope import ListingPolicy
from tests.support import infra_a as fx


def test_tradable_matrix_matches_manifest() -> None:
    scope = fx.make_scope()
    checks = {
        date(2024, 1, 5): set(fx.expected("tradable_on_2024-01-05")),
        date(2024, 1, 8): set(fx.expected("tradable_on_2024-01-08")),
        date(2024, 1, 10): set(fx.expected("tradable_on_2024-01-10")),
    }
    for day, want in checks.items():
        got = {s for s in scope.symbols if scope.is_tradable(s, day)}
        assert got == want, f"{day}: got={sorted(got)} want={sorted(want)}"


def test_late_list_excluded_before_list_date() -> None:
    scope = fx.make_scope(symbols={"600001"})
    assert not scope.is_tradable("600001", date(2024, 1, 5))
    assert scope.is_tradable("600001", date(2024, 1, 8))
    assert scope.listing_policy == ListingPolicy.EXCLUDE_DAY


def test_missing_bar_fixture_day() -> None:
    day = date.fromisoformat(fx.expected("missing_bar_day"))
    assert fx.bars_for_day("600003", day) is None
    assert fx.bars_for_day("600003", date(2024, 1, 8)) is not None
    assert fx.bars_for_day("600003", date(2024, 1, 10)) is not None
