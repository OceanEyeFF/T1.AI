"""Infra A fixture pack — see ``manifest.json`` for scenario matrix.

Layout
------
bars/           per-symbol OHLCV CSV (date index)
meta/           stock_basic.csv (list/delist)
panels/         IC prediction/label panel
seeded_cache/   pre-warmed cache hits for DataLake tests
scopes/         reserved for exported DataScope recipes

Run
---
    bash scripts/run_tests_infra_a.sh
"""
