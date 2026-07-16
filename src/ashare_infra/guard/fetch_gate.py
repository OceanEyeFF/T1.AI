"""FetchGate: role-based scope mutation and incremental fetch triggers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Callable

from ashare_infra.guard.scope import DataScope, ListingPolicy, SymbolLifecycle


class FetchRole(str, Enum):
    """Who is allowed to mutate scope / pull data."""

    AUTO_MAINTAIN = "auto_maintain"
    """(a) Boundary-local incremental fetch only; no scope mutation."""

    ROOT = "root"
    """(b) May change window / add symbols; remove only via fork."""

    STOCKPOOL_REQUEST = "stockpool_request"
    """(c) Append-only symbols; remove only via fork; then triggers (a)."""

    SIM_START = "sim_start"
    """(d) Trigger (a), then freeze scope — no further patch/add/override."""


class ScopeFrozenError(RuntimeError):
    """Raised when a frozen scope rejects mutation."""


class SymbolsImmutableError(RuntimeError):
    """Raised when attempting to remove symbols from a scope (must fork)."""


class RolePermissionError(RuntimeError):
    """Raised when a FetchRole attempts a disallowed operation."""


FetchCallback = Callable[[DataScope], None]


@dataclass
class FetchGate:
    """Gatekeeper for DataScope mutations and fetch triggers.

    Rules (WT-INFRA-001):
    - symbols are append-only on a given scope_id; removal requires ``fork_scope``
    - SIM_START freezes the scope after maintain fetch
    - AUTO_MAINTAIN may only pull incremental data inside existing boundaries
    """

    scope: DataScope
    on_fetch: FetchCallback | None = None
    _history: list[DataScope] = field(default_factory=list, repr=False)

    def _ensure_mutable(self, role: FetchRole) -> None:
        if self.scope.frozen:
            raise ScopeFrozenError(
                f"scope {self.scope.scope_id} is frozen; role={role.value} cannot mutate"
            )

    def _record(self) -> None:
        # DataScope is frozen/immutable — store prior snapshots by reference.
        self._history.append(self.scope)

    def maintain(self, role: FetchRole = FetchRole.AUTO_MAINTAIN) -> DataScope:
        """(a) Incremental fetch within current boundary — no scope change."""
        if role not in (
            FetchRole.AUTO_MAINTAIN,
            FetchRole.ROOT,
            FetchRole.STOCKPOOL_REQUEST,
            FetchRole.SIM_START,
        ):
            raise RolePermissionError(f"role {role} cannot maintain")
        if self.on_fetch is not None:
            self.on_fetch(self.scope)
        return self.scope

    def set_window(
        self,
        window_start: date,
        window_end: date,
        *,
        role: FetchRole,
    ) -> DataScope:
        """Change management window — ROOT only."""
        if role != FetchRole.ROOT:
            raise RolePermissionError(f"role {role.value} cannot change window")
        self._ensure_mutable(role)
        self._record()
        self.scope = self.scope.with_window(window_start, window_end)
        return self.scope

    def add_symbols(self, symbols: set[str] | frozenset[str], *, role: FetchRole) -> DataScope:
        """Append symbols. Allowed for ROOT and STOCKPOOL_REQUEST (not AUTO / SIM)."""
        if role not in (FetchRole.ROOT, FetchRole.STOCKPOOL_REQUEST):
            raise RolePermissionError(f"role {role.value} cannot add_symbols")
        self._ensure_mutable(role)
        self._record()
        merged = frozenset(self.scope.symbols) | frozenset(symbols)
        self.scope = self.scope.with_symbols(merged)
        if role == FetchRole.STOCKPOOL_REQUEST:
            self.maintain(FetchRole.AUTO_MAINTAIN)
        return self.scope

    def remove_symbols(self, symbols: set[str] | frozenset[str], *, role: FetchRole) -> DataScope:
        """Always rejected — use ``fork_scope`` to shrink the universe."""
        _ = symbols, role
        raise SymbolsImmutableError(
            "symbols cannot be removed from an existing scope_id; call fork_scope() instead"
        )

    def override_lifecycle(
        self,
        symbol: str,
        lifecycle: SymbolLifecycle,
        *,
        role: FetchRole,
    ) -> DataScope:
        """Attach scope_override lifecycle for one symbol — ROOT only; blocked when frozen."""
        if role != FetchRole.ROOT:
            raise RolePermissionError(f"role {role.value} cannot override_lifecycle")
        self._ensure_mutable(role)
        if lifecycle.source.kind != "scope_override":
            raise ValueError("override lifecycle source.kind must be 'scope_override'")
        if not lifecycle.source.evidence_ref:
            raise ValueError("override lifecycle requires source.evidence_ref")
        self._record()
        meta = dict(self.scope.symbol_meta)
        meta[symbol] = lifecycle
        self.scope = self.scope.with_meta(meta)
        return self.scope

    def fork_scope(
        self,
        *,
        symbols: frozenset[str] | None = None,
        window_start: date | None = None,
        window_end: date | None = None,
        listing_policy: ListingPolicy | None = None,
        notes: str = "",
        role: FetchRole = FetchRole.ROOT,
    ) -> DataScope:
        """Create a new scope_id (e.g. to drop symbols). Always allowed to fork."""
        if role not in (FetchRole.ROOT, FetchRole.STOCKPOOL_REQUEST):
            raise RolePermissionError(f"role {role.value} cannot fork_scope")
        # Fork does not mutate the frozen parent; it replaces the gate's active scope.
        self._record()
        self.scope = self.scope.fork(
            symbols=symbols,
            window_start=window_start,
            window_end=window_end,
            listing_policy=listing_policy,
            notes=notes,
        )
        return self.scope

    def sim_start(self) -> DataScope:
        """(d) Maintain then freeze — subsequent patch/add/override rejected."""
        self.maintain(FetchRole.AUTO_MAINTAIN)
        self._record()
        self.scope = self.scope.freeze()
        return self.scope
