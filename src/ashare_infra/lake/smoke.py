"""Smoke fetch backend — network-free simulated download / scope ops for Infra.

Use this to exercise FetchGate + DataLake without TuShare/AkShare:

- ``simulate_download`` — maintain-fetch: materialize catalog bars into smoke cache
- ``simulate_add_stocks`` — ROOT add_symbols + optional auto-download
- ``simulate_set_window`` / ``simulate_set_start`` — ROOT window change + download
- journal of ``SmokeEvent`` for assertions / CLI reports

Typical wiring::

    harness = SmokeHarness.from_catalog(catalog, cache_dir=tmp)
    harness.simulate_download()
    harness.simulate_add_stocks({"600001"})
    harness.simulate_set_start(date(2024, 1, 5))
    bars = harness.lake.load_scope_bars(harness.gate.scope)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Mapping

import pandas as pd

from ashare_infra.guard.fetch_gate import FetchGate, FetchRole
from ashare_infra.guard.scope import DataScope
from ashare_infra.lake import DataLake

SmokeEventKind = Literal[
    "download",
    "add_symbols",
    "set_window",
    "set_start",
    "fork",
    "sim_start",
    "maintain",
]


@dataclass(frozen=True)
class SmokeEvent:
    kind: SmokeEventKind
    at: datetime
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class SmokeCatalog:
    """In-memory 'remote' universe: symbol → full OHLCV frame (DatetimeIndex)."""

    frames: dict[str, pd.DataFrame] = field(default_factory=dict)

    @classmethod
    def from_frames(cls, frames: Mapping[str, pd.DataFrame]) -> SmokeCatalog:
        normalized: dict[str, pd.DataFrame] = {}
        for symbol, df in frames.items():
            work = df.copy()
            if not isinstance(work.index, pd.DatetimeIndex):
                if "date" in work.columns:
                    work = work.set_index("date")
                work.index = pd.to_datetime(work.index)
            work = work.sort_index()
            normalized[str(symbol)] = work
        return cls(frames=normalized)

    def has(self, symbol: str) -> bool:
        return symbol in self.frames

    def slice(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        if symbol not in self.frames:
            return pd.DataFrame()
        df = self.frames[symbol]
        lo = pd.Timestamp(start)
        hi = pd.Timestamp(end)
        return df.loc[(df.index >= lo) & (df.index <= hi)].copy()


@dataclass
class SmokeBackend:
    """Materializes catalog slices into ``cache_dir`` (smoke local lake)."""

    catalog: SmokeCatalog
    cache_dir: Path
    journal: list[SmokeEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _log(self, kind: SmokeEventKind, **detail: Any) -> None:
        self.journal.append(SmokeEvent(kind=kind, at=datetime.now(), detail=dict(detail)))

    def cache_path(self, symbol: str) -> Path:
        return self.cache_dir / "smoke" / f"{symbol}.parquet"

    def materialize(self, scope: DataScope, *, reason: str = "maintain") -> dict[str, int]:
        """Write/refresh cached bars for every symbol in scope within the window.

        Returns ``{symbol: n_rows}`` written (0 if catalog miss).
        """
        written: dict[str, int] = {}
        out_dir = self.cache_dir / "smoke"
        out_dir.mkdir(parents=True, exist_ok=True)
        for symbol in sorted(scope.symbols):
            frame = self.catalog.slice(symbol, scope.window_start, scope.window_end)
            path = self.cache_path(symbol)
            if frame.empty:
                written[symbol] = 0
                if path.exists():
                    path.unlink()
                continue
            frame.to_parquet(path)
            written[symbol] = int(len(frame))
        self._log(
            "download",
            reason=reason,
            scope_id=scope.scope_id,
            window_start=scope.window_start.isoformat(),
            window_end=scope.window_end.isoformat(),
            symbols=sorted(scope.symbols),
            rows=written,
        )
        return written

    def load_cached(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        path = self.cache_path(symbol)
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_parquet(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            if "date" in df.columns:
                df = df.set_index("date")
            df.index = pd.to_datetime(df.index)
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        return df.loc[(df.index >= lo) & (df.index <= hi)].copy()

    def as_fetch_callback(self):
        def _on_fetch(scope: DataScope) -> None:
            self.materialize(scope, reason="on_fetch")

        return _on_fetch

    def as_loader(self):
        """DataLake.loader compatible: (symbol, start_yyyymmdd, end_yyyymmdd, adjust) → DF."""

        def _loader(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
            _ = adjust
            return self.load_cached(
                symbol,
                date(int(start[:4]), int(start[4:6]), int(start[6:8])),
                date(int(end[:4]), int(end[4:6]), int(end[6:8])),
            )

        return _loader


@dataclass
class SmokeHarness:
    """High-level smoke controller: simulate download / add stock / change start."""

    gate: FetchGate
    lake: DataLake
    backend: SmokeBackend
    auto_download_on_mutate: bool = True

    @classmethod
    def create(
        cls,
        scope: DataScope,
        catalog: SmokeCatalog,
        cache_dir: Path | str,
        *,
        auto_download_on_mutate: bool = True,
    ) -> SmokeHarness:
        backend = SmokeBackend(catalog=catalog, cache_dir=Path(cache_dir))
        gate = FetchGate(scope=scope, on_fetch=backend.as_fetch_callback())
        lake = DataLake(
            cache_dir=Path(cache_dir),
            default_source="smoke",
            loader=backend.as_loader(),
        )
        return cls(
            gate=gate,
            lake=lake,
            backend=backend,
            auto_download_on_mutate=auto_download_on_mutate,
        )

    @property
    def scope(self) -> DataScope:
        return self.gate.scope

    @property
    def journal(self) -> list[SmokeEvent]:
        return self.backend.journal

    def simulate_download(self, *, role: FetchRole = FetchRole.AUTO_MAINTAIN) -> dict[str, int]:
        """Simulate incremental / full download within current scope boundary."""
        before = len(self.journal)
        self.gate.maintain(role=role)
        # on_fetch already logged download; if no callback ran, materialize explicitly
        if len(self.journal) == before:
            return self.backend.materialize(self.scope, reason="simulate_download")
        last = self.journal[-1]
        return dict(last.detail.get("rows", {}))

    def simulate_add_stocks(
        self,
        symbols: set[str] | frozenset[str] | list[str],
        *,
        role: FetchRole = FetchRole.ROOT,
    ) -> DataScope:
        """Simulate appending symbols (ROOT / STOCKPOOL_REQUEST)."""
        syms = frozenset(symbols)
        missing = sorted(s for s in syms if not self.backend.catalog.has(s))
        if missing:
            raise KeyError(f"smoke catalog missing symbols: {missing}")
        # Log intent before gate mutation so journal order is add_symbols → download
        # (STOCKPOOL_REQUEST triggers maintain/on_fetch inside FetchGate.add_symbols).
        self.backend._log(
            "add_symbols",
            symbols=sorted(syms),
            role=role.value,
            scope_id=self.scope.scope_id,
            universe=sorted(frozenset(self.scope.symbols) | syms),
        )
        self.gate.add_symbols(syms, role=role)
        if self.auto_download_on_mutate and role == FetchRole.ROOT:
            # STOCKPOOL_REQUEST already triggers maintain inside FetchGate
            self.simulate_download()
        return self.scope

    def simulate_set_window(
        self,
        window_start: date,
        window_end: date,
        *,
        role: FetchRole = FetchRole.ROOT,
    ) -> DataScope:
        """Simulate changing the management window (ROOT)."""
        self.gate.set_window(window_start, window_end, role=role)
        self.backend._log(
            "set_window",
            window_start=window_start.isoformat(),
            window_end=window_end.isoformat(),
            role=role.value,
            scope_id=self.scope.scope_id,
        )
        if self.auto_download_on_mutate:
            self.simulate_download()
        return self.scope

    def simulate_set_start(self, window_start: date, *, role: FetchRole = FetchRole.ROOT) -> DataScope:
        """Simulate changing only ``window_start`` (keep end)."""
        end = self.scope.window_end
        self.gate.set_window(window_start, end, role=role)
        self.backend._log(
            "set_start",
            window_start=window_start.isoformat(),
            window_end=end.isoformat(),
            role=role.value,
            scope_id=self.scope.scope_id,
        )
        if self.auto_download_on_mutate:
            self.simulate_download()
        return self.scope

    def simulate_fork(
        self,
        *,
        symbols: frozenset[str] | set[str] | None = None,
        notes: str = "smoke_fork",
    ) -> DataScope:
        self.gate.fork_scope(
            symbols=frozenset(symbols) if symbols is not None else None,
            notes=notes,
            role=FetchRole.ROOT,
        )
        self.backend._log(
            "fork",
            symbols=sorted(self.scope.symbols),
            scope_id=self.scope.scope_id,
            parent=self.scope.parent_scope_id,
            notes=notes,
        )
        if self.auto_download_on_mutate:
            self.simulate_download()
        return self.scope

    def simulate_sim_start(self) -> DataScope:
        self.gate.sim_start()
        self.backend._log("sim_start", scope_id=self.scope.scope_id, frozen=True)
        return self.scope

    def load_scope_bars(self) -> dict[str, pd.DataFrame]:
        return self.lake.load_scope_bars(self.scope)

    def report(self) -> dict[str, Any]:
        return {
            "scope_id": self.scope.scope_id,
            "frozen": self.scope.frozen,
            "symbols": sorted(self.scope.symbols),
            "window_start": self.scope.window_start.isoformat(),
            "window_end": self.scope.window_end.isoformat(),
            "events": [
                {"kind": e.kind, "at": e.at.isoformat(timespec="seconds"), **e.detail}
                for e in self.journal
            ],
            "cached_symbols": sorted(
                p.stem for p in (self.backend.cache_dir / "smoke").glob("*.parquet")
            ),
        }
