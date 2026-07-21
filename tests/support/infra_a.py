"""Infra A fixture loaders and factories (lake + sim + guard).

Fixture root: ``tests/fixtures/infra_a/``

Layers covered by this pack
---------------------------
- **U*** unit: scope/gate, fill/broker edges, IC panel
- **I*** integration: DataLake from seeded cache, TestSession freeze+replay+IC
- **C*** contract: ashare_lab shim identity

Deterministic synthetic market — no network.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_infra.guard.scope import (
    DataScope,
    ListingPolicy,
    MetaSource,
    MissingBarPolicy,
    SymbolLifecycle,
)
from ashare_infra.sim.types import DailyBar

from tests.support.paths import REPO_ROOT

FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "infra_a"


def fixture_root() -> Path:
    return FIXTURE_ROOT


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _parse_day(value: str | date | datetime | pd.Timestamp) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return pd.Timestamp(value).date()


def calendar() -> list[date]:
    return [_parse_day(d) for d in load_manifest()["calendar"]]


def window() -> tuple[date, date]:
    w = load_manifest()["window"]
    return _parse_day(w["start"]), _parse_day(w["end"])


def load_bars(symbol: str) -> pd.DataFrame:
    path = FIXTURE_ROOT / "bars" / f"{symbol}.csv"
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    df.index = pd.DatetimeIndex(df.index)
    return df


def load_all_bars(symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    manifest = load_manifest()
    syms = symbols if symbols is not None else sorted(manifest["symbols"].keys())
    return {s: load_bars(s) for s in syms}


def load_stock_basic() -> pd.DataFrame:
    df = pd.read_csv(FIXTURE_ROOT / "meta" / "stock_basic.csv", dtype=str).fillna("")
    out_rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        delist_raw = str(row.delist_date).strip()
        out_rows.append(
            {
                "symbol": str(row.symbol).strip(),
                "list_date": _parse_day(row.list_date),
                "delist_date": _parse_day(delist_raw) if delist_raw else None,
            }
        )
    return pd.DataFrame(out_rows)


def symbol_lifecycle_map(*, source_kind: str = "stock_basic") -> dict[str, SymbolLifecycle]:
    out: dict[str, SymbolLifecycle] = {}
    for row in load_stock_basic().itertuples(index=False):
        out[str(row.symbol)] = SymbolLifecycle(
            list_date=row.list_date,
            delist_date=row.delist_date,
            source=MetaSource(
                kind=source_kind,
                evidence_ref=str(FIXTURE_ROOT / "meta" / "stock_basic.csv"),
            ),
        )
    return out


def make_scope(
    *,
    symbols: frozenset[str] | set[str] | None = None,
    listing_policy: ListingPolicy = ListingPolicy.EXCLUDE_DAY,
    missing_bar_policy: MissingBarPolicy = MissingBarPolicy.REJECT,
    include_meta: bool = True,
) -> DataScope:
    start, end = window()
    manifest = load_manifest()
    syms = frozenset(symbols) if symbols is not None else frozenset(manifest["symbols"].keys())
    meta = symbol_lifecycle_map() if include_meta else {}
    return DataScope(
        symbols=syms,
        window_start=start,
        window_end=end,
        listing_policy=listing_policy,
        missing_bar_policy=missing_bar_policy,
        symbol_meta=meta,
        notes="infra_a fixture scope",
    )


def make_ic_scope() -> DataScope:
    return make_scope(
        symbols={"600000", "000001", "600003"},
        listing_policy=ListingPolicy.EXCLUDE_DAY,
        missing_bar_policy=MissingBarPolicy.SKIP,
    )


def make_sim_scope() -> DataScope:
    return make_scope(
        symbols={"600000", "600003", "600004"},
        listing_policy=ListingPolicy.EXCLUDE_DAY,
        missing_bar_policy=MissingBarPolicy.REJECT,
    )


def load_ic_panel() -> tuple[pd.Series, pd.Series]:
    df = pd.read_csv(FIXTURE_ROOT / "panels" / "ic_preds_labels.csv")
    df["date"] = pd.to_datetime(df["date"])
    idx = pd.MultiIndex.from_frame(df[["date", "symbol"]])
    predictions = pd.Series(df["prediction"].to_numpy(), index=idx, name="prediction")
    labels = pd.Series(df["label"].to_numpy(), index=idx, name="label")
    return predictions, labels


def bars_for_day(symbol: str, day: date) -> DailyBar | None:
    """Build a DailyBar for ``day`` using prior close as prev_close."""
    df = load_bars(symbol)
    ts = pd.Timestamp(day)
    if ts not in df.index:
        return None
    loc = int(df.index.get_loc(ts))
    if loc <= 0:
        return None
    row = df.iloc[loc]
    prev_close = float(df.iloc[loc - 1]["close"])
    return DailyBar(
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]) * 100.0,  # lots → shares (replay default)
        prev_close=prev_close,
    )


def seeded_cache_dir() -> Path:
    return FIXTURE_ROOT / "seeded_cache"


def expected(key: str) -> Any:
    return load_manifest()["expected"][key]


def build_smoke_harness(
    cache_dir: Path,
    *,
    symbols: set[str] | frozenset[str] | None = None,
):
    """Build a SmokeHarness over Infra A fixtures (no network)."""
    from ashare_infra.lake.smoke import SmokeCatalog, SmokeHarness

    catalog = SmokeCatalog.from_frames(load_all_bars())
    scope = make_scope(
        symbols=symbols if symbols is not None else {"600000", "000001"},
        include_meta=True,
    )
    return SmokeHarness.create(scope, catalog, cache_dir=Path(cache_dir))


def run_smoke_scenario(cache_dir: Path) -> dict[str, Any]:
    """Default smoke path: download → add stocks → set_start → load → sim_start."""
    from datetime import date

    harness = build_smoke_harness(cache_dir)
    steps: list[dict[str, Any]] = []

    rows = harness.simulate_download()
    steps.append({"step": "download", "rows": rows, "symbols": sorted(harness.scope.symbols)})

    harness.simulate_add_stocks(["600001", "600003"])
    steps.append(
        {
            "step": "add_stocks",
            "added": ["600001", "600003"],
            "universe": sorted(harness.scope.symbols),
        }
    )

    harness.simulate_set_start(date(2024, 1, 5))
    steps.append(
        {
            "step": "set_start",
            "window_start": harness.scope.window_start.isoformat(),
            "window_end": harness.scope.window_end.isoformat(),
        }
    )

    bars = harness.load_scope_bars()
    steps.append(
        {
            "step": "load_scope_bars",
            "loaded": {s: int(len(df)) for s, df in bars.items()},
        }
    )

    harness.simulate_sim_start()
    steps.append({"step": "sim_start", "frozen": harness.scope.frozen})

    report = harness.report()
    report["scenario_steps"] = steps
    return report
