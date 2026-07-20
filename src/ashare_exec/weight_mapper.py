"""Sole producer of final target weights from ranked Decision candidates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeightMapper:
    """Map ranked (symbol, score) pairs to portfolio target weights.

    This is the **only** place in ``ashare_exec`` that should emit final weights
    for the engine. Decisions must not bypass this mapper.
    """

    top_n: int = 3

    def map_weights(
        self,
        ranked: list[tuple[str, float]],
        *,
        current_positions: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Equal-weight the first ``top_n`` ranked symbols.

        ``current_positions`` / turnover gates are reserved (non-goals for this WT).
        """
        _ = current_positions
        selected = [symbol for symbol, _ in ranked[: self.top_n]]
        if not selected:
            return {}
        weight = 1.0 / float(len(selected))
        return {symbol: weight for symbol in selected}
