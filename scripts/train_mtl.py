#!/usr/bin/env python
"""Deprecated compatibility CLI for the retired static MTL trainer.

Use ``run_lstm_rolling_retrain_dim19_regime.py`` with a dataset that embeds a
Feature Contract.  This shim deliberately refuses to train because static
artifacts cannot satisfy the current checkpoint compatibility contract.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="DEPRECATED: static MTL training was retired in favor of Feature Contract-aware rolling training."
    )
    parser.parse_args(argv)
    parser.error(
        "train_mtl.py is retired; use scripts/run_lstm_rolling_retrain_dim19_regime.py "
        "with a Feature Contract dataset"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
