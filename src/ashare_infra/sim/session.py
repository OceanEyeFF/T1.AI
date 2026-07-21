"""TestSession: account + timeline façade; IC scoring delegates to guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping

import pandas as pd

from ashare_infra.guard.fetch_gate import FetchGate
from ashare_infra.guard.metrics import calculate_daily_cs_ic, summarize_daily_cs
from ashare_infra.guard.scope import DataScope, ListingPolicy, MissingBarPolicy
from ashare_infra.sim.broker import PaperBroker, SimConfig
from ashare_infra.sim.replay import PlanProvider, ReplayConfig, ReplayEngine, ReplayResult


@dataclass
class TestSession:
    """Bound a DataScope + PaperBroker for IC eval or paper replay.

    - IC evaluation default: ``ListingPolicy.EXCLUDE_DAY`` (eval-side; not
      auto-enforced by PaperBroker — see ListingPolicy docstring)
    - Missing bars: ``for_ic`` / ``for_sim`` both default to ``REJECT`` so
      replay matches historical PaperBroker behaviour; set SKIP/RAISE explicitly
      on scope when needed
    - ``score_ic()`` always delegates to ``ashare_infra.guard.metrics``
    """

    __test__ = False  # not a pytest test class

    scope: DataScope
    broker: PaperBroker = field(default_factory=PaperBroker)
    gate: FetchGate | None = None
    replay_config: ReplayConfig = field(default_factory=ReplayConfig)

    def __post_init__(self) -> None:
        if self.gate is None:
            self.gate = FetchGate(scope=self.scope)
        else:
            self.scope = self.gate.scope
        # Scope declares the policy; session enforces it on the broker.
        self.broker.missing_bar_policy = self.scope.missing_bar_policy

    @classmethod
    def for_ic(
        cls,
        symbols: frozenset[str] | set[str],
        window_start: date,
        window_end: date,
        *,
        sim_config: SimConfig | None = None,
    ) -> TestSession:
        scope = DataScope(
            symbols=frozenset(symbols),
            window_start=window_start,
            window_end=window_end,
            listing_policy=ListingPolicy.EXCLUDE_DAY,
            # REJECT preserves pre-audit PaperBroker behaviour for any accidental
            # for_ic().run_replay(...); score_ic does not use missing-bar policy.
            missing_bar_policy=MissingBarPolicy.REJECT,
        )
        broker = PaperBroker(sim_config or SimConfig())
        return cls(scope=scope, broker=broker)

    @classmethod
    def for_sim(
        cls,
        symbols: frozenset[str] | set[str],
        window_start: date,
        window_end: date,
        *,
        sim_config: SimConfig | None = None,
        freeze: bool = True,
    ) -> TestSession:
        scope = DataScope(
            symbols=frozenset(symbols),
            window_start=window_start,
            window_end=window_end,
            listing_policy=ListingPolicy.EXCLUDE_DAY,
            missing_bar_policy=MissingBarPolicy.REJECT,
        )
        gate = FetchGate(scope=scope)
        if freeze:
            gate.sim_start()
        broker = PaperBroker(sim_config or SimConfig())
        return cls(scope=gate.scope, broker=broker, gate=gate)

    def score_ic(
        self,
        predictions: pd.Series,
        labels: pd.Series,
        *,
        method: str = "pearson",
    ) -> dict[str, float]:
        """Unique IC path — delegates to guard.metrics."""
        daily = calculate_daily_cs_ic(predictions, labels, method=method)
        return summarize_daily_cs(daily)

    def run_replay(
        self,
        data_by_symbol: Mapping[str, pd.DataFrame],
        planner: PlanProvider,
    ) -> ReplayResult:
        """Replay within scope symbols only."""
        scoped = {
            s: df
            for s, df in data_by_symbol.items()
            if s in self.scope.symbols
        }
        engine = ReplayEngine(self.replay_config)
        return engine.run(scoped, planner, broker=self.broker)
