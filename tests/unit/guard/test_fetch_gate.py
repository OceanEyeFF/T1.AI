"""Unit tests for DataScope / FetchGate (no network)."""

from __future__ import annotations

from datetime import date

import pytest

from ashare_infra.guard.fetch_gate import (
    FetchGate,
    FetchRole,
    RolePermissionError,
    ScopeFrozenError,
    SymbolsImmutableError,
)
from ashare_infra.guard.scope import (
    DataScope,
    ListingPolicy,
    MetaSource,
    SymbolLifecycle,
    merge_symbol_lifecycle,
)


def _scope(*symbols: str) -> DataScope:
    return DataScope(
        symbols=frozenset(symbols),
        window_start=date(2024, 1, 1),
        window_end=date(2024, 12, 31),
        listing_policy=ListingPolicy.EXCLUDE_DAY,
    )


def test_data_scope_importable() -> None:
    from ashare_infra.guard.scope import DataScope as DS

    s = DS(
        symbols=frozenset({"600519"}),
        window_start=date(2024, 1, 1),
        window_end=date(2024, 6, 30),
    )
    assert "600519" in s.symbols
    assert s.in_window(date(2024, 3, 1))
    assert not s.in_window(date(2023, 12, 31))


def test_lifecycle_listing_bounds() -> None:
    meta = SymbolLifecycle(
        list_date=date(2024, 3, 1),
        delist_date=date(2024, 9, 1),
        source=MetaSource(kind="stock_basic", evidence_ref="fixture"),
    )
    scope = _scope("600000").with_meta({"600000": meta})
    assert not scope.is_tradable("600000", date(2024, 2, 28))
    assert scope.is_tradable("600000", date(2024, 3, 1))
    assert not scope.is_tradable("600000", date(2024, 9, 1))


def test_remove_symbols_rejected() -> None:
    gate = FetchGate(scope=_scope("600519", "000001"))
    with pytest.raises(SymbolsImmutableError):
        gate.remove_symbols({"000001"}, role=FetchRole.ROOT)


def test_fork_scope_shrinks_universe() -> None:
    gate = FetchGate(scope=_scope("600519", "000001"))
    parent_id = gate.scope.scope_id
    new_scope = gate.fork_scope(symbols=frozenset({"600519"}), role=FetchRole.ROOT)
    assert new_scope.symbols == frozenset({"600519"})
    assert new_scope.scope_id != parent_id
    assert new_scope.parent_scope_id == parent_id


def test_add_symbols_root_and_stockpool() -> None:
    gate = FetchGate(scope=_scope("600519"))
    gate.add_symbols({"000001"}, role=FetchRole.ROOT)
    assert gate.scope.symbols == frozenset({"600519", "000001"})

    gate2 = FetchGate(scope=_scope("600519"))
    fetches: list[frozenset[str]] = []

    def on_fetch(s: DataScope) -> None:
        fetches.append(s.symbols)

    gate2.on_fetch = on_fetch
    gate2.add_symbols({"000002"}, role=FetchRole.STOCKPOOL_REQUEST)
    assert "000002" in gate2.scope.symbols
    assert fetches  # maintain triggered


def test_auto_maintain_cannot_add() -> None:
    gate = FetchGate(scope=_scope("600519"))
    with pytest.raises(RolePermissionError):
        gate.add_symbols({"000001"}, role=FetchRole.AUTO_MAINTAIN)


def test_sim_start_freezes_scope() -> None:
    gate = FetchGate(scope=_scope("600519"))
    gate.sim_start()
    assert gate.scope.frozen
    with pytest.raises(ScopeFrozenError):
        gate.add_symbols({"000001"}, role=FetchRole.ROOT)
    with pytest.raises(ScopeFrozenError):
        gate.set_window(date(2023, 1, 1), date(2023, 12, 31), role=FetchRole.ROOT)


def test_override_lifecycle_requires_evidence() -> None:
    gate = FetchGate(scope=_scope("600519"))
    bad = SymbolLifecycle(
        list_date=date(2020, 1, 1),
        source=MetaSource(kind="scope_override", evidence_ref=""),
    )
    with pytest.raises(ValueError, match="evidence_ref"):
        gate.override_lifecycle("600519", bad, role=FetchRole.ROOT)

    good = SymbolLifecycle(
        list_date=date(2020, 1, 1),
        source=MetaSource(kind="scope_override", evidence_ref="ticket-1"),
    )
    gate.override_lifecycle("600519", good, role=FetchRole.ROOT)
    assert gate.scope.symbol_meta["600519"].list_date == date(2020, 1, 1)


def test_merge_lifecycle_priority() -> None:
    override = SymbolLifecycle(
        list_date=date(2021, 1, 1),
        source=MetaSource(kind="scope_override", evidence_ref="x"),
    )
    basic = SymbolLifecycle(
        list_date=date(2020, 1, 1),
        source=MetaSource(kind="stock_basic", evidence_ref="cache"),
    )
    inferred = SymbolLifecycle(
        list_date=date(2019, 1, 1),
        source=MetaSource(kind="infer_from_bars", evidence_ref=""),
    )
    m, warn = merge_symbol_lifecycle(
        scope_override=override, stock_basic=basic, infer_from_bars=inferred
    )
    assert m is override and warn is None

    m2, warn2 = merge_symbol_lifecycle(stock_basic=basic, infer_from_bars=inferred)
    assert m2 is basic and warn2 is None

    m3, warn3 = merge_symbol_lifecycle(infer_from_bars=inferred)
    assert m3 is inferred and warn3 is not None


def test_data_scope_rejects_inverted_window() -> None:
    with pytest.raises(ValueError):
        DataScope(
            symbols=frozenset({"600000"}),
            window_start=date(2024, 6, 1),
            window_end=date(2024, 1, 1),
            listing_policy=ListingPolicy.EXCLUDE_DAY,
        )
